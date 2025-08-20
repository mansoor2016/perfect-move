-- Initialize PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create initial tables (will be managed by Alembic migrations later)
-- This is just to ensure PostGIS is properly set up

-- Test PostGIS installation
SELECT PostGIS_Version();