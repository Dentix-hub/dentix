import sys
import os

# Setup paths
sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend.services.job_service import JobService


def test_operational_phase5():
    print("\n>>> Testing Phase 5: Operational Tools (Background Jobs)...")
    db = SessionLocal()

    try:
        # 1. Test Job Start
        print("\n[1] Testing Job Start...")
        job = JobService.start_job(db, "test_job_beta", "script_runner")
        print(f" - Job Started: ID={job.id}, Status={job.status}")

        if job.status == "running":
            print(" - Start Logic: PASS")
        else:
            print(" - Start Logic: FAIL")

        # 2. Test Job Completion
        print("\n[2] Testing Job Completion...")
        # Simulate delay
        import time

        time.sleep(0.5)

        updated_job = JobService.complete_job(db, job.id, "success")
        print(
            f" - Job Completed: Status={updated_job.status}, Duration={updated_job.duration_seconds}s"
        )

        if updated_job.status == "success" and updated_job.duration_seconds > 0:
            print(" - Completion Logic: PASS")
        else:
            print(" - Completion Logic: FAIL")

        # 3. Test Retrieve History
        print("\n[3] Testing Job History Retrieval...")
        jobs = JobService.get_recent_jobs(db, limit=5)
        print(f" - Fetched {len(jobs)} recent jobs")

        found = any(j.id == job.id for j in jobs)
        if found:
            print(" - History Retrieval: PASS")
        else:
            print(" - History Retrieval: FAIL")

    except Exception as e:
        print(f"!!! CRITICAL FAIL: {e}")
    finally:
        # Cleanup (optional, keeping logs is fine for debug)
        db.close()


if __name__ == "__main__":
    test_operational_phase5()
