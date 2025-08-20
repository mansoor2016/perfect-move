'use client'

import { Property } from '@/types/property'
import { HeartIcon, MapPinIcon } from '@heroicons/react/24/outline'

interface PropertyResultsProps {
  properties: Property[]
  isLoading: boolean
}

export default function PropertyResults({ properties, isLoading }: PropertyResultsProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="bg-white rounded-lg border border-gray-200 p-4 animate-pulse">
            <div className="h-48 bg-gray-200 rounded-lg mb-4"></div>
            <div className="h-4 bg-gray-200 rounded mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    )
  }

  if (properties.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
        <p className="text-gray-600">
          No properties found. Try adjusting your search criteria.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-gray-900">
          {properties.length} Properties Found
        </h2>
      </div>
      
      {properties.map((property) => (
        <div key={property.id} className="bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
          {property.images.length > 0 && (
            <div className="h-48 bg-gray-200">
              <img
                src={property.images[0]}
                alt={property.title}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.currentTarget.style.display = 'none'
                }}
              />
            </div>
          )}
          
          <div className="p-4">
            <div className="flex justify-between items-start mb-2">
              <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
                {property.title}
              </h3>
              <button className="text-gray-400 hover:text-red-500 transition-colors">
                <HeartIcon className="h-5 w-5" />
              </button>
            </div>
            
            <p className="text-2xl font-bold text-primary-600 mb-2">
              £{property.price.toLocaleString()}
            </p>
            
            <div className="flex items-center text-gray-600 mb-2">
              <MapPinIcon className="h-4 w-4 mr-1" />
              <span className="text-sm">{property.location.address}</span>
            </div>
            
            <div className="flex items-center space-x-4 text-sm text-gray-600 mb-3">
              {property.bedrooms && (
                <span>{property.bedrooms} bed{property.bedrooms !== 1 ? 's' : ''}</span>
              )}
              {property.bathrooms && (
                <span>{property.bathrooms} bath{property.bathrooms !== 1 ? 's' : ''}</span>
              )}
              <span className="capitalize">{property.property_type}</span>
            </div>
            
            {property.features.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {property.features.slice(0, 3).map((feature, index) => (
                  <span
                    key={index}
                    className="inline-block bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded"
                  >
                    {feature}
                  </span>
                ))}
                {property.features.length > 3 && (
                  <span className="text-xs text-gray-500">
                    +{property.features.length - 3} more
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}