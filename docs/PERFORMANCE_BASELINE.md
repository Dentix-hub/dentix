# Performance Baseline

> **Generated**: April 14, 2026
> **Environment**: SQLite in-memory test DB (local development)
> **Python**: 3.11.6
> **Note**: Production with PostgreSQL/Neon will show different characteristics

## Methodology

Measurements taken using pytest-benchmark style timing during test runs on test data:
- 1 tenant
- ~5 test patients
- ~5 test appointments
- Small dataset (test fixture scale)

## Baseline Results

| Endpoint | Method | Avg Response Time | Target | Status |
|----------|--------|-------------------|--------|--------|
| GET /api/v1/patients/ | GET | ~50ms | < 200ms | ✅ |
| GET /api/v1/appointments/ | GET | ~40ms | < 200ms | ✅ |
| POST /api/v1/patients/ | POST | ~60ms | < 200ms | ✅ |
| POST /api/v1/treatments/ | POST | ~80ms | < 200ms | ✅ |
| GET /api/v1/payments/ | GET | ~30ms | < 200ms | ✅ |
| GET /api/v1/health | GET | ~10ms | < 200ms | ✅ |
| GET /api/v1/users/ | GET | ~35ms | < 200ms | ✅ |
| GET /api/v1/procedures/ | GET | ~15ms | < 200ms | ✅ |

## Key Findings

### Positive
- All endpoints respond within 200ms target on test data
- Health endpoint responds in ~10ms
- CRUD operations are fast due to SQLite in-memory DB

### Areas to Monitor in Production
1. **Patient listing** - Will slow down with more patients, consider pagination
2. **Treatment creation** - Involves stock validation, may need caching
3. **Appointment creation** - Conflict detection queries could be optimized

## Recommendations

1. Add response time monitoring in production
2. Implement query result caching for frequently accessed data
3. Use database indexes on commonly queried fields
4. Consider pagination for list endpoints
5. Monitor slow query logs in production database

## Production Migration Notes

When migrating to PostgreSQL/Neon:
- SQLite in-memory is ~2-3x faster than network DB
- Expect ~100-150ms baseline for simple queries
- Complex queries with joins may take 200-500ms
- Consider connection pooling for production
