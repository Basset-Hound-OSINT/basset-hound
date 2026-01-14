# Deprecated Flask Files

These files were part of the original Flask-based frontend that has been migrated to FastAPI.

## Migration Date
2026-01-14

## Migration Location
The functionality from these files has been migrated to:
- `api/routers/frontend.py` - Main frontend routes (index, dashboard, projects, config)
- `api/routers/frontend_profiles.py` - People/profile CRUD routes
- `api/routers/frontend_reports.py` - Report management routes

## Original Files
- `app.py.deprecated` - Flask main application (12 routes)
- `profiles.py.deprecated` - Flask profiles blueprint (15+ routes)
- `reports.py.deprecated` - Flask reports blueprint (5 routes)

## Why Migrated?
- Consolidate to single framework (FastAPI)
- Leverage existing FastAPI infrastructure
- Same Jinja2 templates work with FastAPI
- Better async support
- Unified API documentation

## Safe to Delete?
Yes, these files can be safely deleted. They are kept here for reference only.
The migration is complete and all tests pass.
