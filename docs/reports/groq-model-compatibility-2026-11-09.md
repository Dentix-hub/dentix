# Groq model compatibility preparation — 2026-11-09

**Status: local implementation, genuine provider compatibility and local accounting/replay DONE; remote delivery authorized; hosted delivery and clinical activation PARTIAL.** Base: protected Staging `86f80c1481c977d2c3e318034a914568f7657812`. Three fixed nonclinical Groq completions were executed with the owner-supplied test credential. The owner authorized pushing this branch and opening its Staging PR. No deployment, hosted Dentix request or hosted policy change was performed. Legacy offers remain in their current state as explicitly requested by the owner.

## Confirmed compatibility gap

The existing router/direct-analysis defaults select `llama-3.1-8b-instant` / `llama-3.3-70b-versatile`; Scribe hardcodes `llama3-70b-8192`. Groq's [deprecation history](https://console.groq.com/docs/deprecations) says the former two ceased free/developer-tier availability on August 16, 2026, with an enterprise committed-spend exception; the latter retired August 30, 2025. Account-specific availability has not been inferred from the existence of a hidden API-key secret. The hosted request observed earlier still stops at `ai_egress_denied`, before model transport.

A new router regression failed before the fix (exit 1): it selected the legacy fast ID instead of the supported developer-tier default. Provider-boundary tests now cover all three entry paths, configuration overrides and unchanged analytics behavior. No existing assertions were removed or weakened.

The real service/accounting probe exposed a second pre-provider failure: even an empty synthetic clinic's generated system instructions were rejected by the de-identification confidence gate. A reduced `prepare_ai_messages(build_system_prompt(...))` reproduction and a new regression both failed before its fix. Built-in parameter descriptions contained the bare identity label `اسم المريض`, and two static English instructions contained `patient name`; the guard treats residual unredacted labels as risky. Built-in descriptions now say `الاسم` and static schema instructions use the existing `patient_name` key. Dynamic user/history/RAG/last-entity content and the egress guard itself were not rewritten or exempted. No permissions, parameter keys, required/optional meanings or clinical extraction rules changed.

## Implementation

- Shared selection defaults: `openai/gpt-oss-20b` for normal chat/direct analysis; `openai/gpt-oss-120b` for complex chat/Scribe. Both are listed as production models by [Groq](https://console.groq.com/docs/models), and support the existing [JSON response format](https://console.groq.com/docs/structured-outputs).
- Optional non-secret `GROQ_FAST_MODEL` / `GROQ_COMPLEX_MODEL` overrides are stripped and resolved per request. Explicit enterprise IDs remain possible; a blank override uses the default. The defaults were verified with the supplied credential below; other overrides still require their own account-availability check.
- Core agent, router, direct analysis and Scribe share the selectors, eliminating the retired Scribe literal.
- Static prompt/parameter wording no longer trips the confidence gate in an otherwise nonclinical request. New regressions prove normal/Scribe instruction compatibility, continued dynamic RAG/last-entity/user rejection, identity redaction and default denial. The guard and its patterns are unchanged.
- New model cards use the provider's published context/cost metadata as of the report date. Existing legacy cards remain. The analytics fallback is explicitly pinned to its previous legacy blended estimate so model selection cannot silently reprice historical/missing-cost statistics. Recorded costs retain precedence. Commercial quota units, ledger logic and receipts are unchanged.
- Default-deny egress policy, contractual approval marker, tenant/RBAC checks, clinical extraction prompt/semantics, tool permissions and the existing JSON API contract were not changed.

## Executed verification

**PASS — 44 targeted tests, 0 failed / 0 skipped, exit 0**, including 18 new model/prompt compatibility cases and existing egress-policy, de-identification, PostgreSQL privacy/accounting/replay and analytics tests. The PostgreSQL cases ran against a fresh isolated PostgreSQL 17 database; the synthetic cluster was stopped and removed. This is targeted verification, not a new full-suite or hosted-provider claim.

```text
python -m pytest backend/tests/test_groq_model_compatibility.py backend/tests/test_ai_prompt_egress_compatibility.py backend/tests/test_ai_egress_policy.py backend/tests/test_ai_deidentification.py backend/tests/test_ai_egress_accounting.py backend/tests/ai/test_analytics.py -q --maxfail=0 --tb=short
```

`TEST_DATABASE_URL` pointed only to the isolated local test database. Ruff on all changed Python files and whitespace validation passed, exit 0. New financial-preservation cases independently check four estimated 500-input/500-output-token requests at the unchanged legacy $0.05/$0.10 per million: $0.0003 total; a recorded $2.50 sum remains $2.50. Private red/green/final logs and real exit records are under `/home/ubuntu/dentix-task-artifacts/release-readiness-20261109/`.

## Real nonclinical provider and accounting evidence

The owner supplied the separate test-key file, installed outside Git with mode 0600. The existing hosted key was not read or replaced. Authenticated model discovery succeeded and advertised both selected model IDs. Two real calls through the candidate's actual `_call_llm_safe` returned the required technical JSON object on 20B and 120B, both with finish reason `stop`. The probe only added a 1,024-completion-token bound and disabled SDK retries; responses were not mocked. Fixed synthetic prompts contained no database or patient context.

One further real call ran through actual `AIService.process_query` with a synthetic PostgreSQL 17 clinic and Professional quota ten. It returned the requested marker and consumed exactly one reservation. Same-key replay succeeded without a second provider invocation: consumed=1, reserved=uncertain=0, remaining=9 after both calls. One CONSUMED reservation existed. No patient rows were seeded; all context and identities were synthetic. This verifies service/ledger/provider integration locally, not hosted HTTP/RBAC or clinical data approval.

The accounting fixture initially failed to connect because the application's production-safe DB SSL default was inherited by an SSL-less localhost server; only the fixture's local DB setting was corrected. The next attempt reached the static-prompt rejection above, with zero provider calls and zero quota charge; that failed certificate was retained. After the source wording fix, all original success/accounting/replay assertions passed. Local servers/clusters were stopped and removed. De-identification mode was enabled only in disposable probe processes; no Space variable was changed.

Executed commands, exit 0:

```text
PYTHONPATH=/home/ubuntu/dentix-ai-model-compatibility /home/ubuntu/dentix/.venv/bin/python /home/ubuntu/dentix-task-artifacts/release-readiness-20261109/groq_nonclinical_provider_smoke.py
/home/ubuntu/dentix/.venv/bin/python /home/ubuntu/dentix-task-artifacts/release-readiness-20261109/groq_live_accounting_smoke.py
```

Private result certificates are `groq-nonclinical-provider-result.json` and `groq-live-accounting-result.json` in that artifact directory. They contain model/response hashes and accounting counters, no credential values. There were three nonclinical completion requests in total, plus model discovery; same-key replay added no provider call.

## Remaining hosted/clinical acceptance

1. Deliver the reviewed source fix through its owner-authorized PR to Staging. Local bundles are verified. CI, merge and deployed-Staging acceptance follow the repository workflow; production promotion is not included in this authorization.
2. Hosted end-to-end success, exactly one quota consumption and free replay remain separate acceptance checks after authorized delivery and approved runtime egress configuration. Neither local mocks nor the real local service probe are relabelled as hosted acceptance.
3. Before clinical activation, establish the appropriate approved privacy arrangement. Current de-identification is regex-based and has no recorded comprehensive Arabic/English clinical anonymity benchmark here. Fixing a static-label false positive does not establish anonymity of arbitrary clinical text. Do not set `EXTERNAL_AI_CONTRACT_APPROVED=true` without actual approval. Groq's [data-control documentation](https://console.groq.com/docs/your-data) describes ZDR availability; a provider setting alone does not certify the application's entire clinical data flow.

## Review

Spec: model/key/JSON transport and one real service/quota/replay flow now pass locally; hosted acceptance and clinical output quality remain open. Standards: no new schema/migration, clinic reassignment, plan retirement, tenant/RBAC bypass, privacy weakening or quota/ledger change. Recorded costs and the legacy fallback estimate remain unchanged. No new actionable issue identified in this focused diff; this is not the stronger-model cumulative release review.
