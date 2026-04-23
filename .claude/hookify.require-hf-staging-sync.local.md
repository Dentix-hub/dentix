---
name: require-hf-staging-sync
enabled: true
event: bash
pattern: git\s+push\s+origin\s+staging
---

# 🚀 HF-STAGING SYNC REQUIRED

The user has requested that updates to the staging branch be pushed directly to **hf-staging** as well.

Whenever you push to `origin staging`, you MUST also run:
`git push hf-staging staging:main --force`

This ensures the Hugging Face Space is updated immediately and matches the GitHub staging branch.
