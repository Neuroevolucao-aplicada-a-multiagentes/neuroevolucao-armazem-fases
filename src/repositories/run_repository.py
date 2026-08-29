"""Persistence layer for the Run entity using Supabase Data API."""

from __future__ import annotations

from typing import Any, Mapping, cast
from uuid import UUID, uuid4

from supabase import Client

from database.connection import get_supabase_client


class RunRepositoryError(RuntimeError):
    """Base error for persistence failures in RunRepository."""


class RunRepository:
    """Repository responsible for persisting Run records in Supabase."""

    _SCHEMA = "core"
    _TABLE = "run"
    _UNSET = object()

    def __init__(self, client: Client | None = None) -> None:
        """Initialize the repository with a Supabase client.

        Args:
            client: Optional Supabase client instance for dependency injection
                in tests. When not provided, the shared project client is used.
        """

        self._client = client if client is not None else get_supabase_client()

    def create(
        self,
        *,
        experiment_id: UUID | str,
        phase_code: str,
        run_label: str | None = None,
        seed: int | None = None,
        status: str = "pending",
        started_at: str | None = None,
        finished_at: str | None = None,
        summary_metrics: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a Run record and return the persisted row.

        Args:
            experiment_id: Related experiment UUID.
            phase_code: Code for the training phase.
            run_label: Optional run label.
            seed: Optional deterministic seed.
            status: Initial run status.
            started_at: Optional run start timestamp.
            finished_at: Optional run end timestamp.
            summary_metrics: Optional summary metrics payload.
            metadata: Optional metadata payload.

        Returns:
            The created run row.

        Raises:
            RunRepositoryError: If the operation fails or the inserted row
                cannot be retrieved.
            ValueError: If phase_code or status is empty/whitespace.
            TypeError: If seed has an invalid type.
        """

        normalized_phase_code = phase_code.strip()
        if not normalized_phase_code:
            raise ValueError("phase_code must not be empty or whitespace.")

        normalized_status = status.strip()
        if not normalized_status:
            raise ValueError("status must not be empty or whitespace.")

        if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
            raise TypeError("seed must be an int or None when provided.")

        payload: dict[str, Any] = {
            "id": str(uuid4()),
            "experiment_id": str(experiment_id),
            "phase_code": normalized_phase_code,
            "run_label": run_label,
            "seed": seed,
            "status": normalized_status,
            "started_at": started_at,
            "finished_at": finished_at,
            "summary_metrics": dict(summary_metrics) if summary_metrics is not None else {},
            "metadata": dict(metadata) if metadata is not None else {},
        }

        created_id = payload["id"]

        try:
            response = (
                self._client.schema(self._SCHEMA)
                .table(self._TABLE)
                .insert(payload)
                .execute()
            )
            created = self._first_or_none(response.data)
            if created is None:
                created = self.get_by_id(created_id)
        except RunRepositoryError:
            raise
        except Exception as exc:
            raise RunRepositoryError("Failed to create run in Supabase.") from exc

        if created is None:
            raise RunRepositoryError("Run was inserted but could not be retrieved afterward.")

        return created

    def get_by_id(self, run_id: UUID | str) -> dict[str, Any] | None:
        """Fetch one Run by its UUID identifier.

        Args:
            run_id: Run UUID.

        Returns:
            The run row when found, otherwise None.

        Raises:
            RunRepositoryError: If the read operation fails.
        """

        identifier = str(run_id)

        try:
            response = (
                self._client.schema(self._SCHEMA)
                .table(self._TABLE)
                .select("*")
                .eq("id", identifier)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise RunRepositoryError("Failed to fetch run by id.") from exc

        return self._first_or_none(response.data)

    def list_by_experiment(self, experiment_id: UUID | str) -> list[dict[str, Any]]:
        """List Run rows associated with an experiment.

        Args:
            experiment_id: Experiment UUID.

        Returns:
            A list of run rows ordered by creation timestamp.

        Raises:
            RunRepositoryError: If the read operation fails.
        """

        try:
            response = (
                self._client.schema(self._SCHEMA)
                .table(self._TABLE)
                .select("*")
                .eq("experiment_id", str(experiment_id))
                .order("created_at", desc=False)
                .execute()
            )
        except Exception as exc:
            raise RunRepositoryError("Failed to list runs by experiment.") from exc

        rows = response.data or []
        return [row for row in rows if isinstance(row, dict)]

    def list_all(self) -> list[dict[str, Any]]:
        """List all Run rows ordered by creation timestamp.

        Returns:
            A list of run rows.

        Raises:
            RunRepositoryError: If the read operation fails.
        """

        try:
            response = (
                self._client.schema(self._SCHEMA)
                .table(self._TABLE)
                .select("*")
                .order("created_at", desc=False)
                .execute()
            )
        except Exception as exc:
            raise RunRepositoryError("Failed to list runs.") from exc

        rows = response.data or []
        return [row for row in rows if isinstance(row, dict)]

    def update(
        self,
        run_id: UUID | str,
        *,
        experiment_id: UUID | str | object = _UNSET,
        phase_code: str | object = _UNSET,
        run_label: str | None | object = _UNSET,
        seed: int | None | object = _UNSET,
        status: str | object = _UNSET,
        started_at: str | None | object = _UNSET,
        finished_at: str | None | object = _UNSET,
        summary_metrics: Mapping[str, Any] | None | object = _UNSET,
        metadata: Mapping[str, Any] | None | object = _UNSET,
    ) -> dict[str, Any] | None:
        """Update a Run and return the updated row.

        Args:
            run_id: Run UUID.
            experiment_id: Updated experiment UUID.
            phase_code: Updated phase code.
            run_label: Updated run label.
            seed: Updated seed.
            status: Updated status.
            started_at: Updated start timestamp.
            finished_at: Updated finish timestamp.
            summary_metrics: Updated summary metrics.
            metadata: Updated metadata.

        Returns:
            The updated run row when found, otherwise None.

        Raises:
            ValueError: If no update fields are provided.
            TypeError: If a provided typed field has an invalid type.
            RunRepositoryError: If the update operation fails.
        """

        identifier = str(run_id)
        payload: dict[str, Any] = {}

        if experiment_id is not self._UNSET:
            if not isinstance(experiment_id, (UUID, str)):
                raise TypeError("experiment_id must be a UUID or str when provided.")
            payload["experiment_id"] = str(experiment_id)
        if phase_code is not self._UNSET:
            if not isinstance(phase_code, str):
                raise TypeError("phase_code must be a str when provided.")
            normalized_phase_code = phase_code.strip()
            if not normalized_phase_code:
                raise ValueError("phase_code must not be empty or whitespace.")
            payload["phase_code"] = normalized_phase_code
        if run_label is not self._UNSET:
            if run_label is not None and not isinstance(run_label, str):
                raise TypeError("run_label must be a str or None when provided.")
            payload["run_label"] = run_label
        if seed is not self._UNSET:
            if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
                raise TypeError("seed must be an int or None when provided.")
            payload["seed"] = seed
        if status is not self._UNSET:
            if not isinstance(status, str):
                raise TypeError("status must be a str when provided.")
            normalized_status = status.strip()
            if not normalized_status:
                raise ValueError("status must not be empty or whitespace.")
            payload["status"] = normalized_status
        if started_at is not self._UNSET:
            if started_at is not None and not isinstance(started_at, str):
                raise TypeError("started_at must be a str or None when provided.")
            payload["started_at"] = started_at
        if finished_at is not self._UNSET:
            if finished_at is not None and not isinstance(finished_at, str):
                raise TypeError("finished_at must be a str or None when provided.")
            payload["finished_at"] = finished_at
        if summary_metrics is not self._UNSET:
            if summary_metrics is None:
                payload["summary_metrics"] = {}
            else:
                payload["summary_metrics"] = dict(cast(Mapping[str, Any], summary_metrics))
        if metadata is not self._UNSET:
            if metadata is None:
                payload["metadata"] = {}
            else:
                payload["metadata"] = dict(cast(Mapping[str, Any], metadata))

        if not payload:
            raise ValueError("At least one field must be provided for update.")

        try:
            response = (
                self._client.schema(self._SCHEMA)
                .table(self._TABLE)
                .update(payload)
                .eq("id", identifier)
                .execute()
            )
            updated = self._first_or_none(response.data)
            if updated is not None:
                return updated
        except Exception as exc:
            raise RunRepositoryError("Failed to update run.") from exc

        return self.get_by_id(identifier)

    def delete(self, run_id: UUID | str) -> bool:
        """Delete a Run by UUID.

        Args:
            run_id: Run UUID.

        Returns:
            True when a record existed and was deleted, otherwise False.

        Raises:
            RunRepositoryError: If the delete operation fails.
        """

        try:
            identifier = str(run_id)
            response = (
                self._client.schema(self._SCHEMA)
                .table(self._TABLE)
                .delete()
                .eq("id", identifier)
                .execute()
            )

            if isinstance(response.data, list):
                return len(response.data) > 0

            return self.get_by_id(identifier) is None
        except Exception as exc:
            raise RunRepositoryError("Failed to delete run.") from exc

    @staticmethod
    def _first_or_none(rows: Any) -> dict[str, Any] | None:
        """Return the first row from a list-like API response or None."""

        if isinstance(rows, list) and rows:
            first_row = rows[0]
            if isinstance(first_row, dict):
                return first_row
        return None
