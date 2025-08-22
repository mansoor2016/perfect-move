'use client'

import { useState } from 'react'
import SearchBar from '@/components/SearchBar'
import MockPropertyMap from '@/components/MockPropertyMap'
import AdvancedFilters from '@/components/AdvancedFilters'
import PropertyResults from '@/components/PropertyResults'
import { SearchCriteria, Property } from '@/types/property'

// Mock data for testing
const mockProperties: Property[] = [
  {
    id: '1',
    title: '2 Bedroom Flat in Central London',
    description: 'Modern apartment with great transport links',
    price: 450000,
    property_type: 'flat',
    status: 'for_sale',
    bedrooms: 2,
    bathrooms: 1,
    location: {
      latitude: 51.5074,
      longitude: -0.1278,
      address: '123 Oxford Street, London W1D 2HX',
      postcode: 'W1D 2HX',
      area: 'Central London',
      city: 'London'
    },
    images: [],
    features: ['Modern Kitchen', 'Balcony', 'Parking'],
    energy_rating: 'B',
    council_tax_band: 'D',
    tenure: 'Leasehold',
    floor_area_sqft: 850,
    garden: false,
    parking: true,
    lineage: {
      source: 'test',
      source_id: 'test-1',
      last_updated: '2024-01-01T00:00:00Z',
      reliability_score: 0.9
    },
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  },
  {
    id: '2',
    title: '3 Bedroom House in Suburbs',
    description: 'Family home with garden and parking',
    price: 650000,
    property_type: 'house',
    status: 'for_sale',
    bedrooms: 3,
    bathrooms: 2,
    location: {
      latitude: 51.4994,
      longitude: -0.1245,
      address: '456 Residential Road, London SW1A 1AA',
      postcode: 'SW1A 1AA',
      area: 'Westminster',
      city: 'London'
    },
    images: [],
    features: ['Garden', 'Parking', 'Modern Kitchen', 'Fireplace'],
    energy_rating: 'C',
    council_tax_band: 'E',
    tenure: 'Freehold',
    floor_area_sqft: 1200,
    garden: true,
    parking: true,
    lineage: {
      source: 'test',
      source_id: 'test-2',
      last_updated: '2024-01-01T00:00:00Z',
      reliability_score: 0.95
    },
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  }
]

export default function Home() {
  const [searchCriteria, setSearchCriteria] = useState<SearchCriteria>({
    property_types: ['house', 'flat'],
    status: ['for_sale'],
    areas: [],
    proximity_filters: [],
    commute_filters: [],
    limit: 50,
    offset: 0,
    sort_by: 'relevance'
  })
  const [properties, setProperties] = useState<Property[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false)

  const handleSearch = async (criteria: SearchCriteria) => {
    setIsLoading(true)
    setSearchCriteria(criteria)

    try {
      console.log('Searching with criteria:', criteria)

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000))

      // Mock filtering logic for demonstration
      let filteredProperties = [...mockProperties]

      // Filter by property types
      if (criteria.property_types.length > 0) {
        filteredProperties = filteredProperties.filter(p =>
          criteria.property_types.includes(p.property_type)
        )
      }

      // Filter by price range
      if (criteria.min_price) {
        filteredProperties = filteredProperties.filter(p => p.price >= criteria.min_price!)
      }
      if (criteria.max_price) {
        filteredProperties = filteredProperties.filter(p => p.price <= criteria.max_price!)
      }

      // Filter by bedrooms
      if (criteria.min_bedrooms) {
        filteredProperties = filteredProperties.filter(p =>
          p.bedrooms && p.bedrooms >= criteria.min_bedrooms!
        )
      }
      if (criteria.max_bedrooms) {
        filteredProperties = filteredProperties.filter(p =>
          p.bedrooms && p.bedrooms <= criteria.max_bedrooms!
        )
      }

      // Filter by areas (simple text matching)
      if (criteria.areas.length > 0) {
        filteredProperties = filteredProperties.filter(p =>
          criteria.areas.some(area =>
            p.location.address.toLowerCase().includes(area.toLowerCase()) ||
            p.location.area?.toLowerCase().includes(area.toLowerCase()) ||
            p.title.toLowerCase().includes(area.toLowerCase())
          )
        )
      }

      setProperties(filteredProperties)
    } catch (error) {
      console.error('Search error:', error)
      setProperties([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleApplyFilters = () => {
    handleSearch(searchCriteria)
    setShowAdvancedFilters(false)
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8 text-center">
          Advanced Property Search
        </h1>

        <div className="mb-8 space-y-4">
          <SearchBar
            onSearch={handleSearch}
            isLoading={isLoading}
            savedSearches={[
              {
                id: '1',
                name: 'Family Home Search',
                query: '3 bedroom house with garden',
                criteria: {
                  ...searchCriteria,
                  property_types: ['house'],
                  min_bedrooms: 3,
                  must_have_garden: true
                }
              }
            ]}
          />

          <div className="flex justify-center">
            <AdvancedFilters
              criteria={searchCriteria}
              onCriteriaChange={setSearchCriteria}
              onApplyFilters={handleApplyFilters}
              isVisible={showAdvancedFilters}
              onToggleVisibility={() => setShowAdvancedFilters(!showAdvancedFilters)}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="order-2 lg:order-1">
            <PropertyResults properties={properties} isLoading={isLoading} />
          </div>

          <div className="order-1 lg:order-2">
            <MockPropertyMap properties={properties} searchCriteria={searchCriteria} />
          </div>
        </div>

        {/* Debug Panel */}
        <div className="mt-8 p-4 bg-white rounded-lg border border-gray-200">
          <h3 className="font-semibold text-gray-800 mb-2">Debug Information</h3>
          <div className="text-sm text-gray-600 space-y-1">
            <div>Properties found: {properties.length}</div>
            <div>Loading: {isLoading ? 'Yes' : 'No'}</div>
            <div>Advanced filters visible: {showAdvancedFilters ? 'Yes' : 'No'}</div>
            <details className="mt-2">
              <summary className="cursor-pointer font-medium">Current Search Criteria</summary>
              <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-auto">
                {JSON.stringify(searchCriteria, null, 2)}
              </pre>
            </details>
          </div>
        </div>
      </div>
    </main>
  )
}