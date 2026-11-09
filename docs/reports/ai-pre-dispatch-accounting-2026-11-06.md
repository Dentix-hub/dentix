# AI privacy denials and quota accounting — 2026-11-06

Code correction verified locally; hosted acceptance and commercial launch remain PARTIAL.

## Reproduced failure

PR #369 fixed isolated-session tenant binding and passed staging CD/smoke at `faa7ec6891c18e8da70ff147248f661964655820`. A subsequent synthetic-only live request reached the local privacy gate and returned `External AI processing is disabled by privacy policy`. It never reached the provider. Authenticated diagnostics and a read-only query restricted to that synthetic tenant showed a one-unit CONSUMED reservation and remaining quota falling from 10 to 9.

`AIAgent.process` converted the typed `AIEgressDenied` into a generic soft error without the existing `_provider_dispatched=False` marker. `AIService.process_query` conservatively consumed reservations when that marker was absent. Direct analysis instead classified the same known pre-dispatch rejection as UNCERTAIN. Both outcomes retained an admitted unit, contrary to the approved rule that upfront rejections are free.

Scribe already calls `prepare_ai_messages` before reserving quota. Its existing denial ordering is correct and requires no production-code change.

## Correction

- [Agent boundary](../../backend/ai/agent/core.py): catch `AIEgressDenied` before the generic provider-error handler, return the stable `ai_egress_denied` error code and explicitly mark no dispatch. The existing ledger finalization path then releases the reservation.
- [Direct-analysis boundary](../../backend/services/ai_service.py): release owned or server-preallocated analysis reservations for that same typed exception and return the same error code.
- The exception is raised only by the existing local privacy preparation code, before the SDK call. No string matching is used. An SDK exception with the identical text is still conservatively counted.
- Privacy policy, contractual approval and de-identification checks remain authoritative. API response schemas, authentication/RBAC, provider configuration, plan prices/caps, quota locks and state-transition rules are unchanged.
- Released idempotent requests do not re-dispatch or charge again. Successful requests still consume one unit; unknown provider failures remain admitted. Direct analysis retains UNCERTAIN for unknown dispatch outcomes; this patch does not redesign generic chat-error reconciliation.
- The canonical chat error code also fits `AILog.error_type` (VARCHAR(50)); the former privacy text had 52 characters. The regression verifies a persisted FAILURE log with the stable code on actual PostgreSQL.

## Verification

Before the fix, the initial PostgreSQL regression file produced **6 failed / 8 passed**: chat consumed a unit and direct/preallocated analysis retained an uncertain unit despite no provider call.

After correction: **74 passed / 0 failed / 0 skipped** across the new acceptance tests, existing privacy-policy tests, quota accounting, provider integration, restricted-role RLS/promotion regressions, release hardening, financial AI permissions and connection-pool tests. The new file contains **18 tests**, including deny mode, unapproved contracted mode, real de-identification confidence rejection, free replay, Scribe no-reservation behavior, successful accounting and post-dispatch timeout/same-text-error controls. An overlapping final run additionally verifies persisted chat denial logs; results are not added as unique tests.

Changed backend Ruff and `git diff --check` pass. No frontend changes require a UI build for this diff. The full unchanged application suite was not repeated; authoritative HIGH_RISK PR CI is still required.

Evidence: `/home/ubuntu/dentix-task-artifacts/ai-egress-accounting-20261106/` (`red.log`, `final.xml/.log/.exit`, `acceptance.xml/.log/.exit`). Fixtures create/remove disposable schemas in an explicitly named local PostgreSQL test database. SDK transports are mocked at their network boundary; the real privacy gate, agent/service flow and PostgreSQL ledger execute. No hosted request or data mutation was performed during this correction, and no real patient content was accessed.

## Staging acceptance (under 15 minutes)

1. Merge/deploy only through the authorized staging path and require successful exact-revision CI/CD/smoke.
2. Log into the existing synthetic release-probe clinic. Record current quota diagnostics. Use a **fresh logical request/idempotency key**: the earlier falsely-consumed operation is preserved historical data and would replay without executing the corrected path.
3. With the current privacy-deny configuration, send a nonclinical probe. Expect `success=false`, `error=ai_egress_denied`, a RELEASED reservation and unchanged consumed/reserved/uncertain/remaining totals.
4. Repeat the same new key/payload. It must remain unsuccessful and free, with no provider dispatch. Check the chat denial's FAILURE audit record and stable code.
5. Scribe under the same privacy denial must create no reservation. Direct clinic-wide analysis remains subject to AI_CHAT AND REPORT_READ and must release its preallocated reservation if privacy rejects it.

Do not change privacy approval or enforcement configuration to make this test pass. A genuine provider test remains a separate approved configuration/acceptance step. The observed staging commercial mode remains OFF; this correction does not enable paid-plan enforcement.

## Preservation and limits

No migrations, schema, CI/governance files, hosted policy, production data or historical reservations were changed. Previously recorded consumed/uncertain operations are not automatically refunded or reclassified; arbitrary historical failures may have reached a provider. This patch corrects future known pre-dispatch denials and does not authorize main promotion, live-provider claims or general ledger repair.
