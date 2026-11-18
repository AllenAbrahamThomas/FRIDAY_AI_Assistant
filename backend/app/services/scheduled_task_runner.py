import asyncio
import datetime
import logging
from typing import Optional

from app.core.orchestrator import friday_orchestrator
from app.services.scheduled_task_service import (
    ScheduledTaskService,
    scheduled_task_service
)

logger = logging.getLogger(__name__)


class ScheduledTaskRunner:
    def __init__(
        self,
        service: Optional[ScheduledTaskService] = None,
        poll_interval_seconds: int = 30
    ):
        self.service = service or scheduled_task_service
        self.poll_interval_seconds = poll_interval_seconds

    async def run_forever(self) -> None:
        try:
            recovered = await asyncio.to_thread(self.service.recover_interrupted_runs)
            if recovered:
                logger.warning("Marked %s interrupted scheduled task runs as failed", recovered)
        except Exception as error:
            logger.error(
                "Could not recover interrupted scheduled task runs (%s)",
                type(error).__name__
            )

        while True:
            try:
                due_tasks = await asyncio.to_thread(
                    self.service.claim_due_tasks,
                    datetime.datetime.now(datetime.timezone.utc)
                )
            except Exception as error:
                logger.error("Could not check for due scheduled tasks (%s)", type(error).__name__)
                await asyncio.sleep(self.poll_interval_seconds)
                continue

            for task in due_tasks:
                try:
                    result = await friday_orchestrator.process_request(task["prompt"])
                    status = "failed" if result.error else "completed"
                    await asyncio.to_thread(
                        self.service.finish_run,
                        task["run_id"],
                        status,
                        result.response,
                        result.error
                    )
                except asyncio.CancelledError:
                    await asyncio.to_thread(
                        self.service.finish_run,
                        task["run_id"],
                        "failed",
                        None,
                        "Backend stopped before this run completed; it was not retried automatically."
                    )
                    raise
                except Exception as error:
                    logger.error(
                        "Scheduled task %s failed during execution (%s)",
                        task["task_id"],
                        type(error).__name__
                    )
                    try:
                        await asyncio.to_thread(
                            self.service.finish_run,
                            task["run_id"],
                            "failed",
                            None,
                            "Scheduled task failed. Check backend logs for details."
                        )
                    except Exception as error:
                        logger.error(
                            "Could not record failure for scheduled task %s (%s)",
                            task["task_id"],
                            type(error).__name__
                        )

            await asyncio.sleep(self.poll_interval_seconds)


scheduled_task_runner = ScheduledTaskRunner()
