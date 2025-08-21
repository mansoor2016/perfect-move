# Advanced Property Search Platform

A web application that enables home buyers and renters to search for properties using sophisticated lifestyle-based filters, integrating multiple data sources including property listings, geographic data, environmental data, and transportation information.

## Project Structure

```
├── backend/                 # FastAPI backend (Python)
│   ├── app/
│   │   ├── api/            # API routers and endpoints
│   │   ├── core/           # Configuration and utilities
│   │   ├── models/         # Pydantic models for API contracts
│   │   └── modules/        # Domain modules (modular monolith)
│   │       ├── search/     # Property search functionality
│   │       ├── ingestion/  # External data ingestion
│   │       ├── geospatial/ # Location-based services
│   │       └── users/      # User management
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # Next.js frontend (TypeScript/React)
│   ├── src/
│   │   ├── app/           # Next.js app directory
│   │   ├── components/    # React components
│   │   └── types/         # TypeScript type definitions
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml     # Docker services configuration
└── init-db.sql          # PostgreSQL initialization
```

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL + PostGIS** - Database with geospatial extensions
- **Elasticsearch** - Search engine for complex queries
- **Redis** - Caching and background job queue
- **Celery/RQ** - Background task processing

### Frontend
- **Next.js 14** - React framework with SSR
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **Mapbox GL JS** - Interactive maps

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Quick Start with Docker

1. Clone the repository
2. Copy environment files:
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```
3. Start all services:
   ```bash
   docker-compose up -d
   ```
4. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Local Development

#### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Documentation

The FastAPI backend provides automatic API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Architecture

The system follows a modular monolith architecture with clear domain boundaries:

- **Search Module**: Handles property search with complex lifestyle filters
- **Ingestion Module**: Manages data from external property listing APIs
- **Geospatial Module**: Provides location-based services and calculations
- **User Module**: Manages user accounts, saved searches, and favorites

## Key Features

- Single intelligent search bar with natural language processing
- Interactive map visualization with property markers
- Advanced lifestyle-based filtering (proximity to amenities, commute times, environmental factors)
- Integration with property listing platforms (Rightmove, Zoopla)
- Real-time search suggestions and autocomplete
- User accounts with saved searches and favorites

## Development Status

This is the initial project structure setup. The following tasks are planned:
1. ✅ Project structure and Docker configuration
2. ✅ Database schema and data models
3. ✅ External API integration for property data
4. 🔄 Geospatial services and calculations
5. 🔄 Search functionality with Elasticsearch
6. 🔄 Frontend components and user interface
7. 🔄 User management and authentication

## Contributing

This project follows the spec-driven development methodology. See the requirements and design documents in `.kiro/specs/advanced-property-search/` for detailed specifications.