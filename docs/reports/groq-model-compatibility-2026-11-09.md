# Groq model compatibility preparation — 2026-11-09

**Status: local implementation DONE; real-provider and hosted delivery PARTIAL.** Base: protected Staging `86f80c1481c977d2c3e318034a914568f7657812`. No push, PR, deployment, hosted policy change or live provider request was performed. Legacy offers remain in their current state as explicitly requested by the owner.

## Confirmed compatibility gap

The existing router/direct-analysis defaults select `llama-3.1-8b-instant` / `llama-3.3-70b-versatile`; Scribe hardcodes `llama3-70b-8192`. Groq's [deprecation history](https://console.groq.com/docs/deprecations) says the former two ceased free/developer-tier availability on August 16, 2026, with an enterprise committed-spend exception; the latter retired August 30, 2025. Account-specific availability has not been inferred from the existence of a hidden API-key secret. The hosted request observed earlier still stops at `ai_egress_denied`, before model transport.

A new router regression failed before the fix (exit 1): it selected the legacy fast ID instead of the supported developer-tier default. Provider-boundary tests now cover all three entry paths, configuration overrides and unchanged analytics behavior. No existing assertions were removed or weakened.

## Implementation

- Shared selection defaults: `openai/gpt-oss-20b` for normal chat/direct analysis; `openai/gpt-oss-120b` for complex chat/Scribe. Both are listed as production models by [Groq](https://console.groq.com/docs/models), and support the existing [JSON response format](https://console.groq.com/docs/structured-outputs).
- Optional non-secret `GROQ_FAST_MODEL` / `GROQ_COMPLEX_MODEL` overrides are stripped and resolved per request. Explicit enterprise IDs remain possible; a blank override uses the default. Actual account availability still needs a credentialed check.
- Core agent, router, direct analysis and Scribe share the selectors, eliminating the retired Scribe literal.
- New model cards use the provider's published context/cost metadata as of the report date. Existing legacy cards remain. The analytics fallback is explicitly pinned to its previous legacy blended estimate so model selection cannot silently reprice historical/missing-cost statistics. Recorded costs retain precedence. Commercial quota units, ledger logic and receipts are unchanged.
- Default-deny egress policy, contractual approval marker, tenant/RBAC checks, clinical extraction prompt/semantics, tool permissions and the existing JSON API contract were not changed.

## Executed verification

**PASS — 37 targeted tests, 0 failed / 0 skipped, exit 0**, including 11 new compatibility cases and existing egress-policy, de-identification, PostgreSQL privacy/accounting/replay and analytics tests. The PostgreSQL cases ran against a fresh isolated PostgreSQL 17 database; the synthetic cluster was stopped and removed. This is targeted verification, not a new full-suite or production-provider claim.

```text
python -m pytest backend/tests/test_groq_model_compatibility.py backend/tests/test_ai_egress_policy.py backend/tests/test_ai_deidentification.py backend/tests/test_ai_egress_accounting.py backend/tests/ai/test_analytics.py -q --maxfail=0 --tb=short
```

`TEST_DATABASE_URL` pointed only to the isolated local test database. Ruff on all changed Python files and whitespace validation passed, exit 0. New financial-preservation cases independently check four estimated 500-input/500-output-token requests at the unchanged legacy $0.05/$0.10 per million: $0.0003 total; a recorded $2.50 sum remains $2.50. Private red/green/final logs and real exit records are under `/home/ubuntu/dentix-task-artifacts/release-readiness-20261109/`.

## Remaining provider/clinical acceptance

1. Supply a Groq test credential through a restricted file/secret injection, without changing the existing hosted key. The connector cannot reveal Hugging Face secret values. A blank private template exists at `/home/ubuntu/dentix-task-artifacts/groq-test.env`; it is outside Git and must stay outside Git.
2. Run an isolated fixed nonclinical request against the account's supported model IDs, with bounded output and no database/clinical context. Verify key/model access, genuine JSON output and no demo result. This requires no Space-wide privacy change.
3. Hosted end-to-end success, exactly one quota consumption and free same-key replay remain separate acceptance checks after authorized delivery and approved runtime egress configuration. Local mocked provider tests are not that evidence.
4. Before clinical activation, establish the appropriate approved privacy arrangement. Current de-identification is regex-based and has no recorded comprehensive Arabic/English clinical anonymity benchmark here. Do not infer that switching `EXTERNAL_AI_PHI_MODE=deidentified` guarantees anonymity, or set `EXTERNAL_AI_CONTRACT_APPROVED=true` without actual approval. Groq's [data-control documentation](https://console.groq.com/docs/your-data) describes ZDR availability; enabling a provider setting alone does not certify the application's entire clinical data flow.

## Review

Spec: fixes provider model selection compatibility; actual credential/model quality/hosted acceptance remain open. Standards: no new schema/migration, clinic reassignment, plan retirement, tenant/RBAC bypass, privacy weakening or quota/ledger change. Recorded costs and the legacy fallback estimate remain unchanged. No new actionable issue identified in this focused diff; this is not the stronger-model cumulative release review.
