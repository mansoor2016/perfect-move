import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AdvancedFilters from '../AdvancedFilters'
import { SearchCriteria } from '@/types/property'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { describe } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { describe } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { describe } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { describe } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { describe } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { describe } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { describe } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { describe } from 'node:test'
import { beforeEach } from 'node:test'
import { describe } from 'node:test'

const mockOnCriteriaChange = jest.fn()
const mockOnApplyFilters = jest.fn()
const mockOnToggleVisibility = jest.fn()

const defaultCriteria: SearchCriteria = {
  property_types: ['house', 'flat'],
  status: ['for_sale'],
  areas: [],
  proximity_filters: [],
  commute_filters: [],
  limit: 50,
  offset: 0,
  sort_by: 'relevance'
}

const defaultProps = {
  criteria: defaultCriteria,
  onCriteriaChange: mockOnCriteriaChange,
  onApplyFilters: mockOnApplyFilters,
  onToggleVisibility: mockOnToggleVisibility,
  isVisible: true
}

describe('AdvancedFilters', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Visibility Toggle', () => {
    it('shows toggle button when not visible', () => {
      render(<AdvancedFilters {...defaultProps} isVisible={false} />)
      
      const toggleButton = screen.getByTestId('show-filters-button')
      expect(toggleButton).toBeInTheDocument()
      expect(toggleButton).toHaveTextContent('Advanced Filters')
    })

    it('shows full interface when visible', () => {
      render(<AdvancedFilters {...defaultProps} />)
      
      expect(screen.getByTestId('advanced-filters')).toBeInTheDocument()
      expect(screen.getByText('Advanced Filters')).toBeInTheDocument()
      expect(screen.getByTestId('close-filters-button')).toBeInTheDocument()
    })

    it('calls onToggleVisibility when toggle buttons are clicked', async () => {
      const user = userEvent.setup()
      
      // Test show button
      const { rerender } = render(<AdvancedFilters {...defaultProps} isVisible={false} />)
      await user.click(screen.getByTestId('show-filters-button'))
      expect(mockOnToggleVisibility).toHaveBeenCalledTimes(1)

      // Test close button
      rerender(<AdvancedFilters {...defaultProps} isVisible={true} />)
      await user.click(screen.getByTestId('close-filters-button'))
      expect(mockOnToggleVisibility).toHaveBeenCalledTimes(2)
    })
  })

  describe('Tab Navigation', () => {
    it('renders all tabs', () => {
      render(<AdvancedFilters {...defaultProps} />)
      
      expect(screen.getByTestId('tab-amenities')).toBeInTheDocument()
      expect(screen.getByTestId('tab-commute')).toBeInTheDocument()
      expect(screen.getByTestId('tab-environment')).toBeInTheDocument()
      expect(screen.getByTestId('tab-presets')).toBeInTheDocument()
    })

    it('switches between tabs', async () => {
      const user = userEvent.setup()
      render(<AdvancedFilters {...defaultProps} />)
      
      // Default tab should be amenities
      expect(screen.getByTestId('amenities-tab')).toBeInTheDocument()
      
      // Switch to commute tab
      await user.click(screen.getByTestId('tab-commute'))
      expect(screen.getByTestId('commute-tab')).toBeInTheDocument()
      
      // Switch to environment tab
      await user.click(screen.getByTestId('tab-environment'))
      expect(screen.getByTestId('environment-tab')).toBeInTheDocument()
      
      // Switch to presets tab
      await user.click(screen.getByTestId('tab-presets'))
      expect(screen.getByTestId('presets-tab')).toBeInTheDocument()
    })
  })

  describe('Proximity Filters', () => {
    it('shows empty state when no proximity filters exist', () => {
      render(<AdvancedFilters {...defaultProps} />)
      
      expect(screen.getByText('No amenity filters added yet.')).toBeInTheDocument()
    })

    it('adds a new proximity filter', async () => {
      const user = userEvent.setup()
      render(<AdvancedFilters {...defaultProps} />)
      
      await user.click(screen.getByTestId('add-proximity-filter'))
      
      expect(mockOnCriteriaChange).toHaveBeenCalledWith({
        ...defaultCriteria,
        proximity_filters: [{
          amenity_type: 'park',
          max_distance: 1000,
          distance_unit: 'meters',
          walking_distance: true
        }]
      })
    })

    it('displays existing proximity filters', () => {
      const criteriaWithFilters = {
        ...defaultCriteria,
        proximity_filters: [{
          amenity_type: 'train_station' as const,
          max_distance: 500,
          distance_unit: 'meters' as const,
          walking_distance: true
        }]
      }
      
      render(<AdvancedFilters {...defaultProps} criteria={criteriaWithFilters} />)
      
      expect(screen.getByTestId('proximity-filter-0')).toBeInTheDocument()
      const select = screen.getByTestId('amenity-type-0') as HTMLSelectElement
      expect(select.value).toBe('train_station')
      expect(screen.getByDisplayValue('500')).toBeInTheDocument()
    })

    it('removes a proximity filter', async () => {
      const user = userEvent.setup()
      const criteriaWithFilters = {
        ...defaultCriteria,
        proximity_filters: [{
          amenity_type: 'park' as const,
          max_distance: 1000,
          distance_unit: 'meters' as const,
          walking_distance: true
        }]
      }
      
      render(<AdvancedFilters {...defaultProps} criteria={criteriaWithFilters} />)
      
      await user.click(screen.getByTestId('remove-proximity-filter-0'))
      
      expect(mockOnCriteriaChange).toHaveBeenCalledWith({
        ...defaultCriteria,
        proximity_filters: []
      })
    })

    it('updates proximity filter amenity type', async () => {
      const user = userEvent.setup()
      const criteriaWithFilters = {
        ...defaultCriteria,
        proximity_filters: [{
          amenity_type: 'park' as const,
          max_distance: 1000,
          distance_unit: 'meters' as const,
          walking_distance: true
        }]
      }
      
      render(<AdvancedFilters {...defaultProps} criteria={criteriaWithFilters} />)
      
      const select = screen.getByTestId('amenity-type-0')
      await user.selectOptions(select, 'gym')
      
      expect(mockOnCriteriaChange).toHaveBeenCalledWith({
        ...defaultCriteria,
        proximity_filters: [{
          amenity_type: 'gym',
          max_distance: 1000,
          distance_unit: 'meters',
          walking_distance: true
        }]
      })
    })

    it('updates proximity filter distance', async () => {
      const criteriaWithFilters = {
        ...defaultCriteria,
        proximity_filters: [{
          amenity_type: 'park' as const,
          max_distance: 1000,
          distance_unit: 'meters' as const,
          walking_distance: true
        }]
      }
      
      render(<AdvancedFilters {...defaultProps} criteria={criteriaWithFilters} />)
      
      const input = screen.getByTestId('max-distance-0')
      fireEvent.change(input, { target: { value: '2000' } })
      
      expect(mockOnCriteriaChange).toHaveBeenCalledWith({
        ...defaultCriteria,
        proximity_filters: [{
          amenity_type: 'park',
          max_distance: 2000,
          distance_unit: 'meters',
          walking_distance: true
        }]
      })
    })

    it('toggles walking distance option', async () => {
      const user = userEvent.setup()
      const criteriaWithFilters = {
        ...defaultCriteria,
        proximity_filters: [{
          amenity_type: 'park' as const,
          max_distance: 1000,
          distance_unit: 'meters' as const,
          walking_distance: true
        }]
      }
      
      render(<AdvancedFilters {...defaultProps} criteria={criteriaWithFilters} />)
      
      const checkbox = screen.getByTestId('walking-distance-0')
      await user.click(checkbox)
      
      expect(mockOnCriteriaChange).toHaveBeenCalledWith({
        ...defaultCriteria,
        proximity_filters: [{
          amenity_type: 'park',
          max_distance: 1000,
          distance_unit: 'meters',
          walking_distance: false
        }]
      })
    })
  })

  describe('Commute Filters', () => {
    it('shows empty state when no commute filters exist', async () => {
      const user = userEvent.setup()
      render(<AdvancedFilters {...defaultProps} />)
      
      await user.click(screen.getByTestId('tab-commute'))
      
      expect(screen.getByText('No commute filters added yet.')).toBeInTheDocument()
    })

    it('adds a new commute filter', async () => {
      const user = userEvent.setup()
      render(<AdvancedFilters {...defaultProps} />)
      
      await user.click(screen.getByTestId('tab-commute'))
      await user.click(screen.getByTestId('add-commute-filter'))
      
      expect(mockOnCriteriaChange).toHaveBeenCalledWith({
        ...defaultCriteria,
        commute_filters: [{
          destination_address: '',
          max_commute_minutes: 30,
          transport_modes: ['public_transport']
        }]
      })
    })

    it('updates commute filter destination', async () => {
      const user = userEvent.setup()
      const criteriaWithFilters = {
        ...defaultCriteria,
        commute_filters: [{
          destination_address: '',
          max_commute_minutes: 30,
          transport_modes: ['public_transport']
        }]
      }
      
      render(<AdvancedFilters {...defaultProps} criteria={criteriaWithFilters} />)
      
      await user.click(screen.getByTestId('tab-commute'))
      
      const input = screen.getByTestId('destination-address-0')
      fireEvent.change(input, { target: { value: 'London Bridge' } })
      
      expect(mockOnCriteriaChange).toHaveBeenCalledWith({
        ...defaultCriteria,
        commute_filters: [{
          destination_address: 'London Bridge',
          max_commute_minutes: 30,
          transport_modes: ['public_transport']
        }]
      })
    })

    it('updates commute time', async () => {
      const user = userEvent.setup()
      const criteriaWithFilters = {
        ...defaultCriteria,
        commute_filters: [{
          destination_address: 'London Bridge',
          max_commute_minutes: 30,
          transport_modes: ['public_transport']
        }]
      }
      
      render(<AdvancedFilters {...defaultProps} criteria={criteriaWithFilters} />)
      
      await user.click(screen.getByTestId('tab-commute'))
      
      const input = screen.getByTestId('max-commute-minutes-0')
      fireEvent.change(input, { target: { value: '45' } })
      
      expect(mockOnCriteriaChange).toHaveBeenCalledWith({
        ...defaultCriteria,
        commute_filters: [{
          destination_address: 'London Bridge',
          max_commute_minutes: 45,
          transport_modes: ['public_transport']
        }]
      })
    })

    it('toggles transport modes', async () => {
      const user = userEvent.setup()
      const criteriaWithFilters = {
        ...defaultCriteria,
        commute_filters: [{
          destination_address: 'London Bridge',
          max_commute_minutes: 30,
          transport_modes: ['public_transport']
        }]
      }
      
      render(<AdvancedFilters {...defaultProps} criteria={criteriaWithFilters} />)
      
      await user.click(screen.getByTestId('tab-commute'))
      
      // Add walking mode
      const walkingCheckbox = screen.getByTestId('transport-mode-walking-0')
      await user.click(walkingCheckbox)
      
      expect(mockOnCriteriaChange).toHaveBeenCalledWith({
        ...defaultCriteria,
        commute_filters: [{
          destination_address: 'London Bridge',
          max_commute_minutes: 30,
          transport_modes: ['public_transport', 'walking']
        }]
      })
    })

    it('removes a commute filter', async () => {
      const user = userEvent.setup()
      const criteriaWithFilters = {
        ...defaultCriteria,
        commute_filters: [{
          destination_address: 'London Bridge',
          max_commute_minutes: 30,
          transport_modes: ['public_transport']
        }]
      }
      
      render(<AdvancedFilters {...defaultProps} criteria={criteriaWithFilters} />)
      
      await user.click(screen.getByTestId('tab-commute'))
      await user.click(screen.getByTestId('remove-commute-filter-0'))
      
      expect(mockOnCriteriaChange).toHaveBeenCalledWith({
        ...defaultCriteria,
        commute_filters: []
      })
    })
  })

  describe('Environmental Filters', () => {
    it('updates air pollution level', async () => {
      const user = userEvent.setup()
      render(<AdvancedFilters {...defaultProps} />)
      
      await user.click(screen.getByTestId('tab-environment'))
      
      const slider = screen.getByTestId('air-pollution-slider')
      fireEvent.change(slider, { target: { value: '25' } })
      
      expect(mockOnCriteriaChange).toHaveBeenCalledWith({
        ...defaultCriteria,
        environmental_filters: {
          max_air_pollution_level: 25
        }
      })
    })

    it('updates noise level', async () => {
      const user = userEvent.setup()
      render(<AdvancedFilters {...defaultProps} />)
      
      await user.click(screen.getByTestId('tab-environment'))
      
      const slider = screen.getByTestId('noise-level-slider')
      fireEvent.change(slider, { target: { value: '45' } })
      
      expect(mockOnCriteriaChange).toHaveBeenCalledWith({
        ...defaultCriteria,
        environmental_filters: {
          max_noise_level: 45
        }
      })
    })

    it('updates green space proximity', async () => {
      const user = userEvent.setup()
      render(<AdvancedFilters {...defaultProps} />)
      
      await user.click(screen.getByTestId('tab-environment'))
      
      const input = screen.getByTestId('green-space-proximity')
      fireEvent.change(input, { target: { value: '300' } })
      
      expect(mockOnCriteriaChange).toHaveBeenCalledWith({
        ...defaultCriteria,
        environmental_filters: {
          min_green_space_proximity: 300
        }
      })
    })

    it('toggles flood risk avoidance', async () => {
      const user = userEvent.setup()
      render(<AdvancedFilters {...defaultProps} />)
      
      await user.click(screen.getByTestId('tab-environment'))
      
      const checkbox = screen.getByTestId('avoid-flood-risk')
      await user.click(checkbox)
      
      expect(mockOnCriteriaChange).toHaveBeenCalledWith({
        ...defaultCriteria,
        environmental_filters: {
          avoid_flood_risk: true
        }
      })
    })
  })

  describe('Filter Presets', () => {
    it('displays all preset options', async () => {
      const user = userEvent.setup()
      render(<AdvancedFilters {...defaultProps} />)
      
      await user.click(screen.getByTestId('tab-presets'))
      
      expect(screen.getByTestId('preset-family-friendly')).toBeInTheDocument()
      expect(screen.getByTestId('preset-commuter-friendly')).toBeInTheDocument()
      expect(screen.getByTestId('preset-urban-lifestyle')).toBeInTheDocument()
      expect(screen.getByTestId('preset-green-living')).toBeInTheDocument()
    })

    it('applies a preset', async () => {
      const user = userEvent.setup()
      render(<AdvancedFilters {...defaultProps} />)
      
      await user.click(screen.getByTestId('tab-presets'))
      await user.click(screen.getByTestId('apply-preset-family-friendly'))
      
      expect(mockOnCriteriaChange).toHaveBeenCalledWith(
        expect.objectContaining({
          proximity_filters: expect.arrayContaining([
            expect.objectContaining({ amenity_type: 'school' }),
            expect.objectContaining({ amenity_type: 'park' })
          ]),
          environmental_filters: expect.objectContaining({
            avoid_flood_risk: true,
            max_air_pollution_level: 30,
            max_noise_level: 55
          })
        })
      )
    })
  })

  describe('Filter Conflicts', () => {
    it('detects duplicate amenity filters', () => {
      const criteriaWithDuplicates = {
        ...defaultCriteria,
        proximity_filters: [
          { amenity_type: 'park' as const, max_distance: 500, distance_unit: 'meters' as const, walking_distance: true },
          { amenity_type: 'park' as const, max_distance: 1000, distance_unit: 'meters' as const, walking_distance: true }
        ]
      }
      
      render(<AdvancedFilters {...defaultProps} criteria={criteriaWithDuplicates} />)
      
      expect(screen.getByTestId('filter-conflicts')).toBeInTheDocument()
      expect(screen.getByText(/Duplicate amenity filters detected/)).toBeInTheDocument()
    })

    it('warns about very short commute times', () => {
      const criteriaWithShortCommute = {
        ...defaultCriteria,
        commute_filters: [{
          destination_address: 'London Bridge',
          max_commute_minutes: 5,
          transport_modes: ['walking']
        }]
      }
      
      render(<AdvancedFilters {...defaultProps} criteria={criteriaWithShortCommute} />)
      
      expect(screen.getByTestId('filter-conflicts')).toBeInTheDocument()
      expect(screen.getByText(/Very short commute times may limit/)).toBeInTheDocument()
    })

    it('warns about strict air quality requirements', () => {
      const criteriaWithStrictAir = {
        ...defaultCriteria,
        environmental_filters: {
          max_air_pollution_level: 10
        }
      }
      
      render(<AdvancedFilters {...defaultProps} criteria={criteriaWithStrictAir} />)
      
      expect(screen.getByTestId('filter-conflicts')).toBeInTheDocument()
      expect(screen.getByText(/Very strict air quality requirements/)).toBeInTheDocument()
    })
  })

  describe('Actions', () => {
    it('clears all filters', async () => {
      const user = userEvent.setup()
      const criteriaWithFilters = {
        ...defaultCriteria,
        proximity_filters: [{ amenity_type: 'park' as const, max_distance: 500, distance_unit: 'meters' as const, walking_distance: true }],
        environmental_filters: { max_air_pollution_level: 30 },
        commute_filters: [{ destination_address: 'London', max_commute_minutes: 30, transport_modes: ['walking'] }]
      }
      
      render(<AdvancedFilters {...defaultProps} criteria={criteriaWithFilters} />)
      
      await user.click(screen.getByTestId('clear-all-filters'))
      
      expect(mockOnCriteriaChange).toHaveBeenCalledWith({
        ...defaultCriteria,
        proximity_filters: [],
        environmental_filters: undefined,
        commute_filters: []
      })
    })

    it('calls onApplyFilters when apply button is clicked', async () => {
      const user = userEvent.setup()
      render(<AdvancedFilters {...defaultProps} />)
      
      await user.click(screen.getByTestId('apply-filters'))
      
      expect(mockOnApplyFilters).toHaveBeenCalledTimes(1)
    })

    it('calls onToggleVisibility when cancel button is clicked', async () => {
      const user = userEvent.setup()
      render(<AdvancedFilters {...defaultProps} />)
      
      await user.click(screen.getByTestId('cancel-filters'))
      
      expect(mockOnToggleVisibility).toHaveBeenCalledTimes(1)
    })
  })
})