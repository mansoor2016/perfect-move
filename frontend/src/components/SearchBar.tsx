'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { MagnifyingGlassIcon, ClockIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { SearchCriteria } from '@/types/property'
import { useDebounce } from '@/hooks/useDebounce'
import { searchAPI } from '@/services/api'

interface AutocompleteSuggestion {
  text: string
  description: string
  category: string
  confidence: number
  filters: Record<string, any>
}

interface ParsedQuery {
  parsed_criteria: SearchCriteria
  extracted_entities: Array<{
    type: string
    value: string
    confidence: number
    text: string
    position: [number, number]
  }>
  intent: string
}

interface SearchBarProps {
  onSearch: (criteria: SearchCriteria) => void
  isLoading: boolean
  savedSearches?: Array<{ id: string; name: string; query: string; criteria: SearchCriteria }>
}

export default function SearchBar({ onSearch, isLoading, savedSearches = [] }: SearchBarProps) {
  const [query, setQuery] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [suggestions, setSuggestions] = useState<AutocompleteSuggestion[]>([])
  const [searchHistory, setSearchHistory] = useState<string[]>([])
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(-1)
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false)
  
  const inputRef = useRef<HTMLInputElement>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)
  
  // Debounce the query to avoid too many API calls
  const debouncedQuery = useDebounce(query, 300)

  // Load search history from localStorage on mount
  useEffect(() => {
    const history = localStorage.getItem('searchHistory')
    if (history) {
      try {
        setSearchHistory(JSON.parse(history))
      } catch (e) {
        console.error('Failed to parse search history:', e)
      }
    }
  }, [])

  // Save search history to localStorage
  const saveToHistory = useCallback((searchQuery: string) => {
    if (!searchQuery.trim()) return
    
    const newHistory = [searchQuery, ...searchHistory.filter(h => h !== searchQuery)].slice(0, 10)
    setSearchHistory(newHistory)
    localStorage.setItem('searchHistory', JSON.stringify(newHistory))
  }, [searchHistory])

  // Fetch autocomplete suggestions
  const fetchSuggestions = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim() || searchQuery.length < 2) {
      setSuggestions([])
      return
    }

    setIsLoadingSuggestions(true)
    try {
      const response = await searchAPI.getAutocompleteSuggestions(searchQuery)
      setSuggestions(response.suggestions || [])
    } catch (error) {
      console.error('Failed to fetch suggestions:', error)
      setSuggestions([])
    } finally {
      setIsLoadingSuggestions(false)
    }
  }, [])

  // Fetch suggestions when debounced query changes
  useEffect(() => {
    if (debouncedQuery && showSuggestions) {
      fetchSuggestions(debouncedQuery)
    } else {
      setSuggestions([])
    }
  }, [debouncedQuery, showSuggestions, fetchSuggestions])

  // Parse natural language query and execute search
  const executeSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) return

    try {
      // Parse the natural language query
      const parseResponse = await searchAPI.parseNaturalLanguageQuery(searchQuery)
      const parsedQuery = parseResponse as ParsedQuery
      
      // Use parsed criteria or fall back to basic search
      const criteria = parsedQuery.parsed_criteria || {
        property_types: ['house', 'flat'],
        status: ['for_sale'],
        areas: searchQuery ? [searchQuery] : [],
        proximity_filters: [],
        commute_filters: [],
        limit: 50,
        offset: 0,
        sort_by: 'relevance'
      }
      
      saveToHistory(searchQuery)
      onSearch(criteria)
    } catch (error) {
      console.error('Failed to parse query:', error)
      
      // Fall back to basic search
      const criteria: SearchCriteria = {
        property_types: ['house', 'flat'],
        status: ['for_sale'],
        areas: searchQuery ? [searchQuery] : [],
        proximity_filters: [],
        commute_filters: [],
        limit: 50,
        offset: 0,
        sort_by: 'relevance'
      }
      
      saveToHistory(searchQuery)
      onSearch(criteria)
    }
  }, [onSearch, saveToHistory])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setShowSuggestions(false)
    executeSearch(query)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setQuery(value)
    setSelectedSuggestionIndex(-1)
    setShowSuggestions(true)
  }

  const handleInputFocus = () => {
    setShowSuggestions(true)
  }

  const handleInputBlur = () => {
    // Delay hiding suggestions to allow for clicks
    setTimeout(() => setShowSuggestions(false), 200)
  }

  const handleSuggestionClick = (suggestion: AutocompleteSuggestion) => {
    setQuery(suggestion.text)
    setShowSuggestions(false)
    executeSearch(suggestion.text)
  }

  const handleHistoryClick = (historyItem: string) => {
    setQuery(historyItem)
    setShowSuggestions(false)
    executeSearch(historyItem)
  }

  const handleSavedSearchClick = (savedSearch: { query: string; criteria: SearchCriteria }) => {
    setQuery(savedSearch.query)
    setShowSuggestions(false)
    onSearch(savedSearch.criteria)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showSuggestions) return

    const totalItems = suggestions.length + searchHistory.length + savedSearches.length

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedSuggestionIndex(prev => 
          prev < totalItems - 1 ? prev + 1 : -1
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedSuggestionIndex(prev => 
          prev > -1 ? prev - 1 : totalItems - 1
        )
        break
      case 'Enter':
        if (selectedSuggestionIndex >= 0) {
          e.preventDefault()
          if (selectedSuggestionIndex < suggestions.length) {
            handleSuggestionClick(suggestions[selectedSuggestionIndex])
          } else if (selectedSuggestionIndex < suggestions.length + searchHistory.length) {
            const historyIndex = selectedSuggestionIndex - suggestions.length
            handleHistoryClick(searchHistory[historyIndex])
          } else {
            const savedSearchIndex = selectedSuggestionIndex - suggestions.length - searchHistory.length
            handleSavedSearchClick(savedSearches[savedSearchIndex])
          }
        }
        break
      case 'Escape':
        setShowSuggestions(false)
        setSelectedSuggestionIndex(-1)
        break
    }
  }

  const clearQuery = () => {
    setQuery('')
    setShowSuggestions(false)
    inputRef.current?.focus()
  }

  const shouldShowDropdown = showSuggestions && (
    suggestions.length > 0 || 
    searchHistory.length > 0 || 
    savedSearches.length > 0 ||
    isLoadingSuggestions
  )

  return (
    <div className="w-full max-w-4xl mx-auto relative">
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={handleInputChange}
            onFocus={handleInputFocus}
            onBlur={handleInputBlur}
            onKeyDown={handleKeyDown}
            placeholder="Search for properties... (e.g., '2 bed flat near train station under £400k')"
            className="w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-lg"
            disabled={isLoading}
            autoComplete="off"
            data-testid="search-input"
          />
          {query && (
            <button
              type="button"
              onClick={clearQuery}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400 hover:text-gray-600"
              data-testid="clear-button"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          )}
        </div>
        
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="absolute right-2 top-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md font-medium transition-colors"
          data-testid="search-button"
        >
          {isLoading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {/* Autocomplete Dropdown */}
      {shouldShowDropdown && (
        <div
          ref={suggestionsRef}
          className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto"
          data-testid="suggestions-dropdown"
        >
          {isLoadingSuggestions && (
            <div className="px-4 py-3 text-gray-500 text-sm">
              Loading suggestions...
            </div>
          )}

          {/* Intelligent Suggestions */}
          {suggestions.length > 0 && (
            <div>
              <div className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide border-b">
                Suggestions
              </div>
              {suggestions.map((suggestion, index) => (
                <button
                  key={`suggestion-${index}`}
                  type="button"
                  onClick={() => handleSuggestionClick(suggestion)}
                  className={`w-full text-left px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0 ${
                    selectedSuggestionIndex === index ? 'bg-primary-50' : ''
                  }`}
                  data-testid={`suggestion-${index}`}
                >
                  <div className="font-medium text-gray-900">{suggestion.text}</div>
                  <div className="text-sm text-gray-600">{suggestion.description}</div>
                  <div className="text-xs text-primary-600 mt-1">{suggestion.category}</div>
                </button>
              ))}
            </div>
          )}

          {/* Search History */}
          {searchHistory.length > 0 && (
            <div>
              <div className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide border-b">
                Recent Searches
              </div>
              {searchHistory.slice(0, 5).map((historyItem, index) => (
                <button
                  key={`history-${index}`}
                  type="button"
                  onClick={() => handleHistoryClick(historyItem)}
                  className={`w-full text-left px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0 flex items-center ${
                    selectedSuggestionIndex === suggestions.length + index ? 'bg-primary-50' : ''
                  }`}
                  data-testid={`history-${index}`}
                >
                  <ClockIcon className="h-4 w-4 text-gray-400 mr-3 flex-shrink-0" />
                  <span className="text-gray-700 truncate">{historyItem}</span>
                </button>
              ))}
            </div>
          )}

          {/* Saved Searches */}
          {savedSearches.length > 0 && (
            <div>
              <div className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide border-b">
                Saved Searches
              </div>
              {savedSearches.slice(0, 3).map((savedSearch, index) => (
                <button
                  key={`saved-${index}`}
                  type="button"
                  onClick={() => handleSavedSearchClick(savedSearch)}
                  className={`w-full text-left px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0 ${
                    selectedSuggestionIndex === suggestions.length + searchHistory.length + index ? 'bg-primary-50' : ''
                  }`}
                  data-testid={`saved-search-${index}`}
                >
                  <div className="font-medium text-gray-900">{savedSearch.name}</div>
                  <div className="text-sm text-gray-600 truncate">{savedSearch.query}</div>
                </button>
              ))}
            </div>
          )}

          {/* No results message */}
          {!isLoadingSuggestions && suggestions.length === 0 && searchHistory.length === 0 && savedSearches.length === 0 && query.trim() && (
            <div className="px-4 py-3 text-gray-500 text-sm">
              No suggestions found. Try typing a location, property type, or feature.
            </div>
          )}
        </div>
      )}
    </div>
  )
}