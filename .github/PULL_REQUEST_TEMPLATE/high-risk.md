## Source & Risk Classification

- **Source Issue**: Closes #
- **Source Plan / Requirement IDs**:
- **Execution Mode**: `HIGH_RISK`
- **Risk Category**: `AUTH_RBAC` | `TENANCY_RLS` | `FINANCE` | `DATABASE_MIGRATION` | `CLINICAL_SEMANTICS` | `DEPLOYMENT` | `SECURITY`
- **Parallel Classification**: `SERIAL_ONLY`

## Scope & Non-Goals

- **Included Scope**:
- [ ] No declared non-goals were implemented.
- [ ] Expected touch surface respected: no unlisted production files touched.

## Detailed Verification Evidence (T1 / T2 / T3)

### T1 Targeted Verification
| Exact Command | Exit Code | Result Summary | New or Baseline Failure |
| --- | ---: | --- | --- |
|  | 0 |  | None |

### T2 Subsystem & Integration Gate
| Gate Type | Exact Command | Exit Code | Evidence Summary |
| --- | --- | ---: | --- |
| Lint / Static Analysis |  | 0 | Clean |
| Subsystem Tests |  | 0 | Passed |
| Integration Tests |  | 0 | Passed |

### T3 Full CI Gate
- [ ] Full CI suite passed (`agent:ci-green`).
- [ ] Model-driven CI polling: 0 calls (stopped at `AWAITING_CI`).

## Security, Tenancy & RBAC Analysis

- **Tenant Isolation**: Does every query and operation enforce tenant boundaries?
- **RBAC Checks**: Are endpoint and role permissions verified?
- **Data Protection**: Is PII, clinical, or financial data protected?
- **Analysis Details**:

## Database & Migration Analysis (when applicable)

- **Migration Safety**: Backward compatible? No destructive schema alterations without approval.
- **Alembic Lineage**: Correct down-revision and clean upgrade/downgrade.
- **Analysis Details**:

## Clinical Semantics Analysis (when applicable)

- **Tooth Identity & Notation**: Exact mapping preserved across systems (FDI/Universal/Palmer).
- **Condition / Treatment Meaning**: Preserved clinical domain truth.
- **Analysis Details**:

## Independent Review Sign-Off

- [ ] Independent reviewer session performed by distinct reviewer.
- [ ] Findings and resolutions documented and addressed.
- [ ] No automatic merge authorized.
