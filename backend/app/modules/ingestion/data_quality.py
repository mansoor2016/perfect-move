"""
Data quality validation pipeline for property ingestion
"""
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class IssueType(Enum):
    """Types of data quality issues"""
    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_FORMAT = "invalid_format"
    SUSPICIOUS_VALUE = "suspicious_value"
    DUPLICATE_DETECTED = "duplicate_detected"
    GEOCODING_FAILED = "geocoding_failed"
    PRICE_ANOMALY = "price_anomaly"
    STALE_DATA = "stale_data"


class IssueSeverity(Enum):
    """Severity levels for data quality issues"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DataQualityIssue:
    """Represents a data quality issue"""
    property_id: str
    issue_type: IssueType
    severity: IssueSeverity
    field_name: str
    description: str
    suggested_fix: Optional[str] = None
    detected_at: datetime = None
    
    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.now()


@dataclass
class ValidationReport:
    """Report containing validation results"""
    total_properties: int
    valid_properties: int
    issues: List[DataQualityIssue]
    overall_score: float
    validation_time: datetime
    
    @property
    def issue_count_by_severity(self) -> Dict[str, int]:
        """Count issues by severity"""
        counts = {severity.value: 0 for severity in IssueSeverity}
        for issue in self.issues:
            counts[issue.severity.value] += 1
        return counts
    
    @property
    def issue_count_by_type(self) -> Dict[str, int]:
        """Count issues by type"""
        counts = {issue_type.value: 0 for issue_type in IssueType}
        for issue in self.issues:
            counts[issue.issue_type.value] += 1
        return counts


class DataQualityValidator:
    """Validates property data quality and identifies issues"""
    
    def __init__(self):
        self.required_fields = ['source', 'source_id', 'address', 'price']
        self.optional_fields = ['bedrooms', 'bathrooms', 'property_type', 'description']
        
        # Price validation ranges (in GBP)
        self.min_reasonable_price = 10000
        self.max_reasonable_price = 50000000
        
        # Coordinate validation ranges for UK
        self.uk_lat_range = (49.0, 61.0)
        self.uk_lon_range = (-8.0, 2.0)
    
    def validate_property(self, property_data: Dict[str, Any]) -> List[DataQualityIssue]:
        """Validate a single property and return list of issues"""
        issues = []
        property_id = property_data.get('source_id', 'unknown')
        
        # Check required fields
        issues.extend(self._validate_required_fields(property_data, property_id))
        
        # Validate specific fields
        issues.extend(self._validate_price(property_data, property_id))
        issues.extend(self._validate_coordinates(property_data, property_id))
        issues.extend(self._validate_address(property_data, property_id))
        issues.extend(self._validate_property_characteristics(property_data, property_id))
        issues.extend(self._validate_data_freshness(property_data, property_id))
        
        return issues
    
    def validate_batch(self, properties: List[Dict[str, Any]]) -> ValidationReport:
        """Validate a batch of properties and return comprehensive report"""
        all_issues = []
        valid_count = 0
        
        for prop in properties:
            prop_issues = self.validate_property(prop)
            all_issues.extend(prop_issues)
            
            # Consider property valid if it has no critical or high severity issues
            has_critical_issues = any(
                issue.severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH] 
                for issue in prop_issues
            )
            if not has_critical_issues:
                valid_count += 1
        
        # Calculate overall quality score
        overall_score = self._calculate_quality_score(properties, all_issues)
        
        return ValidationReport(
            total_properties=len(properties),
            valid_properties=valid_count,
            issues=all_issues,
            overall_score=overall_score,
            validation_time=datetime.now()
        )
    
    def _validate_required_fields(self, property_data: Dict[str, Any], 
                                property_id: str) -> List[DataQualityIssue]:
        """Validate that all required fields are present and non-empty"""
        issues = []
        
        for field in self.required_fields:
            value = property_data.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                issues.append(DataQualityIssue(
                    property_id=property_id,
                    issue_type=IssueType.MISSING_REQUIRED_FIELD,
                    severity=IssueSeverity.CRITICAL,
                    field_name=field,
                    description=f"Required field '{field}' is missing or empty",
                    suggested_fix=f"Provide a valid value for {field}"
                ))
        
        return issues
    
    def _validate_price(self, property_data: Dict[str, Any], 
                       property_id: str) -> List[DataQualityIssue]:
        """Validate property price"""
        issues = []
        price = property_data.get('price')
        
        if price is not None:
            try:
                price_float = float(price)
                
                # Check if price is within reasonable range
                if price_float < self.min_reasonable_price:
                    issues.append(DataQualityIssue(
                        property_id=property_id,
                        issue_type=IssueType.SUSPICIOUS_VALUE,
                        severity=IssueSeverity.MEDIUM,
                        field_name='price',
                        description=f"Price {price_float} seems unusually low",
                        suggested_fix="Verify price accuracy with source"
                    ))
                elif price_float > self.max_reasonable_price:
                    issues.append(DataQualityIssue(
                        property_id=property_id,
                        issue_type=IssueType.SUSPICIOUS_VALUE,
                        severity=IssueSeverity.MEDIUM,
                        field_name='price',
                        description=f"Price {price_float} seems unusually high",
                        suggested_fix="Verify price accuracy with source"
                    ))
                
                # Check for obviously wrong prices (like 0 or negative)
                if price_float <= 0:
                    issues.append(DataQualityIssue(
                        property_id=property_id,
                        issue_type=IssueType.INVALID_FORMAT,
                        severity=IssueSeverity.HIGH,
                        field_name='price',
                        description=f"Invalid price value: {price_float}",
                        suggested_fix="Provide a positive price value"
                    ))
                    
            except (ValueError, TypeError):
                issues.append(DataQualityIssue(
                    property_id=property_id,
                    issue_type=IssueType.INVALID_FORMAT,
                    severity=IssueSeverity.HIGH,
                    field_name='price',
                    description=f"Price '{price}' is not a valid number",
                    suggested_fix="Provide price as a numeric value"
                ))
        
        return issues
    
    def _validate_coordinates(self, property_data: Dict[str, Any], 
                            property_id: str) -> List[DataQualityIssue]:
        """Validate latitude and longitude coordinates"""
        issues = []
        lat = property_data.get('latitude')
        lon = property_data.get('longitude')
        
        if lat is not None and lon is not None:
            try:
                lat_float = float(lat)
                lon_float = float(lon)
                
                # Check if coordinates are within UK bounds
                if not (self.uk_lat_range[0] <= lat_float <= self.uk_lat_range[1]):
                    issues.append(DataQualityIssue(
                        property_id=property_id,
                        issue_type=IssueType.GEOCODING_FAILED,
                        severity=IssueSeverity.MEDIUM,
                        field_name='latitude',
                        description=f"Latitude {lat_float} is outside UK bounds",
                        suggested_fix="Verify property location and geocoding"
                    ))
                
                if not (self.uk_lon_range[0] <= lon_float <= self.uk_lon_range[1]):
                    issues.append(DataQualityIssue(
                        property_id=property_id,
                        issue_type=IssueType.GEOCODING_FAILED,
                        severity=IssueSeverity.MEDIUM,
                        field_name='longitude',
                        description=f"Longitude {lon_float} is outside UK bounds",
                        suggested_fix="Verify property location and geocoding"
                    ))
                
                # Check for obviously invalid coordinates (0,0)
                if lat_float == 0.0 and lon_float == 0.0:
                    issues.append(DataQualityIssue(
                        property_id=property_id,
                        issue_type=IssueType.GEOCODING_FAILED,
                        severity=IssueSeverity.HIGH,
                        field_name='coordinates',
                        description="Coordinates are (0,0) which indicates geocoding failure",
                        suggested_fix="Re-geocode the property address"
                    ))
                    
            except (ValueError, TypeError):
                issues.append(DataQualityIssue(
                    property_id=property_id,
                    issue_type=IssueType.INVALID_FORMAT,
                    severity=IssueSeverity.HIGH,
                    field_name='coordinates',
                    description=f"Invalid coordinate format: lat={lat}, lon={lon}",
                    suggested_fix="Provide coordinates as numeric values"
                ))
        
        return issues
    
    def _validate_address(self, property_data: Dict[str, Any], 
                         property_id: str) -> List[DataQualityIssue]:
        """Validate property address"""
        issues = []
        address = property_data.get('address', '')
        
        if address:
            # Check address length
            if len(address.strip()) < 10:
                issues.append(DataQualityIssue(
                    property_id=property_id,
                    issue_type=IssueType.SUSPICIOUS_VALUE,
                    severity=IssueSeverity.LOW,
                    field_name='address',
                    description="Address seems too short",
                    suggested_fix="Verify address completeness"
                ))
            
            # Check for UK postcode pattern
            uk_postcode_pattern = r'[A-Z]{1,2}[0-9R][0-9A-Z]? [0-9][ABD-HJLNP-UW-Z]{2}'
            if not re.search(uk_postcode_pattern, address.upper()):
                issues.append(DataQualityIssue(
                    property_id=property_id,
                    issue_type=IssueType.SUSPICIOUS_VALUE,
                    severity=IssueSeverity.LOW,
                    field_name='address',
                    description="Address doesn't contain a valid UK postcode",
                    suggested_fix="Verify postcode format"
                ))
        
        return issues
    
    def _validate_property_characteristics(self, property_data: Dict[str, Any], 
                                         property_id: str) -> List[DataQualityIssue]:
        """Validate property characteristics like bedrooms, bathrooms"""
        issues = []
        
        # Validate bedrooms
        bedrooms = property_data.get('bedrooms')
        if bedrooms is not None:
            try:
                bedrooms_int = int(bedrooms)
                if bedrooms_int < 0 or bedrooms_int > 20:
                    issues.append(DataQualityIssue(
                        property_id=property_id,
                        issue_type=IssueType.SUSPICIOUS_VALUE,
                        severity=IssueSeverity.MEDIUM,
                        field_name='bedrooms',
                        description=f"Unusual number of bedrooms: {bedrooms_int}",
                        suggested_fix="Verify bedroom count"
                    ))
            except (ValueError, TypeError):
                issues.append(DataQualityIssue(
                    property_id=property_id,
                    issue_type=IssueType.INVALID_FORMAT,
                    severity=IssueSeverity.MEDIUM,
                    field_name='bedrooms',
                    description=f"Invalid bedrooms value: {bedrooms}",
                    suggested_fix="Provide bedrooms as an integer"
                ))
        
        # Validate bathrooms
        bathrooms = property_data.get('bathrooms')
        if bathrooms is not None:
            try:
                bathrooms_int = int(bathrooms)
                if bathrooms_int < 0 or bathrooms_int > 10:
                    issues.append(DataQualityIssue(
                        property_id=property_id,
                        issue_type=IssueType.SUSPICIOUS_VALUE,
                        severity=IssueSeverity.MEDIUM,
                        field_name='bathrooms',
                        description=f"Unusual number of bathrooms: {bathrooms_int}",
                        suggested_fix="Verify bathroom count"
                    ))
            except (ValueError, TypeError):
                issues.append(DataQualityIssue(
                    property_id=property_id,
                    issue_type=IssueType.INVALID_FORMAT,
                    severity=IssueSeverity.MEDIUM,
                    field_name='bathrooms',
                    description=f"Invalid bathrooms value: {bathrooms}",
                    suggested_fix="Provide bathrooms as an integer"
                ))
        
        return issues
    
    def _validate_data_freshness(self, property_data: Dict[str, Any], 
                               property_id: str) -> List[DataQualityIssue]:
        """Validate data freshness"""
        issues = []
        last_updated = property_data.get('last_updated')
        
        if last_updated:
            try:
                if isinstance(last_updated, str):
                    update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                else:
                    update_time = last_updated
                
                # Check if data is older than 7 days
                days_old = (datetime.now() - update_time.replace(tzinfo=None)).days
                
                if days_old > 7:
                    severity = IssueSeverity.LOW if days_old <= 30 else IssueSeverity.MEDIUM
                    issues.append(DataQualityIssue(
                        property_id=property_id,
                        issue_type=IssueType.STALE_DATA,
                        severity=severity,
                        field_name='last_updated',
                        description=f"Data is {days_old} days old",
                        suggested_fix="Refresh property data from source"
                    ))
                    
            except (ValueError, TypeError) as e:
                issues.append(DataQualityIssue(
                    property_id=property_id,
                    issue_type=IssueType.INVALID_FORMAT,
                    severity=IssueSeverity.LOW,
                    field_name='last_updated',
                    description=f"Invalid date format: {last_updated}",
                    suggested_fix="Use ISO format for dates"
                ))
        
        return issues
    
    def _calculate_quality_score(self, properties: List[Dict[str, Any]], 
                               issues: List[DataQualityIssue]) -> float:
        """Calculate overall data quality score (0.0 to 1.0)"""
        if not properties:
            return 1.0
        
        # Weight issues by severity
        severity_weights = {
            IssueSeverity.LOW: 0.1,
            IssueSeverity.MEDIUM: 0.3,
            IssueSeverity.HIGH: 0.7,
            IssueSeverity.CRITICAL: 1.0
        }
        
        total_penalty = sum(severity_weights[issue.severity] for issue in issues)
        max_possible_penalty = len(properties) * sum(severity_weights.values())
        
        if max_possible_penalty == 0:
            return 1.0
        
        score = 1.0 - (total_penalty / max_possible_penalty)
        return max(0.0, min(1.0, score))
    
    def resolve_conflicts(self, conflicting_properties: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Resolve conflicts between duplicate properties"""
        if not conflicting_properties:
            return {}
        
        if len(conflicting_properties) == 1:
            return conflicting_properties[0]
        
        # Score each property based on data quality
        scored_properties = []
        for prop in conflicting_properties:
            issues = self.validate_property(prop)
            quality_score = self._calculate_quality_score([prop], issues)
            scored_properties.append((prop, quality_score))
        
        # Sort by quality score (highest first)
        scored_properties.sort(key=lambda x: x[1], reverse=True)
        
        # Return the highest quality property
        best_property = scored_properties[0][0]
        
        logger.info(f"Resolved conflict: selected property from {best_property.get('source')} "
                   f"with quality score {scored_properties[0][1]:.2f}")
        
        return best_property