'use client'

import { useState } from 'react'
import SearchBar from '@/components/SearchBar'
import PropertyMap from '@/components/PropertyMap'
import PropertyResults from '@/components/PropertyResults'
import { SearchCriteria, Property } from '@/types/property'

export default function Home() {
  const [searchCriteria, setSearchCriteria] = useState<SearchCriteria | null>(null)
  const [properties, setProperties] = useState<Property[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const handleSearch = async (criteria: SearchCriteria) => {
    setIsLoading(true)
    setSearchCriteria(criteria)
    
    try {
      // TODO: Implement API call to search properties
      console.log('Searching with criteria:', criteria)
      // Placeholder - will be implemented in later tasks
      setProperties([])
    } catch (error) {
      console.error('Search error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8 text-center">
          Advanced Property Search
        </h1>
        
        <div className="mb-8">
          <SearchBar onSearch={handleSearch} isLoading={isLoading} />
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="order-2 lg:order-1">
            <PropertyResults properties={properties} isLoading={isLoading} />
          </div>
          
          <div className="order-1 lg:order-2">
            <PropertyMap properties={properties} searchCriteria={searchCriteria} />
          </div>
        </div>
      </div>
    </main>
  )
}