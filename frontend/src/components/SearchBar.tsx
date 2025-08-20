'use client'

import { useState } from 'react'
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import { SearchCriteria } from '@/types/property'

interface SearchBarProps {
  onSearch: (criteria: SearchCriteria) => void
  isLoading: boolean
}

export default function SearchBar({ onSearch, isLoading }: SearchBarProps) {
  const [query, setQuery] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Basic search criteria - will be enhanced in later tasks
    const criteria: SearchCriteria = {
      property_types: ['house', 'flat'],
      status: ['for_sale'],
      areas: query ? [query] : [],
      proximity_filters: [],
      commute_filters: [],
      limit: 50,
      offset: 0,
      sort_by: 'relevance'
    }
    
    onSearch(criteria)
  }

  return (
    <div className="w-full max-w-4xl mx-auto">
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search for properties... (e.g., 'London', 'near parks', 'within 10 minutes of train station')"
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-lg"
            disabled={isLoading}
          />
        </div>
        
        <div className="flex justify-between items-center mt-4">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-primary-600 hover:text-primary-700 text-sm font-medium"
          >
            {showAdvanced ? 'Hide' : 'Show'} Advanced Filters
          </button>
          
          <button
            type="submit"
            disabled={isLoading}
            className="bg-primary-600 hover:bg-primary-700 disabled:bg-gray-400 text-white px-6 py-2 rounded-lg font-medium transition-colors"
          >
            {isLoading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>
      
      {showAdvanced && (
        <div className="mt-6 p-4 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-600 text-sm">
            Advanced filters will be implemented in later tasks
          </p>
        </div>
      )}
    </div>
  )
}