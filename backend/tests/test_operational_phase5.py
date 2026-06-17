import sys
import os
import pytest

# Setup paths
sys.path.append(os.getcwd())

from backend.services.job_service import JobService


@pytest.mark.asyncio
async def test_operational_phase5(async_db_session):
    print("\n>>> Testing Phase 5: Operational Tools (Background Jobs)...")
    db = async_db_session

    try:
        # 1. Test Job Start
        print("\n[1] Testing Job Start...")
        job = await JobService.start_job(db, "test_job_beta", "script_runner")
        print(f" - Job Started: ID={job.id}, Status={job.status}")

        if job.status == "running":
            print(" - Start Logic: PASS")
        else:
            print(" - Start Logic: FAIL")
            assert False, "Job start logic failed"

        # 2. Test Job Completion
        print("\n[2] Testing Job Completion...")
        import asyncio

        await asyncio.sleep(0.5)

        updated_job = await JobService.complete_job(db, job.id, "success")
        print(
            f" - Job Completed: Status={updated_job.status}, Duration={updated_job.duration_seconds}s"
        )

        if updated_job.status == "success" and updated_job.duration_seconds > 0:
            print(" - Completion Logic: PASS")
        else:
            print(" - Completion Logic: FAIL")
            assert False, "Job completion logic failed"

        # 3. Test Retrieve History
        print("\n[3] Testing Job History Retrieval...")
        jobs = await JobService.get_recent_jobs(db, limit=5)
        print(f" - Fetched {len(jobs)} recent jobs")

        found = any(j.id == job.id for j in jobs)
        if found:
            print(" - History Retrieval: PASS")
        else:
            print(" - History Retrieval: FAIL")
            assert False, "Job history retrieval failed"

    finally:
        pass


if __name__ == "__main__":
    import asyncio
    from backend.database import AsyncSessionLocal
    async def run_standalone():
        async with AsyncSessionLocal() as session:
            await test_operational_phase5(session)
    asyncio.run(run_standalone())

