import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SearchBar from '../SearchBar'
import { searchAPI } from '@/services/api'
import { SearchCriteria } from '@/types/property'

// Mock the API service
jest.mock('@/services/api', () => ({
  searchAPI: {
    getAutocompleteSuggestions: jest.fn(),
    parseNaturalLanguageQuery: jest.fn(),
  }
}))

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
}
Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage
})

const mockOnSearch = jest.fn()

const defaultProps = {
  onSearch: mockOnSearch,
  isLoading: false,
}

const mockSuggestions = [
  {
    text: '2 bedroom flat near train station',
    description: 'Properties with 2 bedrooms close to public transport',
    category: 'Property Type + Amenity',
    confidence: 0.9,
    filters: { bedrooms: 2, amenities: ['train_station'] }
  },
  {
    text: 'house with garden under £400k',
    description: 'Houses with outdoor space within budget',
    category: 'Property Type + Feature + Price',
    confidence: 0.85,
    filters: { property_type: 'house', max_price: 400000, features: ['garden'] }
  }
]

const mockParsedQuery = {
  query: '2 bed flat near station',
  parsed_criteria: {
    property_types: ['flat'],
    status: ['for_sale'],
    min_bedrooms: 2,
    max_bedrooms: 2,
    proximity_filters: [{
      amenity_type: 'train_station' as const,
      max_distance: 1000,
      distance_unit: 'meters' as const,
      walking_distance: true
    }],
    areas: [],
    commute_filters: [],
    limit: 50,
    offset: 0,
    sort_by: 'relevance'
  },
  extracted_entities: [
    {
      type: 'bedrooms',
      value: '2',
      confidence: 0.95,
      text: '2 bed',
      position: [0, 5] as [number, number]
    },
    {
      type: 'property_type',
      value: 'flat',
      confidence: 0.9,
      text: 'flat',
      position: [6, 10] as [number, number]
    }
  ],
  intent: 'property_search'
}

describe('SearchBar', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockLocalStorage.getItem.mockReturnValue(null)
  })

  it('renders the search input with correct placeholder', () => {
    render(<SearchBar {...defaultProps} />)
    
    const input = screen.getByTestId('search-input')
    expect(input).toBeInTheDocument()
    expect(input).toHaveAttribute('placeholder', "Search for properties... (e.g., '2 bed flat near train station under £400k')")
  })

  it('updates input value when user types', async () => {
    const user = userEvent.setup()
    render(<SearchBar {...defaultProps} />)
    
    const input = screen.getByTestId('search-input')
    await user.type(input, 'test query')
    
    expect(input).toHaveValue('test query')
  })

  it('shows clear button when input has value', async () => {
    const user = userEvent.setup()
    render(<SearchBar {...defaultProps} />)
    
    const input = screen.getByTestId('search-input')
    await user.type(input, 'test')
    
    expect(screen.getByTestId('clear-button')).toBeInTheDocument()
  })

  it('clears input when clear button is clicked', async () => {
    const user = userEvent.setup()
    render(<SearchBar {...defaultProps} />)
    
    const input = screen.getByTestId('search-input')
    await user.type(input, 'test')
    
    const clearButton = screen.getByTestId('clear-button')
    await user.click(clearButton)
    
    expect(input).toHaveValue('')
  })

  it('disables input and search button when loading', () => {
    render(<SearchBar {...defaultProps} isLoading={true} />)
    
    const input = screen.getByTestId('search-input')
    const searchButton = screen.getByTestId('search-button')
    
    expect(input).toBeDisabled()
    expect(searchButton).toBeDisabled()
    expect(searchButton).toHaveTextContent('Searching...')
  })

  it('fetches autocomplete suggestions when user types', async () => {
    const user = userEvent.setup()
    const mockGetAutocompleteSuggestions = searchAPI.getAutocompleteSuggestions as jest.Mock
    mockGetAutocompleteSuggestions.mockResolvedValue({
      query: 'test',
      suggestions: mockSuggestions
    })

    render(<SearchBar {...defaultProps} />)
    
    const input = screen.getByTestId('search-input')
    await user.type(input, 'test')
    
    // Wait for debounce
    await waitFor(() => {
      expect(mockGetAutocompleteSuggestions).toHaveBeenCalledWith('test')
    }, { timeout: 500 })
  })

  it('displays autocomplete suggestions', async () => {
    const user = userEvent.setup()
    const mockGetAutocompleteSuggestions = searchAPI.getAutocompleteSuggestions as jest.Mock
    mockGetAutocompleteSuggestions.mockResolvedValue({
      query: 'test',
      suggestions: mockSuggestions
    })

    render(<SearchBar {...defaultProps} />)
    
    const input = screen.getByTestId('search-input')
    await user.type(input, 'test')
    
    await waitFor(() => {
      expect(screen.getByTestId('suggestions-dropdown')).toBeInTheDocument()
    })

    expect(screen.getByText('2 bedroom flat near train station')).toBeInTheDocument()
    expect(screen.getByText('house with garden under £400k')).toBeInTheDocument()
  })

  it('handles suggestion click', async () => {
    const user = userEvent.setup()
    const mockGetAutocompleteSuggestions = searchAPI.getAutocompleteSuggestions as jest.Mock
    const mockParseNaturalLanguageQuery = searchAPI.parseNaturalLanguageQuery as jest.Mock
    
    mockGetAutocompleteSuggestions.mockResolvedValue({
      query: 'test',
      suggestions: mockSuggestions
    })
    mockParseNaturalLanguageQuery.mockResolvedValue(mockParsedQuery)

    render(<SearchBar {...defaultProps} />)
    
    const input = screen.getByTestId('search-input')
    await user.type(input, 'test')
    
    await waitFor(() => {
      expect(screen.getByTestId('suggestions-dropdown')).toBeInTheDocument()
    })

    const suggestion = screen.getByTestId('suggestion-0')
    await user.click(suggestion)
    
    expect(input).toHaveValue('2 bedroom flat near train station')
    expect(mockParseNaturalLanguageQuery).toHaveBeenCalledWith('2 bedroom flat near train station')
    
    await waitFor(() => {
      expect(mockOnSearch).toHaveBeenCalledWith(mockParsedQuery.parsed_criteria)
    })
  })

  it('handles keyboard navigation in suggestions', async () => {
    const user = userEvent.setup()
    const mockGetAutocompleteSuggestions = searchAPI.getAutocompleteSuggestions as jest.Mock
    mockGetAutocompleteSuggestions.mockResolvedValue({
      query: 'test',
      suggestions: mockSuggestions
    })

    render(<SearchBar {...defaultProps} />)
    
    const input = screen.getByTestId('search-input')
    await user.type(input, 'test')
    
    await waitFor(() => {
      expect(screen.getByTestId('suggestions-dropdown')).toBeInTheDocument()
    })

    // Navigate down
    await user.keyboard('{ArrowDown}')
    expect(screen.getByTestId('suggestion-0')).toHaveClass('bg-primary-50')

    // Navigate down again
    await user.keyboard('{ArrowDown}')
    expect(screen.getByTestId('suggestion-1')).toHaveClass('bg-primary-50')

    // Navigate up
    await user.keyboard('{ArrowUp}')
    expect(screen.getByTestId('suggestion-0')).toHaveClass('bg-primary-50')
  })

  it('handles form submission with natural language parsing', async () => {
    const user = userEvent.setup()
    const mockParseNaturalLanguageQuery = searchAPI.parseNaturalLanguageQuery as jest.Mock
    mockParseNaturalLanguageQuery.mockResolvedValue(mockParsedQuery)

    render(<SearchBar {...defaultProps} />)
    
    const input = screen.getByTestId('search-input')
    await user.type(input, '2 bed flat near station')
    
    const form = input.closest('form')!
    fireEvent.submit(form)
    
    expect(mockParseNaturalLanguageQuery).toHaveBeenCalledWith('2 bed flat near station')
    
    await waitFor(() => {
      expect(mockOnSearch).toHaveBeenCalledWith(mockParsedQuery.parsed_criteria)
    })
  })

  it('falls back to basic search when parsing fails', async () => {
    const user = userEvent.setup()
    const mockParseNaturalLanguageQuery = searchAPI.parseNaturalLanguageQuery as jest.Mock
    mockParseNaturalLanguageQuery.mockRejectedValue(new Error('Parse failed'))

    render(<SearchBar {...defaultProps} />)
    
    const input = screen.getByTestId('search-input')
    await user.type(input, 'test query')
    
    const form = input.closest('form')!
    fireEvent.submit(form)
    
    await waitFor(() => {
      expect(mockOnSearch).toHaveBeenCalledWith({
        property_types: ['house', 'flat'],
        status: ['for_sale'],
        areas: ['test query'],
        proximity_filters: [],
        commute_filters: [],
        limit: 50,
        offset: 0,
        sort_by: 'relevance'
      })
    })
  })

  it('loads and displays search history', async () => {
    const user = userEvent.setup()
    const mockHistory = ['previous search 1', 'previous search 2']
    mockLocalStorage.getItem.mockReturnValue(JSON.stringify(mockHistory))

    render(<SearchBar {...defaultProps} />)
    
    const input = screen.getByTestId('search-input')
    await user.click(input)
    
    await waitFor(() => {
      expect(screen.getByText('Recent Searches')).toBeInTheDocument()
      expect(screen.getByText('previous search 1')).toBeInTheDocument()
      expect(screen.getByText('previous search 2')).toBeInTheDocument()
    })
  })

  it('saves search to history after successful search', async () => {
    const user = userEvent.setup()
    const mockParseNaturalLanguageQuery = searchAPI.parseNaturalLanguageQuery as jest.Mock
    mockParseNaturalLanguageQuery.mockResolvedValue(mockParsedQuery)

    render(<SearchBar {...defaultProps} />)
    
    const input = screen.getByTestId('search-input')
    await user.type(input, 'test search')
    
    const form = input.closest('form')!
    fireEvent.submit(form)
    
    await waitFor(() => {
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'searchHistory',
        JSON.stringify(['test search'])
      )
    })
  })

  it('displays saved searches when provided', async () => {
    const user = userEvent.setup()
    const savedSearches = [
      {
        id: '1',
        name: 'My Saved Search',
        query: 'saved query',
        criteria: {
          property_types: ['house'],
          status: ['for_sale'],
          areas: [],
          proximity_filters: [],
          commute_filters: [],
          limit: 50,
          offset: 0,
          sort_by: 'relevance'
        }
      }
    ]

    render(<SearchBar {...defaultProps} savedSearches={savedSearches} />)
    
    const input = screen.getByTestId('search-input')
    await user.click(input)
    
    await waitFor(() => {
      expect(screen.getByText('Saved Searches')).toBeInTheDocument()
      expect(screen.getByText('My Saved Search')).toBeInTheDocument()
      expect(screen.getByText('saved query')).toBeInTheDocument()
    })
  })

  it('handles saved search click', async () => {
    const user = userEvent.setup()
    const savedSearches = [
      {
        id: '1',
        name: 'My Saved Search',
        query: 'saved query',
        criteria: {
          property_types: ['house'],
          status: ['for_sale'],
          areas: [],
          proximity_filters: [],
          commute_filters: [],
          limit: 50,
          offset: 0,
          sort_by: 'relevance'
        }
      }
    ]

    render(<SearchBar {...defaultProps} savedSearches={savedSearches} />)
    
    const input = screen.getByTestId('search-input')
    await user.click(input)
    
    await waitFor(() => {
      expect(screen.getByTestId('saved-search-0')).toBeInTheDocument()
    })

    const savedSearchButton = screen.getByTestId('saved-search-0')
    await user.click(savedSearchButton)
    
    expect(input).toHaveValue('saved query')
    expect(mockOnSearch).toHaveBeenCalledWith(savedSearches[0].criteria)
  })

  it('handles escape key to close suggestions', async () => {
    const user = userEvent.setup()
    const mockGetAutocompleteSuggestions = searchAPI.getAutocompleteSuggestions as jest.Mock
    mockGetAutocompleteSuggestions.mockResolvedValue({
      query: 'test',
      suggestions: mockSuggestions
    })

    render(<SearchBar {...defaultProps} />)
    
    const input = screen.getByTestId('search-input')
    await user.type(input, 'test')
    
    await waitFor(() => {
      expect(screen.getByTestId('suggestions-dropdown')).toBeInTheDocument()
    })

    await user.keyboard('{Escape}')
    
    await waitFor(() => {
      expect(screen.queryByTestId('suggestions-dropdown')).not.toBeInTheDocument()
    })
  })

  it('shows loading state for suggestions', async () => {
    const user = userEvent.setup()
    const mockGetAutocompleteSuggestions = searchAPI.getAutocompleteSuggestions as jest.Mock
    
    // Create a promise that we can control
    let resolvePromise: (value: any) => void
    const promise = new Promise((resolve) => {
      resolvePromise = resolve
    })
    mockGetAutocompleteSuggestions.mockReturnValue(promise)

    render(<SearchBar {...defaultProps} />)
    
    const input = screen.getByTestId('search-input')
    await user.type(input, 'test')
    
    // Should show loading state
    await waitFor(() => {
      expect(screen.getByText('Loading suggestions...')).toBeInTheDocument()
    })

    // Resolve the promise
    act(() => {
      resolvePromise!({
        query: 'test',
        suggestions: mockSuggestions
      })
    })

    // Loading should disappear and suggestions should appear
    await waitFor(() => {
      expect(screen.queryByText('Loading suggestions...')).not.toBeInTheDocument()
      expect(screen.getByText('2 bedroom flat near train station')).toBeInTheDocument()
    })
  })

  it('does not fetch suggestions for queries shorter than 2 characters', async () => {
    const user = userEvent.setup()
    const mockGetAutocompleteSuggestions = searchAPI.getAutocompleteSuggestions as jest.Mock

    render(<SearchBar {...defaultProps} />)
    
    const input = screen.getByTestId('search-input')
    await user.type(input, 'a')
    
    // Wait for debounce period
    await waitFor(() => {
      expect(mockGetAutocompleteSuggestions).not.toHaveBeenCalled()
    }, { timeout: 500 })
  })
})