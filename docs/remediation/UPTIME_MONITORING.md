# DENTIX External Uptime Monitoring Specification

## 1. Scope
External synthetic uptime probes verify availability of core public health check surfaces without accessing patient data.

## 2. Health Endpoints

| Endpoint | Method | Expected Status | Check Cadence |
|---|---|---|---|
| `/health` | `GET` | `200 OK` | Every 60s |
| `/api/v1/ping` | `GET` | `200 OK` | Every 60s |
| `/` (Frontend Root) | `GET` | `200 OK` | Every 120s |

## 3. SLA & Degradation Criteria
- **Healthy**: Response time < 500ms, HTTP 200.
- **Degraded**: Response time 500ms - 2000ms.
- **Outage**: 3 consecutive failed probes across >= 2 geographic regions.
