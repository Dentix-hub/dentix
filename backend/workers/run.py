import asyncio
import argparse
import logging
import sys
from backend.workers.event_processor import poll_outbox
from backend.workers.subscription_checker import start_subscription_checker_loop

# Set up logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("smart_clinic.workers.run")

async def main():
    parser = argparse.ArgumentParser(description="Run Dentix background workers.")
    parser.add_argument(
        "--workers",
        choices=["all", "events", "subscriptions"],
        default="all",
        help="Which workers to run (default: all)",
    )
    args = parser.parse_args()

    tasks = []
    if args.workers in ("all", "events"):
        logger.info("Starting outbox event processor worker...")
        tasks.append(asyncio.create_task(poll_outbox(poll_interval=5)))
    if args.workers in ("all", "subscriptions"):
        logger.info("Starting subscription checker worker...")
        # For daemon running, checking every 12 hours is normal, but let's allow it to start immediately
        tasks.append(asyncio.create_task(start_subscription_checker_loop(interval_hours=12)))

    if not tasks:
        logger.error("No workers selected to run.")
        return

    # Keep tasks running
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Worker tasks cancelled. Shutting down gracefully...")
    except Exception as e:
        logger.critical(f"Worker runtime failed with critical error: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down workers.")
