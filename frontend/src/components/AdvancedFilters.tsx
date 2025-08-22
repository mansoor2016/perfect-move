'use client'

import { useState, useEffect } from 'react'
import {
  AdjustmentsHorizontalIcon,
  XMarkIcon,
  ExclamationTriangleIcon,
  BookmarkIcon,
  PlusIcon
} from '@heroicons/react/24/outline'
import { SearchCriteria, ProximityFilter, EnvironmentalFilter, CommuteFilter } from '@/types/property'

interface FilterConflict {
  type: 'warning' | 'error'
  message: string
  affectedFilters: string[]
}

interface FilterPreset {
  id: string
  name: string
  description: string
  criteria: Partial<SearchCriteria>
}

interface AdvancedFiltersProps {
  criteria: SearchCriteria
  onCriteriaChange: (criteria: SearchCriteria) => void
  onApplyFilters: () => void
  isVisible: boolean
  onToggleVisibility: () => void
}

const AMENITY_OPTIONS = [
  { value: 'park', label: 'Parks & Green Spaces', icon: '🌳' },
  { value: 'train_station', label: 'Train Station', icon: '🚂' },
  { value: 'gym', label: 'Gym & Fitness', icon: '💪' },
  { value: 'school', label: 'Schools', icon: '🏫' },
  { value: 'hospital', label: 'Hospital', icon: '🏥' },
  { value: 'shopping_center', label: 'Shopping Center', icon: '🛒' },
  { value: 'restaurant', label: 'Restaurants', icon: '🍽️' },
  { value: 'pharmacy', label: 'Pharmacy', icon: '💊' },
] as const

const TRANSPORT_MODES = [
  { value: 'walking', label: 'Walking', icon: '🚶' },
  { value: 'cycling', label: 'Cycling', icon: '🚴' },
  { value: 'public_transport', label: 'Public Transport', icon: '🚌' },
  { value: 'driving', label: 'Driving', icon: '🚗' },
] as const

const DEFAULT_PRESETS: FilterPreset[] = [
  {
    id: 'family-friendly',
    name: 'Family Friendly',
    description: 'Near schools, parks, and safe areas',
    criteria: {
      proximity_filters: [
        { amenity_type: 'school', max_distance: 1000, distance_unit: 'meters', walking_distance: true },
        { amenity_type: 'park', max_distance: 500, distance_unit: 'meters', walking_distance: true }
      ],
      environmental_filters: {
        avoid_flood_risk: true,
        max_air_pollution_level: 30,
        max_noise_level: 55
      }
    }
  },
  {
    id: 'commuter-friendly',
    name: 'Commuter Friendly',
    description: 'Close to transport links',
    criteria: {
      proximity_filters: [
        { amenity_type: 'train_station', max_distance: 1000, distance_unit: 'meters', walking_distance: true }
      ]
    }
  },
  {
    id: 'urban-lifestyle',
    name: 'Urban Lifestyle',
    description: 'Near restaurants, gyms, and shopping',
    criteria: {
      proximity_filters: [
        { amenity_type: 'restaurant', max_distance: 500, distance_unit: 'meters', walking_distance: true },
        { amenity_type: 'gym', max_distance: 1000, distance_unit: 'meters', walking_distance: true },
        { amenity_type: 'shopping_center', max_distance: 2000, distance_unit: 'meters', walking_distance: false }
      ]
    }
  },
  {
    id: 'green-living',
    name: 'Green Living',
    description: 'Low pollution, near green spaces',
    criteria: {
      proximity_filters: [
        { amenity_type: 'park', max_distance: 300, distance_unit: 'meters', walking_distance: true }
      ],
      environmental_filters: {
        max_air_pollution_level: 25,
        max_noise_level: 50,
        min_green_space_proximity: 200
      }
    }
  }
]

export default function AdvancedFilters({
  criteria,
  onCriteriaChange,
  onApplyFilters,
  isVisible,
  onToggleVisibility
}: AdvancedFiltersProps) {
  const [conflicts, setConflicts] = useState<FilterConflict[]>([])
  const [activeTab, setActiveTab] = useState<'amenities' | 'commute' | 'environment' | 'presets'>('amenities')

  // Validate filters and detect conflicts
  useEffect(() => {
    const newConflicts: FilterConflict[] = []

    // Check for conflicting proximity filters
    const proximityAmenities = criteria.proximity_filters?.map(f => f.amenity_type) || []
    const duplicateAmenities = proximityAmenities.filter((item, index) => proximityAmenities.indexOf(item) !== index)

    if (duplicateAmenities.length > 0) {
      newConflicts.push({
        type: 'warning',
        message: `Duplicate amenity filters detected: ${duplicateAmenities.join(', ')}. Consider combining or removing duplicates.`,
        affectedFilters: ['proximity_filters']
      })
    }

    // Check for unrealistic commute constraints
    const commuteFilters = criteria.commute_filters || []
    const shortCommutes = commuteFilters.filter(f => f.max_commute_minutes < 10)
    if (shortCommutes.length > 0) {
      newConflicts.push({
        type: 'warning',
        message: 'Very short commute times (under 10 minutes) may limit available properties significantly',
        affectedFilters: ['commute_filters']
      })
    }

    // Check for commute filters without transport modes
    const emptyTransportModes = commuteFilters.filter(f => f.transport_modes.length === 0)
    if (emptyTransportModes.length > 0) {
      newConflicts.push({
        type: 'error',
        message: 'Commute filters must have at least one transport mode selected',
        affectedFilters: ['commute_filters']
      })
    }

    // Check for commute filters without destination
    const emptyDestinations = commuteFilters.filter(f => !f.destination_address.trim())
    if (emptyDestinations.length > 0) {
      newConflicts.push({
        type: 'error',
        message: 'Commute filters must have a destination address specified',
        affectedFilters: ['commute_filters']
      })
    }

    // Check for conflicting environmental filters
    const envFilters = criteria.environmental_filters
    if (envFilters?.max_air_pollution_level && envFilters.max_air_pollution_level < 15) {
      newConflicts.push({
        type: 'warning',
        message: 'Very strict air quality requirements (AQI < 15) may severely limit results',
        affectedFilters: ['environmental_filters']
      })
    }

    if (envFilters?.max_noise_level && envFilters.max_noise_level < 40) {
      newConflicts.push({
        type: 'warning',
        message: 'Very strict noise requirements (< 40dB) may severely limit results in urban areas',
        affectedFilters: ['environmental_filters']
      })
    }

    // Check for proximity filters with zero distance
    const zeroDistanceFilters = criteria.proximity_filters?.filter(f => f.max_distance === 0) || []
    if (zeroDistanceFilters.length > 0) {
      newConflicts.push({
        type: 'error',
        message: 'Proximity filters must have a distance greater than 0',
        affectedFilters: ['proximity_filters']
      })
    }

    // Check for excessive number of filters that might impact performance
    const totalFilters = (criteria.proximity_filters?.length || 0) + (criteria.commute_filters?.length || 0)
    if (totalFilters > 10) {
      newConflicts.push({
        type: 'warning',
        message: 'Large number of filters may impact search performance. Consider using presets or reducing filters.',
        affectedFilters: ['proximity_filters', 'commute_filters']
      })
    }

    setConflicts(newConflicts)
  }, [criteria])

  const updateProximityFilters = (filters: ProximityFilter[]) => {
    onCriteriaChange({
      ...criteria,
      proximity_filters: filters
    })
  }

  const updateEnvironmentalFilters = (filters: EnvironmentalFilter) => {
    onCriteriaChange({
      ...criteria,
      environmental_filters: filters
    })
  }

  const updateCommuteFilters = (filters: CommuteFilter[]) => {
    onCriteriaChange({
      ...criteria,
      commute_filters: filters
    })
  }

  const addProximityFilter = () => {
    const newFilter: ProximityFilter = {
      amenity_type: 'park',
      max_distance: 1000,
      distance_unit: 'meters',
      walking_distance: true
    }
    updateProximityFilters([...(criteria.proximity_filters || []), newFilter])
  }

  const removeProximityFilter = (index: number) => {
    const filters = [...(criteria.proximity_filters || [])]
    filters.splice(index, 1)
    updateProximityFilters(filters)
  }

  const updateProximityFilter = (index: number, filter: ProximityFilter) => {
    const filters = [...(criteria.proximity_filters || [])]
    filters[index] = filter
    updateProximityFilters(filters)
  }

  const addCommuteFilter = () => {
    const newFilter: CommuteFilter = {
      destination_address: '',
      max_commute_minutes: 30,
      transport_modes: ['public_transport']
    }
    updateCommuteFilters([...(criteria.commute_filters || []), newFilter])
  }

  const removeCommuteFilter = (index: number) => {
    const filters = [...(criteria.commute_filters || [])]
    filters.splice(index, 1)
    updateCommuteFilters(filters)
  }

  const updateCommuteFilter = (index: number, filter: CommuteFilter) => {
    const filters = [...(criteria.commute_filters || [])]
    filters[index] = filter
    updateCommuteFilters(filters)
  }

  const applyPreset = (preset: FilterPreset) => {
    const newCriteria = {
      ...criteria,
      ...preset.criteria,
      // Merge proximity filters instead of replacing
      proximity_filters: [
        ...(criteria.proximity_filters || []),
        ...(preset.criteria.proximity_filters || [])
      ]
    }
    onCriteriaChange(newCriteria)
  }

  const clearAllFilters = () => {
    onCriteriaChange({
      ...criteria,
      proximity_filters: [],
      environmental_filters: undefined,
      commute_filters: []
    })
  }

  if (!isVisible) {
    return (
      <button
        onClick={onToggleVisibility}
        className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        data-testid="show-filters-button"
      >
        <AdjustmentsHorizontalIcon className="h-5 w-5" />
        Advanced Filters
      </button>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg" data-testid="advanced-filters">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Advanced Filters</h3>
        <button
          onClick={onToggleVisibility}
          className="p-1 hover:bg-gray-100 rounded-md transition-colors"
          data-testid="close-filters-button"
        >
          <XMarkIcon className="h-5 w-5" />
        </button>
      </div>

      {/* Conflicts Display */}
      {conflicts.length > 0 && (
        <div className="p-4 border-b border-gray-200" data-testid="filter-conflicts" role="alert" aria-live="polite">
          {conflicts.map((conflict, index) => (
            <div
              key={index}
              className={`flex items-start gap-2 p-3 rounded-md mb-2 last:mb-0 ${conflict.type === 'error' ? 'bg-red-50 text-red-800 border border-red-200' : 'bg-yellow-50 text-yellow-800 border border-yellow-200'
                }`}
              role={conflict.type === 'error' ? 'alert' : 'status'}
            >
              <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div className="flex-1">
                <span className="text-sm font-medium">
                  {conflict.type === 'error' ? 'Error: ' : 'Warning: '}
                </span>
                <span className="text-sm">{conflict.message}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        {[
          { id: 'amenities', label: 'Amenities' },
          { id: 'commute', label: 'Commute' },
          { id: 'environment', label: 'Environment' },
          { id: 'presets', label: 'Presets' }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === tab.id
              ? 'border-primary-500 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            data-testid={`tab-${tab.id}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="p-4 max-h-96 overflow-y-auto">
        {activeTab === 'amenities' && (
          <div data-testid="amenities-tab">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-medium text-gray-900">Proximity to Amenities</h4>
              <button
                onClick={addProximityFilter}
                className="flex items-center gap-1 px-3 py-1 text-sm bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
                data-testid="add-proximity-filter"
              >
                <PlusIcon className="h-4 w-4" />
                Add Filter
              </button>
            </div>

            <div className="space-y-4">
              {(criteria.proximity_filters || []).map((filter, index) => (
                <div key={index} className="p-4 border border-gray-200 rounded-lg" data-testid={`proximity-filter-${index}`}>
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-medium text-gray-900">Amenity Filter {index + 1}</span>
                    <button
                      onClick={() => removeProximityFilter(index)}
                      className="text-red-600 hover:text-red-800 transition-colors"
                      data-testid={`remove-proximity-filter-${index}`}
                    >
                      <XMarkIcon className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Amenity Type
                      </label>
                      <select
                        value={filter.amenity_type}
                        onChange={(e) => updateProximityFilter(index, {
                          ...filter,
                          amenity_type: e.target.value as any
                        })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        data-testid={`amenity-type-${index}`}
                      >
                        {AMENITY_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.icon} {option.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Max Distance
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="number"
                          value={filter.max_distance}
                          onChange={(e) => updateProximityFilter(index, {
                            ...filter,
                            max_distance: parseInt(e.target.value) || 0
                          })}
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                          min="0"
                          data-testid={`max-distance-${index}`}
                        />
                        <select
                          value={filter.distance_unit}
                          onChange={(e) => updateProximityFilter(index, {
                            ...filter,
                            distance_unit: e.target.value as any
                          })}
                          className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                          data-testid={`distance-unit-${index}`}
                        >
                          <option value="meters">m</option>
                          <option value="kilometers">km</option>
                          <option value="miles">mi</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div className="mt-3">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={filter.walking_distance}
                        onChange={(e) => updateProximityFilter(index, {
                          ...filter,
                          walking_distance: e.target.checked
                        })}
                        className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        data-testid={`walking-distance-${index}`}
                      />
                      <span className="text-sm text-gray-700">Walking distance (vs straight line)</span>
                    </label>
                  </div>
                </div>
              ))}

              {(criteria.proximity_filters || []).length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <p>No amenity filters added yet.</p>
                  <p className="text-sm">Click "Add Filter" to get started.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'commute' && (
          <div data-testid="commute-tab">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-medium text-gray-900">Commute Constraints</h4>
              <button
                onClick={addCommuteFilter}
                className="flex items-center gap-1 px-3 py-1 text-sm bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
                data-testid="add-commute-filter"
              >
                <PlusIcon className="h-4 w-4" />
                Add Commute
              </button>
            </div>

            <div className="space-y-4">
              {(criteria.commute_filters || []).map((filter, index) => (
                <div key={index} className="p-4 border border-gray-200 rounded-lg" data-testid={`commute-filter-${index}`}>
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-medium text-gray-900">Commute {index + 1}</span>
                    <button
                      onClick={() => removeCommuteFilter(index)}
                      className="text-red-600 hover:text-red-800 transition-colors"
                      data-testid={`remove-commute-filter-${index}`}
                    >
                      <XMarkIcon className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Destination Address
                      </label>
                      <input
                        type="text"
                        value={filter.destination_address}
                        onChange={(e) => updateCommuteFilter(index, {
                          ...filter,
                          destination_address: e.target.value
                        })}
                        placeholder="e.g., London Bridge Station, SW1A 1AA"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        data-testid={`destination-address-${index}`}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Max Commute Time (minutes)
                      </label>
                      <input
                        type="number"
                        value={filter.max_commute_minutes}
                        onChange={(e) => updateCommuteFilter(index, {
                          ...filter,
                          max_commute_minutes: parseInt(e.target.value) || 0
                        })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        min="1"
                        max="180"
                        data-testid={`max-commute-minutes-${index}`}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Transport Modes
                      </label>
                      <div className="grid grid-cols-2 gap-2">
                        {TRANSPORT_MODES.map((mode) => (
                          <label key={mode.value} className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={filter.transport_modes.includes(mode.value)}
                              onChange={(e) => {
                                const modes = e.target.checked
                                  ? [...filter.transport_modes, mode.value]
                                  : filter.transport_modes.filter(m => m !== mode.value)
                                updateCommuteFilter(index, {
                                  ...filter,
                                  transport_modes: modes
                                })
                              }}
                              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                              data-testid={`transport-mode-${mode.value}-${index}`}
                            />
                            <span className="text-sm text-gray-700">
                              {mode.icon} {mode.label}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {(criteria.commute_filters || []).length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <p>No commute filters added yet.</p>
                  <p className="text-sm">Click "Add Commute" to get started.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'environment' && (
          <div data-testid="environment-tab">
            <h4 className="font-medium text-gray-900 mb-4">Environmental Preferences</h4>

            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Air Pollution Level (AQI)
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={criteria.environmental_filters?.max_air_pollution_level || 50}
                  onChange={(e) => updateEnvironmentalFilters({
                    ...criteria.environmental_filters,
                    max_air_pollution_level: parseInt(e.target.value)
                  })}
                  className="w-full"
                  data-testid="air-pollution-slider"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Clean (0)</span>
                  <span className="font-medium">
                    {criteria.environmental_filters?.max_air_pollution_level || 50}
                  </span>
                  <span>Polluted (100)</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Noise Level (dB)
                </label>
                <input
                  type="range"
                  min="30"
                  max="80"
                  value={criteria.environmental_filters?.max_noise_level || 60}
                  onChange={(e) => updateEnvironmentalFilters({
                    ...criteria.environmental_filters,
                    max_noise_level: parseInt(e.target.value)
                  })}
                  className="w-full"
                  data-testid="noise-level-slider"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Quiet (30)</span>
                  <span className="font-medium">
                    {criteria.environmental_filters?.max_noise_level || 60}
                  </span>
                  <span>Loud (80)</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Min Green Space Proximity (meters)
                </label>
                <input
                  type="number"
                  value={criteria.environmental_filters?.min_green_space_proximity || ''}
                  onChange={(e) => updateEnvironmentalFilters({
                    ...criteria.environmental_filters,
                    min_green_space_proximity: parseInt(e.target.value) || undefined
                  })}
                  placeholder="e.g., 200"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  min="0"
                  data-testid="green-space-proximity"
                />
              </div>

              <div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={criteria.environmental_filters?.avoid_flood_risk || false}
                    onChange={(e) => updateEnvironmentalFilters({
                      ...criteria.environmental_filters,
                      avoid_flood_risk: e.target.checked
                    })}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    data-testid="avoid-flood-risk"
                  />
                  <span className="text-sm text-gray-700">Avoid flood risk areas</span>
                </label>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'presets' && (
          <div data-testid="presets-tab">
            <h4 className="font-medium text-gray-900 mb-4">Filter Presets</h4>

            <div className="space-y-3">
              {DEFAULT_PRESETS.map((preset) => (
                <div
                  key={preset.id}
                  className="p-4 border border-gray-200 rounded-lg hover:border-primary-300 transition-colors"
                  data-testid={`preset-${preset.id}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h5 className="font-medium text-gray-900 mb-1">{preset.name}</h5>
                      <p className="text-sm text-gray-600 mb-3">{preset.description}</p>

                      <div className="text-xs text-gray-500">
                        {preset.criteria.proximity_filters && (
                          <div>
                            Amenities: {preset.criteria.proximity_filters.map(f => f.amenity_type).join(', ')}
                          </div>
                        )}
                        {preset.criteria.environmental_filters && (
                          <div>Environmental filters included</div>
                        )}
                      </div>
                    </div>

                    <button
                      onClick={() => applyPreset(preset)}
                      className="flex items-center gap-1 px-3 py-1 text-sm bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
                      data-testid={`apply-preset-${preset.id}`}
                    >
                      <BookmarkIcon className="h-4 w-4" />
                      Apply
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Active Filters Summary */}
      {((criteria.proximity_filters?.length || 0) > 0 || 
        (criteria.commute_filters?.length || 0) > 0 || 
        criteria.environmental_filters) && (
        <div className="p-4 border-t border-gray-200 bg-gray-50" data-testid="active-filters-summary">
          <h4 className="text-sm font-medium text-gray-900 mb-2">Active Filters Summary</h4>
          <div className="flex flex-wrap gap-2">
            {(criteria.proximity_filters || []).map((filter, index) => (
              <span
                key={`proximity-${index}`}
                className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800"
              >
                {AMENITY_OPTIONS.find(opt => opt.value === filter.amenity_type)?.icon} {filter.max_distance}{filter.distance_unit === 'meters' ? 'm' : filter.distance_unit === 'kilometers' ? 'km' : 'mi'}
              </span>
            ))}
            {(criteria.commute_filters || []).map((filter, index) => (
              <span
                key={`commute-${index}`}
                className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-800"
              >
                🚌 {filter.max_commute_minutes}min to {filter.destination_address.slice(0, 20)}...
              </span>
            ))}
            {criteria.environmental_filters?.max_air_pollution_level && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-purple-100 text-purple-800">
                🌬️ AQI ≤ {criteria.environmental_filters.max_air_pollution_level}
              </span>
            )}
            {criteria.environmental_filters?.max_noise_level && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-purple-100 text-purple-800">
                🔇 ≤ {criteria.environmental_filters.max_noise_level}dB
              </span>
            )}
            {criteria.environmental_filters?.avoid_flood_risk && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-purple-100 text-purple-800">
                🌊 No flood risk
              </span>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between p-4 border-t border-gray-200 bg-gray-50">
        <button
          onClick={clearAllFilters}
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="clear-all-filters"
          disabled={
            (criteria.proximity_filters?.length || 0) === 0 && 
            (criteria.commute_filters?.length || 0) === 0 && 
            !criteria.environmental_filters
          }
        >
          Clear All Filters
        </button>

        <div className="flex gap-2">
          <button
            onClick={onToggleVisibility}
            className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            data-testid="cancel-filters"
          >
            Cancel
          </button>
          <button
            onClick={onApplyFilters}
            className={`px-4 py-2 text-sm rounded-md transition-colors ${
              conflicts.some(c => c.type === 'error')
                ? 'bg-gray-400 text-gray-600 cursor-not-allowed'
                : 'bg-primary-600 text-white hover:bg-primary-700'
            }`}
            data-testid="apply-filters"
            disabled={conflicts.some(c => c.type === 'error')}
            title={conflicts.some(c => c.type === 'error') ? 'Please fix errors before applying filters' : 'Apply filters to search'}
          >
            Apply Filters
          </button>
        </div>
      </div>
    </div>
  )
}