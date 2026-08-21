# Dentix Production Surface Verification — 2026-08-21

## Result

**Phase 1 verdict: PASS — Case A.**

The live custom-domain binding was verified from the connected Vercel account rather than inferred from repository configuration.

## Evidence

Production frontend project:

- project: `smartclinic-v2plus`
- project id: `prj_irSjmNJ9lRwpFrplNoy0DDzAWlYC`
- assigned domains include `dentixs.app` and `www.dentixs.app`

Staging frontend project:

- project: `dentix-staging`
- project id: `prj_r1YSA1KijlImxYXudAp6pRx7Ei30`
- the production custom domain is not assigned to this staging project

Repository routing evidence:

- `frontend/vercel.json` rewrites `/api/:path*` to `https://dentix-dentix.hf.space/api/:path*`
- SPA/static asset paths are not sent through that API rewrite

## Verified topology

```text
User -> dentixs.app / www.dentixs.app
     -> Vercel smartclinic-v2plus
        |-- SPA/assets/PWA files
        +-- /api/* -> Hugging Face production API
```

The root production Dockerfile separately embeds `frontend/dist` under the Hugging Face/FastAPI image. That copy is a secondary direct-HF frontend surface; it is not the verified custom-domain binding above.

## Operational consequence

The stale-asset/PWA forensic phase must test the Vercel custom-domain surface first. A stale hashed asset failure observed only on direct Hugging Face static serving must not automatically be treated as the production-user root cause.

## Limits

Hosting bindings are mutable external state. Re-check the Vercel project/domain assignment before future routing or stale-asset architecture changes.
