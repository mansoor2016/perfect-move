'use client'

import { useEffect, useRef } from 'react'
import mapboxgl from 'mapbox-gl'
import { Property, SearchCriteria } from '@/types/property'

interface PropertyMapProps {
  properties: Property[]
  searchCriteria: SearchCriteria | null
}

export default function PropertyMap({ properties, searchCriteria }: PropertyMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<mapboxgl.Map | null>(null)

  useEffect(() => {
    if (!mapContainer.current) return

    // Initialize map
    if (!map.current) {
      // Set a default token for now - will be configured properly in later tasks
      mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || 'pk.placeholder'
      
      map.current = new mapboxgl.Map({
        container: mapContainer.current,
        style: 'mapbox://styles/mapbox/streets-v12',
        center: [-0.1276, 51.5074], // London center
        zoom: 10
      })

      map.current.addControl(new mapboxgl.NavigationControl(), 'top-right')
    }

    return () => {
      if (map.current) {
        map.current.remove()
        map.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (!map.current || !properties.length) return

    // Clear existing markers
    const existingMarkers = document.querySelectorAll('.mapboxgl-marker')
    existingMarkers.forEach(marker => marker.remove())

    // Add property markers
    properties.forEach(property => {
      const marker = new mapboxgl.Marker()
        .setLngLat([property.location.longitude, property.location.latitude])
        .setPopup(
          new mapboxgl.Popup({ offset: 25 }).setHTML(`
            <div class="p-2">
              <h3 class="font-semibold">${property.title}</h3>
              <p class="text-sm text-gray-600">£${property.price.toLocaleString()}</p>
              <p class="text-xs text-gray-500">${property.location.address}</p>
            </div>
          `)
        )
        .addTo(map.current!)
    })

    // Fit map to show all properties
    if (properties.length > 0) {
      const bounds = new mapboxgl.LngLatBounds()
      properties.forEach(property => {
        bounds.extend([property.location.longitude, property.location.latitude])
      })
      map.current.fitBounds(bounds, { padding: 50 })
    }
  }, [properties])

  return (
    <div className="h-96 lg:h-[600px] rounded-lg overflow-hidden border border-gray-200">
      <div ref={mapContainer} className="w-full h-full" />
      {!process.env.NEXT_PUBLIC_MAPBOX_TOKEN && (
        <div className="absolute inset-0 bg-gray-100 flex items-center justify-center">
          <p className="text-gray-600 text-center">
            Map will be available when Mapbox token is configured
          </p>
        </div>
      )}
    </div>
  )
}