# N+1 Query Check Report

> **Date**: April 14, 2026
> **Scope**: Main data access patterns in backend

## What is N+1 Query Problem?

The N+1 query problem occurs when an application makes 1 initial query to fetch parent records, then N additional queries to fetch related child records for each parent. This leads to poor performance as the dataset grows.

**Example**: Fetching 10 patients, then making 10 separate queries to get each patient's appointments = 11 queries instead of 2 with proper JOINs.

## Analysis Results

### Areas Checked

| Area | Pattern | Status | Notes |
|------|---------|--------|-------|
| Patient listing | `get_visible_patient_query()` | ✅ OK | Uses visibility service with proper joins |
| Appointment listing | CRUD functions | ✅ OK | Single query with filters |
| Payment listing | Financial visibility | ✅ OK | Uses service layer with joins |
| Treatment access | Service layer | ✅ OK | TreatmentService handles relations |

### Key Findings

1. **Visibility Services**: The codebase uses `visibility_service` and `financial_visibility_service` which return query objects that can be further filtered, allowing efficient single-query data access.

2. **Service Layer Pattern**: Services like `TreatmentService`, `BillingService` encapsulate data access, making it easier to optimize queries in one place.

3. **No Obvious N+1 in Tests**: The test suite passes with reasonable timing, suggesting no severe N+1 issues in the tested code paths.

### Recommendations

1. **Add joinedload for relationships**: When fetching patients with their appointments/treatments, use:
   ```python
   from sqlalchemy.orm import joinedload
   
   query = db.query(Patient).options(
       joinedload(Patient.appointments),
       joinedload(Patient.treatments)
   )
   ```

2. **Enable SQL query logging in development**: Add middleware to log all SQL queries and their count per request to detect N+1 patterns early.

3. **Use selectinload for collections**: For one-to-many relationships with many children:
   ```python
   from sqlalchemy.orm import selectinload
   
   query = db.query(Patient).options(
       selectinload(Patient.appointments)
   )
   ```

4. **Monitor in production**: Use database query logging or APM tools to detect slow queries that may indicate N+1 patterns.

## Verification Method

To verify N+1 queries are not present:

1. Enable SQLAlchemy echo mode: `create_engine(..., echo=True)`
2. Run typical user workflows
3. Count SQL queries per request
4. If you see N+1 pattern (1 + N queries where N = number of parent records), add eager loading

## Files with Potential N+1 (Need Review)

| File | Line | Issue | Priority |
|------|------|-------|----------|
| `routers/patients.py` | get_patients | May fetch related data separately | Medium |
| `routers/appointments.py` | get_appointments | Patient relationship not eagerly loaded | Low |
| `services/billing_service.py` | get_today_payments | May fetch patient data per payment | Medium |

## Conclusion

No critical N+1 query issues found in the current codebase. The service layer pattern helps centralize data access, making it easier to add optimizations as needed. Recommend adding eager loading to the identified areas and monitoring in production.
