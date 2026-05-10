from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src import main as pipeline_main
from src.db import app_event_repo, pipeline_job_repo


class FakeResult:
    def __init__(self, *, scalar: Any = None, rowcount: int = 0) -> None:
        self._scalar = scalar
        self.rowcount = rowcount

    def scalar_one(self) -> Any:
        if self._scalar is None:
            raise RuntimeError("expected scalar result but got None")
        return self._scalar

    def scalar_one_or_none(self) -> Any:
        return self._scalar


class FakeConnection:
    def __init__(
        self,
        *,
        jobs: dict[str, dict[str, Any]] | None = None,
        events: list[dict[str, Any]] | None = None,
    ) -> None:
        self.jobs = jobs if jobs is not None else {}
        self.events = events if events is not None else []
        self.lock_keys: list[int] = []

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> FakeResult:
        sql = str(statement).lower()
        payload = params or {}

        if "select pg_advisory_xact_lock" in sql:
            self.lock_keys.append(int(payload["lock_key"]))
            return FakeResult(scalar=1, rowcount=1)

        if "insert into app_events" in sql:
            aggregate_id = str(payload["aggregate_id"])
            event_type = str(payload["event_type"])
            key = (aggregate_id, event_type)
            exists = any(
                event["aggregate_id"] == aggregate_id and event["event_type"] == event_type
                for event in self.events
            )
            if exists:
                return FakeResult(rowcount=0)

            self.events.append(
                {
                    "aggregate_id": aggregate_id,
                    "event_type": event_type,
                    "payload": json.loads(str(payload["payload"])),
                    "available_at": payload["available_at"],
                    "status": "pending",
                    "aggregate_type": "pipeline_job",
                }
            )
            return FakeResult(rowcount=1)

        if "update pipeline_jobs" in sql and "set status = 'failed'" in sql:
            job_id = str(payload["job_id"])
            job = self.jobs.get(job_id)
            if job is None:
                return FakeResult(scalar=None, rowcount=0)
            if job["status"] not in {"pending", "running"}:
                return FakeResult(scalar=None, rowcount=0)

            job["status"] = "failed"
            job["error_message"] = payload["error_message"]
            job["finished_at"] = payload["finished_at"]
            job["output_version"] = None
            return FakeResult(scalar=payload["job_id"], rowcount=1)

        if "select status" in sql and "from pipeline_jobs" in sql:
            job = self.jobs.get(str(payload["job_id"]))
            status = None if job is None else job["status"]
            return FakeResult(scalar=status, rowcount=1 if job is not None else 0)

        raise AssertionError(f"unsupported fake SQL statement: {statement}")


def _fake_get_connection(connection: FakeConnection) -> Any:
    @contextmanager
    def _manager() -> Any:
        yield connection

    return _manager


def test_success_zero_rejected_rows_marks_complete_and_emits_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    dataset_id = uuid4()
    expected_job_id = uuid4()
    call_order: list[str] = []
    emitted: list[dict[str, Any]] = []

    def fake_create_job(*, dataset_id: UUID, job_type: str) -> UUID:
        assert job_type == "ingestion"
        assert dataset_id
        call_order.append("create_job")
        return expected_job_id

    def fake_mark_running(*, job_id: UUID) -> None:
        assert job_id == expected_job_id
        call_order.append("mark_running")

    def fake_mark_complete(
        *,
        job_id: UUID,
        processed_rows: int,
        rejected_rows: int,
        output_version: int,
    ) -> str:
        assert job_id == expected_job_id
        assert processed_rows == 100
        assert rejected_rows == 0
        assert output_version == 7
        call_order.append("mark_complete")
        return "complete"

    def fake_emit_completed(*, pipeline_job_id: UUID, status: str, output_version: int) -> None:
        emitted.append(
            {
                "pipeline_job_id": pipeline_job_id,
                "status": status,
                "output_version": output_version,
            }
        )
        call_order.append("emit_completed")

    def fake_run_pipeline(received_job_id: UUID) -> pipeline_main.PipelineResult:
        assert received_job_id == expected_job_id
        call_order.append("run_pipeline")
        return pipeline_main.PipelineResult(
            processed_rows=100,
            rejected_rows=0,
            output_version=7,
        )

    monkeypatch.setattr(pipeline_main.pipeline_job_repo, "create_job", fake_create_job)
    monkeypatch.setattr(pipeline_main.pipeline_job_repo, "mark_running", fake_mark_running)
    monkeypatch.setattr(pipeline_main.pipeline_job_repo, "mark_complete", fake_mark_complete)
    monkeypatch.setattr(pipeline_main.app_event_repo, "emit_ingestion_completed", fake_emit_completed)

    result_job_id = pipeline_main.run_pipeline_job(
        dataset_id=dataset_id,
        job_type="ingestion",
        run_pipeline=fake_run_pipeline,
    )

    assert result_job_id == expected_job_id
    assert call_order == [
        "create_job",
        "mark_running",
        "run_pipeline",
        "mark_complete",
        "emit_completed",
    ]
    assert emitted == [
        {
            "pipeline_job_id": expected_job_id,
            "status": "complete",
            "output_version": 7,
        }
    ]


def test_success_with_rejections_marks_partial_and_emits_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    dataset_id = uuid4()
    job_id = uuid4()
    emitted: list[dict[str, Any]] = []

    monkeypatch.setattr(
        pipeline_main.pipeline_job_repo,
        "create_job",
        lambda *, dataset_id, job_type: job_id,
    )
    monkeypatch.setattr(
        pipeline_main.pipeline_job_repo,
        "mark_running",
        lambda *, job_id: None,
    )
    monkeypatch.setattr(
        pipeline_main.pipeline_job_repo,
        "mark_complete",
        lambda *, job_id, processed_rows, rejected_rows, output_version: "partial",
    )
    monkeypatch.setattr(
        pipeline_main.app_event_repo,
        "emit_ingestion_completed",
        lambda *, pipeline_job_id, status, output_version: emitted.append(
            {
                "pipeline_job_id": pipeline_job_id,
                "status": status,
                "output_version": output_version,
            }
        ),
    )

    result = pipeline_main.run_pipeline_job(
        dataset_id=dataset_id,
        job_type="ingestion",
        run_pipeline=lambda _: pipeline_main.PipelineResult(
            processed_rows=42,
            rejected_rows=3,
            output_version=11,
        ),
    )

    assert result == job_id
    assert emitted == [
        {
            "pipeline_job_id": job_id,
            "status": "partial",
            "output_version": 11,
        }
    ]


def test_failure_path_marks_failed_and_emits_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    dataset_id = uuid4()
    job_id = uuid4()
    job_state: dict[str, Any] = {
        "status": "running",
        "output_version": None,
        "error_message": None,
    }
    failed_events: list[dict[str, Any]] = []
    mark_complete_calls = 0

    monkeypatch.setattr(
        pipeline_main.pipeline_job_repo,
        "create_job",
        lambda *, dataset_id, job_type: job_id,
    )
    monkeypatch.setattr(
        pipeline_main.pipeline_job_repo,
        "mark_running",
        lambda *, job_id: None,
    )

    def fake_mark_complete(
        *,
        job_id: UUID,
        processed_rows: int,
        rejected_rows: int,
        output_version: int,
    ) -> str:
        nonlocal mark_complete_calls
        mark_complete_calls += 1
        return "complete"

    def fake_mark_failed(*, job_id: UUID, error_message: str) -> None:
        job_state["status"] = "failed"
        job_state["error_message"] = error_message
        job_state["output_version"] = None
        job_state["finished_at"] = datetime.now(timezone.utc)

    monkeypatch.setattr(pipeline_main.pipeline_job_repo, "mark_complete", fake_mark_complete)
    monkeypatch.setattr(pipeline_main.pipeline_job_repo, "mark_failed", fake_mark_failed)
    monkeypatch.setattr(
        pipeline_main.app_event_repo,
        "emit_ingestion_failed",
        lambda *, pipeline_job_id, error_message: failed_events.append(
            {
                "pipeline_job_id": pipeline_job_id,
                "error_message": error_message,
                "status": "failed",
            }
        ),
    )

    with pytest.raises(RuntimeError, match="pipeline exploded"):
        pipeline_main.run_pipeline_job(
            dataset_id=dataset_id,
            job_type="ingestion",
            run_pipeline=lambda _: (_ for _ in ()).throw(RuntimeError("pipeline exploded")),
        )

    assert mark_complete_calls == 0
    assert job_state["status"] == "failed"
    assert job_state["error_message"] == "pipeline exploded"
    assert job_state["output_version"] is None
    assert job_state["finished_at"] is not None
    assert failed_events == [
        {
            "pipeline_job_id": job_id,
            "error_message": "pipeline exploded",
            "status": "failed",
        }
    ]


def test_mark_complete_rejects_null_output_version() -> None:
    with pytest.raises(ValidationError):
        pipeline_job_repo.mark_complete(
            job_id=uuid4(),
            processed_rows=10,
            rejected_rows=0,
            output_version=None,  # type: ignore[arg-type]
        )


def test_mark_failed_leaves_output_version_null(monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = uuid4()
    jobs = {
        str(job_id): {
            "status": "running",
            "output_version": 99,
            "error_message": None,
            "finished_at": None,
        }
    }
    fake_connection = FakeConnection(jobs=jobs)
    monkeypatch.setattr(pipeline_job_repo, "get_connection", _fake_get_connection(fake_connection))

    pipeline_job_repo.mark_failed(job_id=job_id, error_message="fatal stage error")

    assert jobs[str(job_id)]["status"] == "failed"
    assert jobs[str(job_id)]["error_message"] == "fatal stage error"
    assert jobs[str(job_id)]["output_version"] is None
    assert jobs[str(job_id)]["finished_at"] is not None


def test_emit_ingestion_completed_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    pipeline_job_id = uuid4()
    events: list[dict[str, Any]] = []
    fake_connection = FakeConnection(events=events)
    monkeypatch.setattr(app_event_repo, "get_connection", _fake_get_connection(fake_connection))

    app_event_repo.emit_ingestion_completed(
        pipeline_job_id=pipeline_job_id,
        status="complete",
        output_version=5,
    )
    app_event_repo.emit_ingestion_completed(
        pipeline_job_id=pipeline_job_id,
        status="complete",
        output_version=5,
    )

    assert len(events) == 1
    assert events[0]["event_type"] == "pipeline.ingestion.completed"
    assert events[0]["aggregate_type"] == "pipeline_job"
    assert events[0]["status"] == "pending"
    assert events[0]["payload"] == {
        "type": "pipeline.ingestion.completed",
        "pipelineJobId": str(pipeline_job_id),
        "status": "complete",
        "outputVersion": 5,
    }


def test_emit_ingestion_failed_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    pipeline_job_id = uuid4()
    events: list[dict[str, Any]] = []
    fake_connection = FakeConnection(events=events)
    monkeypatch.setattr(app_event_repo, "get_connection", _fake_get_connection(fake_connection))

    app_event_repo.emit_ingestion_failed(
        pipeline_job_id=pipeline_job_id,
        error_message="fatal failure",
    )
    app_event_repo.emit_ingestion_failed(
        pipeline_job_id=pipeline_job_id,
        error_message="fatal failure",
    )

    assert len(events) == 1
    assert events[0]["event_type"] == "pipeline.ingestion.failed"
    assert events[0]["aggregate_type"] == "pipeline_job"
    assert events[0]["status"] == "pending"
    assert events[0]["payload"] == {
        "type": "pipeline.ingestion.failed",
        "pipelineJobId": str(pipeline_job_id),
        "status": "failed",
        "errorMessage": "fatal failure",
    }


def test_orchestrator_reraises_original_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    dataset_id = uuid4()
    job_id = uuid4()
    original_error = RuntimeError("original error")
    captured_failed_error_messages: list[str] = []

    monkeypatch.setattr(
        pipeline_main.pipeline_job_repo,
        "create_job",
        lambda *, dataset_id, job_type: job_id,
    )
    monkeypatch.setattr(
        pipeline_main.pipeline_job_repo,
        "mark_running",
        lambda *, job_id: None,
    )
    monkeypatch.setattr(
        pipeline_main.pipeline_job_repo,
        "mark_failed",
        lambda *, job_id, error_message: captured_failed_error_messages.append(error_message),
    )
    monkeypatch.setattr(
        pipeline_main.app_event_repo,
        "emit_ingestion_failed",
        lambda *, pipeline_job_id, error_message: None,
    )

    def failing_pipeline(_: UUID) -> pipeline_main.PipelineResult:
        raise original_error

    with pytest.raises(RuntimeError) as raised:
        pipeline_main.run_pipeline_job(
            dataset_id=dataset_id,
            job_type="ingestion",
            run_pipeline=failing_pipeline,
        )

    assert raised.value is original_error
    assert captured_failed_error_messages == ["original error"]
