# DENTIX Performance Budgets and Verification Status

## Proposed p95 budgets

| Endpoint class | p95 budget | Evidence status |
|---|---:|---|
| health probes | 50 ms | not load-tested in this local run |
| authentication | 250 ms | not load-tested in this local run |
| patient list/search | 200 ms | query-count regression tests only |
| clinical history | 200 ms | query-count regression tests only |
| financial summary | 300 ms | correctness tests only |
| protected metrics | 100 ms | functional access tests only |

The earlier document listed measured latency values without a retained benchmark artifact; those values are withdrawn. Local N+1/query-count tests pass, but they do not establish production latency or throughput.

Before release, run a guarded load test against an explicitly approved non-production target with production-like PostgreSQL data. Record workload, concurrency, dataset size, p50/p95/p99, error rate, database saturation, and `EXPLAIN (ANALYZE, BUFFERS)` for slow queries. Do not claim these budgets as met until that artifact exists.
