# Web Push Rollout Notes (PR-PWA-05/06)

**Status:** Code complete + tested; production delivery gated on key provisioning.

## Required environment (backend)

| Variable | Purpose |
|---|---|
| `VAPID_PRIVATE_KEY` | Server-side only. Generate once: `npx web-push generate-vapid-keys` |
| `VAPID_SUBJECT` | `mailto:support@dentixs.app` |

Without `VAPID_PRIVATE_KEY` the `WebPushProvider` reports `NOT_CONFIGURED`
and delivery is skipped safely — subscriptions still register.

## Required environment (frontend build)

| Variable | Purpose |
|---|---|
| `VITE_VAPID_PUBLIC_KEY` | The matching public key, embedded in the frontend bundle |

## Rollout order (plan §12.9)

1. Developer/test accounts.
2. Staging clinic fixtures.
3. Controlled real-clinic accounts.
4. General availability.

## Session semantics

- Subscriptions bind to the device-scoped JWT `sid` stored as `session_sid`.
- That sid maps to `UserSession.device_info` and remains stable across refresh-token rotation for the same device.
- Multiple active device sessions can receive push notifications concurrently.
- Delivery eligibility is re-checked at send time against the corresponding active, unexpired `UserSession`; stale subscriptions are revoked and never delivered to.
- Logging out one device revokes only that device session. Other device sessions remain valid.
- Permanent endpoint invalidation (HTTP 404/410 from the push service) revokes the subscription automatically.

## Legacy Firebase

`backend/utils/firebase_manager.py` is now a facade over the single bootstrap
in `backend/core/firebase_client.py` — only one `firebase_admin` default app
initialization path remains. The scalar `User.fcm_token` path is untouched but
no new PWA traffic uses it.
