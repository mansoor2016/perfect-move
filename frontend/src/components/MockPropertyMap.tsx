'use client'

import { Property, SearchCriteria } from '@/types/property'

interface PropertyMapProps {
  properties: Property[]
  searchCriteria: SearchCriteria | null
}

export default function MockPropertyMap({ properties, searchCriteria }: PropertyMapProps) {
  return (
    <div className="h-96 lg:h-[600px] rounded-lg overflow-hidden border border-gray-200 bg-gray-100 flex flex-col">
      <div className="bg-gray-200 p-4 border-b">
        <h3 className="font-semibold text-gray-800">Property Map (Mock)</h3>
        <p className="text-sm text-gray-600">
          {properties.length} properties found
          {searchCriteria && ` • Search criteria applied`}
        </p>
      </div>
      
      <div className="flex-1 p-4 overflow-y-auto">
        {properties.length > 0 ? (
          <div className="space-y-2">
            <h4 className="font-medium text-gray-700 mb-3">Property Locations:</h4>
            {properties.map((property, index) => (
              <div key={property.id} className="bg-white p-3 rounded border shadow-sm">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h5 className="font-medium text-gray-900">{property.title}</h5>
                    <p className="text-sm text-gray-600">£{property.price.toLocaleString()}</p>
                    <p className="text-xs text-gray-500 mt-1">{property.location.address}</p>
                  </div>
                  <div className="text-xs text-gray-400 ml-2">
                    📍 {property.location.latitude.toFixed(4)}, {property.location.longitude.toFixed(4)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-500">
              <div className="text-4xl mb-2">🗺️</div>
              <p>No properties to display on map</p>
              <p className="text-sm mt-1">Search for properties to see them here</p>
            </div>
          </div>
        )}
      </div>
      
      {searchCriteria && (
        <div className="bg-blue-50 p-3 border-t">
          <h4 className="font-medium text-blue-800 mb-2">Active Search Criteria:</h4>
          <div className="text-xs text-blue-700 space-y-1">
            {searchCriteria.areas.length > 0 && (
              <div>📍 Areas: {searchCriteria.areas.join(', ')}</div>
            )}
            {searchCriteria.property_types.length > 0 && (
              <div>🏠 Types: {searchCriteria.property_types.join(', ')}</div>
            )}
            {searchCriteria.min_price && (
              <div>💰 Min Price: £{searchCriteria.min_price.toLocaleString()}</div>
            )}
            {searchCriteria.max_price && (
              <div>💰 Max Price: £{searchCriteria.max_price.toLocaleString()}</div>
            )}
            {searchCriteria.proximity_filters.length > 0 && (
              <div>🎯 Proximity Filters: {searchCriteria.proximity_filters.length} active</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}