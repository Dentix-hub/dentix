# Supabase Migration Task List

## Goal
Migrate database from Neon to Supabase and ensure API connectivity.

## Tasks
- [ ] Task 1: Update `.env` with Supabase `DATABASE_URL` → Verify: `.env` content matches Supabase dashboard
- [ ] Task 2: Validate SSL and Pooling config in `backend/database.py` → Verify: `DB_SSL_MODE=require`
- [ ] Task 3: Run schema initialization → `alembic upgrade head`
- [ ] Task 4: Setup Firebase Admin SDK → Install `firebase-admin`
- [ ] Task 5: Add Firebase Service Account configuration → Create `firebase-service-account.json` (placeholder)
- [ ] Task 6: Final system audit → Run `python .agent/scripts/checklist.py .`

## Done When
- [ ] Backend starts without DB errors.
- [ ] `alembic` reports successful migration.
- [ ] Firebase initialization succeeds without errors.
