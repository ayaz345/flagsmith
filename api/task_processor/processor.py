import logging
import traceback
import typing

from django.utils import timezone

from task_processor.models import (
    RecurringTask,
    RecurringTaskRun,
    Task,
    TaskResult,
    TaskRun,
)

logger = logging.getLogger(__name__)


def run_tasks(num_tasks: int = 1) -> typing.List[TaskRun]:
    if num_tasks < 1:
        raise ValueError("Number of tasks to process must be at least one")

    if tasks := Task.objects.get_tasks_to_process(num_tasks):
        executed_tasks = []
        task_runs = []

        for task in tasks:
            task, task_run = _run_task(task)

            executed_tasks.append(task)
            task_runs.append(task_run)

        if executed_tasks:
            Task.objects.bulk_update(
                executed_tasks, fields=["completed", "num_failures", "is_locked"]
            )

        if task_runs:
            TaskRun.objects.bulk_create(task_runs)

        return task_runs

    logger.debug("No tasks to process.")
    return []


def run_recurring_tasks(num_tasks: int = 1) -> typing.List[RecurringTask]:
    if num_tasks < 1:
        raise ValueError("Number of tasks to process must be at least one")

    if tasks := RecurringTask.objects.get_tasks_to_process(num_tasks):
        task_runs = []
        executed_tasks = []

        for task in tasks:
            # Remove the task if it's not registered anymore
            if not task.is_task_registered:
                task.delete()
                continue

            if task.should_execute:
                task, task_run = _run_task(task)
                executed_tasks.append(task)
                task_runs.append(task_run)

        if executed_tasks:
            RecurringTask.objects.bulk_update(executed_tasks, fields=["is_locked"])

        if task_runs:
            RecurringTaskRun.objects.bulk_create(task_runs)

        return task_runs

    logger.debug("No tasks to process.")
    return []


def _run_task(task: Task) -> typing.Optional[typing.Tuple[Task, TaskRun]]:
    task_run = task.task_runs.model(started_at=timezone.now(), task=task)

    try:
        task.run()
        task_run.result = TaskResult.SUCCESS

        task_run.finished_at = timezone.now()
        task.mark_success()
    except Exception:
        task.mark_failure()

        task_run.result = TaskResult.FAILURE
        task_run.error_details = str(traceback.format_exc())

    return task, task_run
