import axios from 'axios'
import { SearchCriteria, SearchResult } from '@/types/property'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor for authentication if needed
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('authToken')
      // Redirect to login if needed
    }
    return Promise.reject(error)
  }
)

export interface AutocompleteSuggestion {
  text: string
  description: string
  category: string
  confidence: number
  filters: Record<string, any>
}

export interface AutocompleteResponse {
  query: string
  suggestions: AutocompleteSuggestion[]
}

export interface ParsedEntity {
  type: string
  value: string
  confidence: number
  text: string
  position: [number, number]
}

export interface ParseResponse {
  query: string
  parsed_criteria: SearchCriteria
  extracted_entities: ParsedEntity[]
  intent: string
}

export interface SearchExamplesResponse {
  examples: string[]
  description: string
}

export const searchAPI = {
  /**
   * Search for properties based on criteria
   */
  async searchProperties(criteria: SearchCriteria, useCache = true): Promise<SearchResult> {
    const response = await apiClient.post('/api/search/', criteria, {
      params: { use_cache: useCache }
    })
    return response.data
  },

  /**
   * Get autocomplete suggestions for a query
   */
  async getAutocompleteSuggestions(query: string, limit = 10): Promise<AutocompleteResponse> {
    const response = await apiClient.get('/api/search/autocomplete', {
      params: { q: query, limit }
    })
    return response.data
  },

  /**
   * Parse a natural language query into structured criteria
   */
  async parseNaturalLanguageQuery(query: string): Promise<ParseResponse> {
    const response = await apiClient.post('/api/search/parse', null, {
      params: { query }
    })
    return response.data
  },

  /**
   * Get example search queries
   */
  async getSearchExamples(): Promise<SearchExamplesResponse> {
    const response = await apiClient.get('/api/search/examples')
    return response.data
  },

  /**
   * Validate search criteria
   */
  async validateSearchCriteria(criteria: SearchCriteria) {
    const response = await apiClient.get('/api/search/validate', {
      params: criteria
    })
    return response.data
  },

  /**
   * Get search aggregations for faceted filtering
   */
  async getSearchAggregations(criteria: SearchCriteria) {
    const response = await apiClient.get('/api/search/aggregations', {
      params: criteria
    })
    return response.data
  }
}

export const propertyAPI = {
  /**
   * Get property details by ID
   */
  async getPropertyById(id: string) {
    const response = await apiClient.get(`/api/properties/${id}`)
    return response.data
  },

  /**
   * Get similar properties
   */
  async getSimilarProperties(id: string, limit = 5) {
    const response = await apiClient.get(`/api/properties/${id}/similar`, {
      params: { limit }
    })
    return response.data
  }
}

export const userAPI = {
  /**
   * Get user's saved searches
   */
  async getSavedSearches() {
    const response = await apiClient.get('/api/users/saved-searches')
    return response.data
  },

  /**
   * Save a search
   */
  async saveSearch(name: string, query: string, criteria: SearchCriteria) {
    const response = await apiClient.post('/api/users/saved-searches', {
      name,
      query,
      criteria
    })
    return response.data
  },

  /**
   * Delete a saved search
   */
  async deleteSavedSearch(id: string) {
    const response = await apiClient.delete(`/api/users/saved-searches/${id}`)
    return response.data
  },

  /**
   * Get user's favorite properties
   */
  async getFavorites() {
    const response = await apiClient.get('/api/users/favorites')
    return response.data
  },

  /**
   * Add property to favorites
   */
  async addToFavorites(propertyId: string) {
    const response = await apiClient.post('/api/users/favorites', {
      property_id: propertyId
    })
    return response.data
  },

  /**
   * Remove property from favorites
   */
  async removeFromFavorites(propertyId: string) {
    const response = await apiClient.delete(`/api/users/favorites/${propertyId}`)
    return response.data
  }
}

export default apiClient