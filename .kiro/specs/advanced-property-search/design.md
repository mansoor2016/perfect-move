# Advanced Property Search Platform - Design Document (Speed-to-Market Focus)

## Overview

The Advanced Property Search platform provides lifestyle-based property search with a single intelligent interface, map visualisation, and integration of property listings with geospatial, environmental, and transport data. To deliver quickly, the system will launch as a **modular monolith** in Python, with clear module boundaries for potential future extraction into services.

## Architecture

### High-Level Architecture (Monolith First)

```
┌─────────────────┐
│   Frontend      │   (React/Next.js)
└─────────────────┘
          │
          ▼
┌──────────────────────────┐
│    Backend (FastAPI)     │
│ ┌──────────────────────┐ │
│ │  API Routers         │ │
│ │  (search, users,     │ │
│ │   properties)        │ │
│ └──────────────────────┘ │
│ ┌──────────────────────┐ │
│ │  Domain Modules      │ │
│ │  (search, ingestion, │ │
│ │   geospatial, users) │ │
│ └──────────────────────┘ │
│ ┌──────────────────────┐ │
│ │  Infrastructure      │ │
│ │  (DB, ES, Redis,     │ │
│ │   API clients)       │ │
│ └──────────────────────┘ │
└──────────────────────────┘
          │
          ▼
┌─────────────────┐
│ Data Layer      │ (Postgres + PostGIS, Elasticsearch, Redis)
└─────────────────┘
          │
          ▼
┌─────────────────┐
│ External APIs   │ (Rightmove, Zoopla, Mapbox, TfL, etc.)
└─────────────────┘
```

**Design Rationale:** The monolith allows a single deployment, faster iteration, and less operational overhead. Domain modules enforce separation in code so we can split them later if scaling requires.

### Technology Stack

* **Frontend:** React + Next.js (SEO, SSR)
* **Backend:** Python with FastAPI (async APIs, modular monolith)
* **Database:** PostgreSQL + PostGIS (geospatial)
* **Search:** Elasticsearch (fast filtering, free-text)
* **Cache:** Redis (search caching, sessions, background job queue)
* **Maps:** Mapbox GL JS (interactive mapping)
* **Workers:** Celery/RQ for ingestion, deduplication, background sync

## Components and Interfaces

### Frontend

* **Single search bar** with autocomplete and natural language parsing.
* **Interactive map** with markers, amenity layers, and commute overlays.
* **Results view** with property cards, favourites, and saved searches.

### Backend Modules (in one codebase)

#### Search Module

* Executes search queries via Elasticsearch + PostGIS.
* Supports lifestyle filters (amenities, commute time, environment).
* Ranking engine combines price, match score, proximity, and freshness.

#### Ingestion Module

* Adapters for Rightmove, Zoopla, etc.
* Deduplication (fuzzy address + geocode matching).
* Normalisation pipeline (consistent schema).
* Lineage stamping (source, sync time, reliability score).

#### Geospatial Module

* Distance and proximity queries (straight, walking).
* Commute isochrones (Mapbox/TfL APIs).
* Environmental layers (air quality, flood risk, crime stats).

#### User Module

* Manage saved searches and favourites.
* Store user weights/preferences for personalised ranking.
* Notifications (new matches, updates).

## Data Models

Keep lightweight, Pydantic models for API contracts. Store search criteria as JSON in Postgres for flexibility. Key indices:

* PostGIS spatial index on properties.
* Full-text + structured indexes for search.
* Amenity categories indexed for proximity queries.

## Error Handling

* **Graceful degradation:** Return partial data when APIs fail.
* **Retries with backoff** for transient API errors.
* **Lineage tracking:** Show users when some data is missing or stale.
* **Fallback UX states:** UI indicates limited data (e.g. “commute info unavailable”).

## Performance Optimisation

* **Search:** Elasticsearch + Redis cache for repeated queries.
* **Maps:** Marker clustering, viewport-based loading.
* **Ingestion:** Incremental sync with background jobs.
* **Batch vs realtime:** Realtime updates via outbox table; nightly reconciliation jobs.

## Testing Strategy

* **Unit tests:** Data models, deduplication logic, distance functions.
* **Integration tests:** API endpoints, DB queries, external API mocks.
* **E2E tests:** Search flows, map interactions, property discovery.
* **Load testing:** Ensure 95% searches return <2s.

## Security & Compliance

* **Input sanitisation** and query parameter validation.
* **Rate limiting** on public APIs.
* **Secure secret management** for API keys.
* **GDPR compliance:** anonymise search logs.

## Scalability & Migration Path

* Initially scale via multiple app replicas + worker pool.
* Add Postgres read replicas + ES cluster as traffic grows.
* If needed, peel off ingestion or search into separate services later (module boundaries already defined).

## Speed-to-Market Priorities

1. **Phase 1 (MVP):** Core ingestion (Rightmove, Zoopla), search API, map visualisation, filters.
2. **Phase 2:** Deduplication, commute isochrones, environmental overlays.
3. **Phase 3:** Personalised ranking, notifications, advanced analytics.

**Guiding Principle:** Ship fast with a monolith, keeping clean module boundaries to avoid a rewrite when scaling requires service extraction.
