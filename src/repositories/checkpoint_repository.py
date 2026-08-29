"""Persistence layer for the Checkpoint entity using Supabase Data API."""

from __future__ import annotations

from typing import Any, Mapping, cast
from uuid import UUID, uuid4

from supabase import Client

from database.connection import get_supabase_client


Numeric = int | float


class CheckpointRepositoryError(RuntimeError):
    """Base error for persistence failures in CheckpointRepository."""


class CheckpointRepository:
    """Repository responsible for persisting checkpoint records in Supabase."""

    _SCHEMA = "core"
    _TABLE = "checkpoint"
    _UNSET = object()
    _CHECKPOINT_TYPES = {"best", "elite", "manual"}

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
        run_id: UUID | str,
        generation_id: UUID | str,
        storage_path: str,
        checkpoint_type: str = "best",
        individual_id: UUID | str | None = None,
        storage_bucket: str | None = None,
        fitness: Numeric | None = None,
        metrics: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a checkpoint record and return the persisted row.

        Args:
            run_id: Related run UUID.
            generation_id: Related generation UUID.
            storage_path: Path where the checkpoint artifact is stored.
            checkpoint_type: Checkpoint type constrained by the database.
            individual_id: Optional related individual UUID.
            storage_bucket: Optional storage bucket name.
            fitness: Optional fitness value.
            metrics: Optional metrics payload.

        Returns:
            The created checkpoint row.

        Raises:
            ValueError: If required values are invalid or constraints are
                violated.
            TypeError: If UUID, text, numeric, or JSON payloads have an invalid
                type.
            CheckpointRepositoryError: If the operation fails or the inserted
                row cannot be retrieved.
        """

        normalized_run_id = self._normalize_uuid_like(run_id, "run_id")
        normalized_generation_id = self._normalize_uuid_like(generation_id, "generation_id")
        normalized_individual_id = self._normalize_nullable_uuid_like(
            individual_id, "individual_id"
        )
        normalized_checkpoint_type = self._normalize_checkpoint_type(
            checkpoint_type, "checkpoint_type"
        )
        normalized_storage_path = self._normalize_required_text(storage_path, "storage_path")
        normalized_storage_bucket = self._normalize_optional_text(
            storage_bucket, "storage_bucket"
        )
        normalized_metrics = self._normalize_jsonb_mapping(metrics, "metrics")
        self._validate_optional_number(fitness, "fitness")

        payload: dict[str, Any] = {
            "id": str(uuid4()),
            "run_id": normalized_run_id,
            "generation_id": normalized_generation_id,
            "individual_id": normalized_individual_id,
            "checkpoint_type": normalized_checkpoint_type,
            "storage_path": normalized_storage_path,
            "storage_bucket": normalized_storage_bucket,
            "fitness": fitness,
            "metrics": normalized_metrics,
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
        except CheckpointRepositoryError:
            raise
        except Exception as exc:
            raise CheckpointRepositoryError("Failed to create checkpoint in Supabase.") from exc

        if created is None:
            raise CheckpointRepositoryError(
                "Checkpoint was inserted but could not be retrieved afterward."
            )

        return created

    def get_by_id(self, checkpoint_id: UUID | str) -> dict[str, Any] | None:
        """Fetch one checkpoint by its UUID identifier.

        Args:
            checkpoint_id: Checkpoint UUID.

        Returns:
            The checkpoint row when found, otherwise None.

        Raises:
            TypeError: If checkpoint_id has an invalid type.
            ValueError: If checkpoint_id is empty or invalid.
            CheckpointRepositoryError: If the read operation fails.
        """

        identifier = self._normalize_uuid_like(checkpoint_id, "checkpoint_id")

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
            raise CheckpointRepositoryError("Failed to fetch checkpoint by id.") from exc

        return self._first_or_none(response.data)

    def list_by_run(self, run_id: UUID | str) -> list[dict[str, Any]]:
        """List checkpoints associated with a run.

        Args:
            run_id: Run UUID.

        Returns:
            A list of checkpoint rows ordered deterministically.

        Raises:
            TypeError: If run_id has an invalid type.
            ValueError: If run_id is empty or invalid.
            CheckpointRepositoryError: If the read operation fails.
        """

        identifier = self._normalize_uuid_like(run_id, "run_id")

        try:
            response = (
                self._client.schema(self._SCHEMA)
                .table(self._TABLE)
                .select("*")
                .eq("run_id", identifier)
                .order("generation_id", desc=False)
                .order("checkpoint_type", desc=False)
                .order("created_at", desc=False)
                .order("id", desc=False)
                .execute()
            )
        except Exception as exc:
            raise CheckpointRepositoryError("Failed to list checkpoints by run.") from exc

        rows = response.data or []
        return [row for row in rows if isinstance(row, dict)]

    def list_by_generation(self, generation_id: UUID | str) -> list[dict[str, Any]]:
        """List checkpoints associated with a generation.

        Args:
            generation_id: Generation UUID.

        Returns:
            A list of checkpoint rows for the generation.

        Raises:
            TypeError: If generation_id has an invalid type.
            ValueError: If generation_id is empty or invalid.
            CheckpointRepositoryError: If the read operation fails.
        """

        identifier = self._normalize_uuid_like(generation_id, "generation_id")

        try:
            response = (
                self._client.schema(self._SCHEMA)
                .table(self._TABLE)
                .select("*")
                .eq("generation_id", identifier)
                .order("checkpoint_type", desc=False)
                .order("created_at", desc=False)
                .order("id", desc=False)
                .execute()
            )
        except Exception as exc:
            raise CheckpointRepositoryError(
                "Failed to list checkpoints by generation."
            ) from exc

        rows = response.data or []
        return [row for row in rows if isinstance(row, dict)]

    def list_all(self) -> list[dict[str, Any]]:
        """List all checkpoints in a deterministic order.

        Returns:
            A list of checkpoint rows.

        Raises:
            CheckpointRepositoryError: If the read operation fails.
        """

        try:
            response = (
                self._client.schema(self._SCHEMA)
                .table(self._TABLE)
                .select("*")
                .order("run_id", desc=False)
                .order("generation_id", desc=False)
                .order("checkpoint_type", desc=False)
                .order("created_at", desc=False)
                .order("id", desc=False)
                .execute()
            )
        except Exception as exc:
            raise CheckpointRepositoryError("Failed to list checkpoints.") from exc

        rows = response.data or []
        return [row for row in rows if isinstance(row, dict)]

    def update(
        self,
        checkpoint_id: UUID | str,
        *,
        run_id: UUID | str | object = _UNSET,
        generation_id: UUID | str | object = _UNSET,
        individual_id: UUID | str | None | object = _UNSET,
        checkpoint_type: str | object = _UNSET,
        storage_path: str | object = _UNSET,
        storage_bucket: str | None | object = _UNSET,
        fitness: Numeric | None | object = _UNSET,
        metrics: Mapping[str, Any] | None | object = _UNSET,
    ) -> dict[str, Any] | None:
        """Update a checkpoint and return the updated row.

        Args:
            checkpoint_id: Checkpoint UUID.
            run_id: Updated run UUID.
            generation_id: Updated generation UUID.
            individual_id: Updated individual UUID.
            checkpoint_type: Updated checkpoint type.
            storage_path: Updated storage path.
            storage_bucket: Updated storage bucket.
            fitness: Updated fitness value.
            metrics: Updated metrics payload.

        Returns:
            The updated checkpoint row when found, otherwise None.

        Raises:
            ValueError: If no update fields are provided.
            TypeError: If a provided field has an invalid type.
            CheckpointRepositoryError: If the update operation fails.
        """

        identifier = self._normalize_uuid_like(checkpoint_id, "checkpoint_id")
        payload: dict[str, Any] = {}

        if run_id is not self._UNSET:
            payload["run_id"] = self._normalize_uuid_like(run_id, "run_id")
        if generation_id is not self._UNSET:
            payload["generation_id"] = self._normalize_uuid_like(generation_id, "generation_id")
        if individual_id is not self._UNSET:
            payload["individual_id"] = self._normalize_nullable_uuid_like(
                individual_id, "individual_id"
            )
        if checkpoint_type is not self._UNSET:
            payload["checkpoint_type"] = self._normalize_checkpoint_type(
                checkpoint_type, "checkpoint_type"
            )
        if storage_path is not self._UNSET:
            payload["storage_path"] = self._normalize_required_text(
                storage_path, "storage_path"
            )
        if storage_bucket is not self._UNSET:
            payload["storage_bucket"] = self._normalize_optional_text(
                storage_bucket, "storage_bucket"
            )
        if fitness is not self._UNSET:
            self._validate_optional_number(fitness, "fitness")
            payload["fitness"] = fitness
        if metrics is not self._UNSET:
            payload["metrics"] = self._normalize_jsonb_mapping(metrics, "metrics")

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
        except CheckpointRepositoryError:
            raise
        except Exception as exc:
            raise CheckpointRepositoryError("Failed to update checkpoint.") from exc

        return self.get_by_id(identifier)

    def delete(self, checkpoint_id: UUID | str) -> bool:
        """Delete a checkpoint by UUID.

        Args:
            checkpoint_id: Checkpoint UUID.

        Returns:
            True when a record existed and was deleted, otherwise False.

        Raises:
            TypeError: If checkpoint_id has an invalid type.
            ValueError: If checkpoint_id is empty or invalid.
            CheckpointRepositoryError: If the delete operation fails.
        """

        identifier = self._normalize_uuid_like(checkpoint_id, "checkpoint_id")
        existing = self.get_by_id(identifier)
        if existing is None:
            return False

        try:
            self._client.schema(self._SCHEMA).table(self._TABLE).delete().eq("id", identifier).execute()
        except Exception as exc:
            raise CheckpointRepositoryError("Failed to delete checkpoint.") from exc

        return True

    @staticmethod
    def _first_or_none(rows: Any) -> dict[str, Any] | None:
        """Return the first row from a list-like API response or None."""

        if isinstance(rows, list) and rows:
            first_row = rows[0]
            if isinstance(first_row, dict):
                return first_row
        return None

    @staticmethod
    def _validate_optional_number(value: object, field_name: str) -> None:
        """Validate an optional numeric field."""

        if value is None:
            return
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"{field_name} must be an int, float, or None when provided.")

    @staticmethod
    def _normalize_required_text(value: object, field_name: str) -> str:
        """Normalize a required text field."""

        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a str.")
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError(f"{field_name} must not be empty or whitespace.")
        return normalized_value

    @staticmethod
    def _normalize_optional_text(value: object, field_name: str) -> str | None:
        """Normalize an optional text field, preserving None."""

        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a str or None when provided.")
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError(f"{field_name} must not be empty or whitespace.")
        return normalized_value

    @staticmethod
    def _normalize_checkpoint_type(value: object, field_name: str) -> str:
        """Validate and normalize the checkpoint type."""

        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a str.")
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError(f"{field_name} must not be empty or whitespace.")
        if normalized_value not in CheckpointRepository._CHECKPOINT_TYPES:
            raise ValueError(
                f"{field_name} must be one of: {', '.join(sorted(CheckpointRepository._CHECKPOINT_TYPES))}."
            )
        return normalized_value

    @staticmethod
    def _normalize_jsonb_mapping(value: object, field_name: str) -> dict[str, Any]:
        """Normalize an optional JSONB mapping field to a dictionary."""

        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise TypeError(f"{field_name} must be a mapping or None when provided.")
        return dict(cast(Mapping[str, Any], value))

    @staticmethod
    def _normalize_nullable_uuid_like(value: object, field_name: str) -> str | None:
        """Normalize an optional UUID-like field to canonical string form."""

        if value is None:
            return None
        return CheckpointRepository._normalize_uuid_like(value, field_name)

    @staticmethod
    def _normalize_uuid_like(value: object, field_name: str) -> str:
        """Normalize a UUID-like field to canonical string form after validation."""

        if isinstance(value, UUID):
            return str(value)
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a UUID or str when provided.")
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError(f"{field_name} must not be empty or whitespace.")
        try:
            return str(UUID(normalized_value))
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a valid UUID.") from exc
