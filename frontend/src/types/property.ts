export interface Location {
  latitude: number
  longitude: number
  address: string
  postcode?: string
  area?: string
  city?: string
}

export interface PropertyLineage {
  source: string
  source_id: string
  last_updated: string
  reliability_score: number
}

export interface Property {
  id: string
  title: string
  description?: string
  price: number
  property_type: 'house' | 'flat' | 'bungalow' | 'maisonette' | 'land'
  status: 'for_sale' | 'for_rent' | 'sold' | 'let'
  bedrooms?: number
  bathrooms?: number
  location: Location
  images: string[]
  features: string[]
  energy_rating?: string
  council_tax_band?: string
  tenure?: string
  floor_area_sqft?: number
  garden?: boolean
  parking?: boolean
  lineage: PropertyLineage
  created_at: string
  updated_at: string
}

export interface ProximityFilter {
  amenity_type: 'park' | 'train_station' | 'gym' | 'school' | 'hospital' | 'shopping_center' | 'restaurant' | 'pharmacy'
  max_distance: number
  distance_unit: 'meters' | 'kilometers' | 'miles'
  walking_distance: boolean
}

export interface EnvironmentalFilter {
  max_air_pollution_level?: number
  max_noise_level?: number
  avoid_flood_risk: boolean
  min_green_space_proximity?: number
}

export interface CommuteFilter {
  destination_address: string
  max_commute_minutes: number
  transport_modes: string[]
}

export interface SearchCriteria {
  min_price?: number
  max_price?: number
  property_types: string[]
  status: string[]
  min_bedrooms?: number
  max_bedrooms?: number
  min_bathrooms?: number
  center_latitude?: number
  center_longitude?: number
  radius_km?: number
  areas: string[]
  proximity_filters: ProximityFilter[]
  environmental_filters?: EnvironmentalFilter
  commute_filters: CommuteFilter[]
  must_have_garden?: boolean
  must_have_parking?: boolean
  min_floor_area_sqft?: number
  limit: number
  offset: number
  sort_by: string
}

export interface SearchResultProperty extends Property {
  match_score: number
  distance_km?: number
  matched_filters: string[]
}

export interface SearchResult {
  properties: SearchResultProperty[]
  total_count: number
  search_time_ms: number
  filters_applied: Record<string, any>
}