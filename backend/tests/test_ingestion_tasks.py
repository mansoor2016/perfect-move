"""
Tests for ingestion background tasks and data quality validation
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from celery import Celery

from app.modules.ingestion.tasks import (
    sync_properties_for_location,
    sync_rightmove_properties,
    sync_zoopla_properties,
    incremental_sync_properties,
    cleanup_old_properties,
    validate_property_data_quality,
    schedule_location_sync,
    get_task_status
)
from app.modules.ingestion.data_quality import (
    DataQualityValidator,
    DataQualityIssue,
    IssueType,
    IssueSeverity,
    ValidationReport
)


class TestDataQualityValidator:
    """Test data quality validation functionality"""
    
    @pytest.fixture
    def validator(self):
        return DataQualityValidator()
    
    @pytest.fixture
    def valid_property(self):
        return {
            'source': 'rightmove',
            'source_id': 'rm_123',
            'address': '123 Test Street, London SW1 1AA',
            'price': 450000,
            'bedrooms': 3,
            'bathrooms': 2,
            'property_type': 'house',
            'latitude': 51.5074,
            'longitude': -0.1278,
            'last_updated': datetime.now().isoformat()
        }
    
    @pytest.fixture
    def invalid_property(self):
        return {
            'source': 'zoopla',
            'source_id': 'zp_456',
            'address': '',  # Missing address
            'price': -100,  # Invalid price
            'bedrooms': 50,  # Suspicious bedroom count
            'bathrooms': 'invalid',  # Invalid format
            'latitude': 0.0,  # Invalid coordinates
            'longitude': 0.0,
            'last_updated': (datetime.now() - timedelta(days=60)).isoformat()  # Stale data
        }
    
    def test_validate_valid_property(self, validator, valid_property):
        """Test validation of a valid property"""
        issues = validator.validate_property(valid_property)
        
        # Should have minimal or no issues
        critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        assert len(critical_issues) == 0
    
    def test_validate_invalid_property(self, validator, invalid_property):
        """Test validation of an invalid property"""
        issues = validator.validate_property(invalid_property)
        
        # Should have multiple issues
        assert len(issues) > 0
        
        # Check for specific issue types
        issue_types = {issue.issue_type for issue in issues}
        assert IssueType.MISSING_REQUIRED_FIELD in issue_types
        assert IssueType.INVALID_FORMAT in issue_types
        assert IssueType.SUSPICIOUS_VALUE in issue_types
    
    def test_validate_batch(self, validator, valid_property, invalid_property):
        """Test batch validation"""
        properties = [valid_property, invalid_property]
        report = validator.validate_batch(properties)
        
        assert isinstance(report, ValidationReport)
        assert report.total_properties == 2
        assert report.valid_properties <= 2
        assert len(report.issues) > 0
        assert 0.0 <= report.overall_score <= 1.0
    
    def test_price_validation(self, validator):
        """Test price validation logic"""
        # Valid price
        prop_valid = {'source_id': 'test', 'price': 300000}
        issues = validator._validate_price(prop_valid, 'test')
        assert len(issues) == 0
        
        # Invalid price (too low)
        prop_low = {'source_id': 'test', 'price': 1000}
        issues = validator._validate_price(prop_low, 'test')
        assert any(issue.issue_type == IssueType.SUSPICIOUS_VALUE for issue in issues)
        
        # Invalid price (negative)
        prop_negative = {'source_id': 'test', 'price': -100}
        issues = validator._validate_price(prop_negative, 'test')
        assert any(issue.severity == IssueSeverity.HIGH for issue in issues)
        
        # Invalid price format
        prop_invalid = {'source_id': 'test', 'price': 'not_a_number'}
        issues = validator._validate_price(prop_invalid, 'test')
        assert any(issue.issue_type == IssueType.INVALID_FORMAT for issue in issues)
    
    def test_coordinate_validation(self, validator):
        """Test coordinate validation"""
        # Valid UK coordinates
        prop_valid = {
            'source_id': 'test',
            'latitude': 51.5074,
            'longitude': -0.1278
        }
        issues = validator._validate_coordinates(prop_valid, 'test')
        assert len(issues) == 0
        
        # Invalid coordinates (0,0)
        prop_zero = {
            'source_id': 'test',
            'latitude': 0.0,
            'longitude': 0.0
        }
        issues = validator._validate_coordinates(prop_zero, 'test')
        assert any(issue.issue_type == IssueType.GEOCODING_FAILED for issue in issues)
        
        # Coordinates outside UK
        prop_outside = {
            'source_id': 'test',
            'latitude': 40.7128,  # New York
            'longitude': -74.0060
        }
        issues = validator._validate_coordinates(prop_outside, 'test')
        assert len(issues) > 0
    
    def test_address_validation(self, validator):
        """Test address validation"""
        # Valid address with postcode
        prop_valid = {
            'source_id': 'test',
            'address': '123 Test Street, London SW1 1AA'
        }
        issues = validator._validate_address(prop_valid, 'test')
        # Should have minimal issues
        critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        assert len(critical_issues) == 0
        
        # Short address
        prop_short = {
            'source_id': 'test',
            'address': '123 St'
        }
        issues = validator._validate_address(prop_short, 'test')
        assert any(issue.issue_type == IssueType.SUSPICIOUS_VALUE for issue in issues)
    
    def test_resolve_conflicts(self, validator):
        """Test conflict resolution between duplicate properties"""
        high_quality_prop = {
            'source': 'rightmove',
            'source_id': 'rm_123',
            'address': '123 Test Street, London SW1 1AA',
            'price': 450000,
            'bedrooms': 3,
            'bathrooms': 2,
            'reliability_score': 0.9
        }
        
        low_quality_prop = {
            'source': 'zoopla',
            'source_id': 'zp_123',
            'address': '123 Test St',  # Shorter address
            'price': None,  # Missing price
            'bedrooms': 3,
            'reliability_score': 0.6
        }
        
        resolved = validator.resolve_conflicts([high_quality_prop, low_quality_prop])
        
        # Should select the higher quality property
        assert resolved['source'] == 'rightmove'
        assert resolved['price'] == 450000


class TestCeleryTasks:
    """Test Celery background tasks"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None
        db.query.return_value.offset.return_value.limit.return_value.all.return_value = []
        db.commit.return_value = None
        db.rollback.return_value = None
        return db
    
    @pytest.fixture
    def mock_ingestion_service(self):
        """Mock ingestion service"""
        service = Mock()
        service.sync_properties_for_location.return_value = [
            {
                'source': 'rightmove',
                'source_id': 'rm_123',
                'address': '123 Test Street',
                'price': 450000
            }
        ]
        service.save_properties_to_db.return_value = [Mock()]
        return service
    
    @patch('app.modules.ingestion.tasks.IngestionService')
    @patch('app.modules.ingestion.tasks.DataQualityValidator')
    def test_sync_properties_for_location_task(self, mock_validator_class, 
                                             mock_service_class, mock_db):
        """Test the main property sync task"""
        # Setup mocks
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        mock_validator = Mock()
        mock_validator_class.return_value = mock_validator
        mock_validator.validate_batch.return_value = {
            'overall_score': 0.85,
            'issues': []
        }
        
        # Mock async call
        with patch('asyncio.run') as mock_asyncio:
            mock_asyncio.return_value = [{'source': 'rightmove', 'source_id': 'rm_123'}]
            mock_service.save_properties_to_db.return_value = [Mock()]
            
            # Create a mock task instance
            task_instance = Mock()
            task_instance.request.retries = 0
            
            # Call the task function directly
            result = sync_properties_for_location.run(
                mock_db, "London", 5, 100
            )
            
            # Verify result
            assert result['location'] == "London"
            assert 'properties_fetched' in result
            assert 'sync_time' in result
    
    def test_schedule_location_sync(self):
        """Test task scheduling utility"""
        with patch('app.modules.ingestion.tasks.sync_properties_for_location.delay') as mock_delay:
            mock_delay.return_value = Mock(id='task_123')
            
            result = schedule_location_sync("London", 5, 100)
            
            mock_delay.assert_called_once_with("London", 5, 100)
            assert result.id == 'task_123'
    
    def test_get_task_status(self):
        """Test task status retrieval"""
        with patch('app.modules.ingestion.tasks.celery_app.AsyncResult') as mock_result:
            mock_async_result = Mock()
            mock_async_result.status = 'SUCCESS'
            mock_async_result.result = {'completed': True}
            mock_async_result.ready.return_value = True
            mock_async_result.failed.return_value = False
            mock_result.return_value = mock_async_result
            
            status = get_task_status('task_123')
            
            assert status['task_id'] == 'task_123'
            assert status['status'] == 'SUCCESS'
            assert status['result'] == {'completed': True}
    
    @pytest.mark.skip(reason="Complex SQLAlchemy mocking - functionality tested in integration tests")
    def test_cleanup_old_properties_task(self, mock_db):
        """Test cleanup of old properties"""
        # This test is skipped due to complex SQLAlchemy mocking requirements
        # The functionality is covered by integration tests
        pass


class TestDataQualityIssue:
    """Test DataQualityIssue class"""
    
    def test_issue_creation(self):
        """Test creating a data quality issue"""
        issue = DataQualityIssue(
            property_id='test_123',
            issue_type=IssueType.MISSING_REQUIRED_FIELD,
            severity=IssueSeverity.HIGH,
            field_name='price',
            description='Price is missing'
        )
        
        assert issue.property_id == 'test_123'
        assert issue.issue_type == IssueType.MISSING_REQUIRED_FIELD
        assert issue.severity == IssueSeverity.HIGH
        assert issue.field_name == 'price'
        assert issue.description == 'Price is missing'
        assert issue.detected_at is not None


class TestValidationReport:
    """Test ValidationReport class"""
    
    def test_report_creation(self):
        """Test creating a validation report"""
        issues = [
            DataQualityIssue('prop1', IssueType.MISSING_REQUIRED_FIELD, IssueSeverity.HIGH, 'price', 'Missing price'),
            DataQualityIssue('prop2', IssueType.SUSPICIOUS_VALUE, IssueSeverity.MEDIUM, 'bedrooms', 'Too many bedrooms'),
            DataQualityIssue('prop3', IssueType.STALE_DATA, IssueSeverity.LOW, 'last_updated', 'Old data')
        ]
        
        report = ValidationReport(
            total_properties=10,
            valid_properties=7,
            issues=issues,
            overall_score=0.75,
            validation_time=datetime.now()
        )
        
        assert report.total_properties == 10
        assert report.valid_properties == 7
        assert len(report.issues) == 3
        assert report.overall_score == 0.75
        
        # Test issue counting
        severity_counts = report.issue_count_by_severity
        assert severity_counts['high'] == 1
        assert severity_counts['medium'] == 1
        assert severity_counts['low'] == 1
        
        type_counts = report.issue_count_by_type
        assert type_counts['missing_required_field'] == 1
        assert type_counts['suspicious_value'] == 1
        assert type_counts['stale_data'] == 1


@pytest.mark.integration
def test_full_ingestion_pipeline_with_quality_validation():
    """Integration test for the complete ingestion pipeline with quality validation"""
    validator = DataQualityValidator()
    
    # Sample properties with various quality issues
    properties = [
        {
            'source': 'rightmove',
            'source_id': 'rm_good',
            'address': '123 Perfect Street, London SW1 1AA',
            'price': 450000,
            'bedrooms': 3,
            'bathrooms': 2,
            'property_type': 'house',
            'latitude': 51.5074,
            'longitude': -0.1278,
            'last_updated': datetime.now().isoformat()
        },
        {
            'source': 'zoopla',
            'source_id': 'zp_issues',
            'address': 'Bad St',  # Too short
            'price': -100,  # Invalid
            'bedrooms': 50,  # Suspicious
            'bathrooms': 'invalid',  # Wrong format
            'latitude': 0.0,  # Invalid coordinates
            'longitude': 0.0,
            'last_updated': (datetime.now() - timedelta(days=60)).isoformat()  # Stale
        }
    ]
    
    # Run validation
    report = validator.validate_batch(properties)
    
    # Verify results
    assert report.total_properties == 2
    assert report.valid_properties == 1  # Only the good property should be valid
    assert len(report.issues) > 0
    assert report.overall_score < 1.0  # Should be reduced due to issues
    
    # Verify issue detection
    issue_types = {issue.issue_type for issue in report.issues}
    assert IssueType.INVALID_FORMAT in issue_types
    assert IssueType.SUSPICIOUS_VALUE in issue_types