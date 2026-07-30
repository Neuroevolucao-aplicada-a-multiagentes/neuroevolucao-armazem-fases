"""Persistence layer for the RunConfigSnapshot entity using Supabase Data API."""

from __future__ import annotations

from typing import Any, Mapping, cast
from uuid import UUID, uuid4

from supabase import Client

from database.connection import get_supabase_client


class RunConfigSnapshotRepositoryError(RuntimeError):
    """Base error for persistence failures in RunConfigSnapshotRepository."""


class RunConfigSnapshotRepository:
    """Repository responsible for persisting run config snapshots in Supabase."""

    _SCHEMA = "core"
    _TABLE = "run_config_snapshot"
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
        run_id: UUID | str,
        config: Mapping[str, Any],
        config_hash: str | None = None,
    ) -> dict[str, Any]:
        """Create a run config snapshot and return the persisted row.

        Args:
            run_id: Related run UUID.
            config: Snapshot configuration payload.
            config_hash: Optional hash for the configuration.

        Returns:
            The created snapshot row.

        Raises:
            TypeError: If run_id or config_hash has an invalid type.
            ValueError: If run_id, config, or config_hash are invalid.
            RunConfigSnapshotRepositoryError: If the operation fails or the
                inserted row cannot be retrieved.
        """

        normalized_run_id = self._normalize_uuid_like(run_id, "run_id")
        normalized_config_hash = self._normalize_text_or_none(config_hash, "config_hash")
        self._validate_required_mapping(config, "config")

        payload: dict[str, Any] = {
            "id": str(uuid4()),
            "run_id": normalized_run_id,
            "config": dict(config),
            "config_hash": normalized_config_hash,
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
        except RunConfigSnapshotRepositoryError:
            raise
        except Exception as exc:
            raise RunConfigSnapshotRepositoryError(
                "Failed to create run config snapshot in Supabase."
            ) from exc

        if created is None:
            raise RunConfigSnapshotRepositoryError(
                "Run config snapshot was inserted but could not be retrieved afterward."
            )

        return created

    def get_by_id(self, snapshot_id: UUID | str) -> dict[str, Any] | None:
        """Fetch one run config snapshot by its UUID identifier.

        Args:
            snapshot_id: Snapshot UUID.

        Returns:
            The snapshot row when found, otherwise None.

        Raises:
            TypeError: If snapshot_id has an invalid type.
            ValueError: If snapshot_id is empty or invalid.
            RunConfigSnapshotRepositoryError: If the read operation fails.
        """

        identifier = self._normalize_uuid_like(snapshot_id, "snapshot_id")

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
            raise RunConfigSnapshotRepositoryError(
                "Failed to fetch run config snapshot by id."
            ) from exc

        return self._first_or_none(response.data)

    def get_by_run(self, run_id: UUID | str) -> dict[str, Any] | None:
        """Fetch the snapshot associated with a run.

        Args:
            run_id: Run UUID.

        Returns:
            The snapshot row when found, otherwise None.

        Raises:
            TypeError: If run_id has an invalid type.
            ValueError: If run_id is empty or invalid.
            RunConfigSnapshotRepositoryError: If the read operation fails.
        """

        identifier = self._normalize_uuid_like(run_id, "run_id")

        try:
            response = (
                self._client.schema(self._SCHEMA)
                .table(self._TABLE)
                .select("*")
                .eq("run_id", identifier)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise RunConfigSnapshotRepositoryError(
                "Failed to fetch run config snapshot by run."
            ) from exc

        return self._first_or_none(response.data)

    def list_all(self) -> list[dict[str, Any]]:
        """List all run config snapshots ordered by creation timestamp.

        Returns:
            A list of snapshot rows.

        Raises:
            RunConfigSnapshotRepositoryError: If the read operation fails.
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
            raise RunConfigSnapshotRepositoryError(
                "Failed to list run config snapshots."
            ) from exc

        rows = response.data or []
        return [row for row in rows if isinstance(row, dict)]

    def update(
        self,
        snapshot_id: UUID | str,
        *,
        run_id: UUID | str | object = _UNSET,
        config: Mapping[str, Any] | object = _UNSET,
        config_hash: str | None | object = _UNSET,
    ) -> dict[str, Any] | None:
        """Update a run config snapshot and return the updated row.

        Args:
            snapshot_id: Snapshot UUID.
            run_id: Updated run UUID.
            config: Updated snapshot configuration payload.
            config_hash: Updated configuration hash.

        Returns:
            The updated snapshot row when found, otherwise None.

        Raises:
            ValueError: If no update fields are provided.
            TypeError: If a provided field has an invalid type.
            RunConfigSnapshotRepositoryError: If the update operation fails.
        """

        identifier = self._normalize_uuid_like(snapshot_id, "snapshot_id")
        payload: dict[str, Any] = {}

        if run_id is not self._UNSET:
            payload["run_id"] = self._normalize_uuid_like(run_id, "run_id")
        if config is not self._UNSET:
            self._validate_required_mapping(config, "config")
            payload["config"] = dict(cast(Mapping[str, Any], config))
        if config_hash is not self._UNSET:
            payload["config_hash"] = self._normalize_text_or_none(
                config_hash, "config_hash"
            )

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
            raise RunConfigSnapshotRepositoryError(
                "Failed to update run config snapshot."
            ) from exc

        return self.get_by_id(identifier)

    def delete(self, snapshot_id: UUID | str) -> bool:
        """Delete a run config snapshot by UUID.

        Args:
            snapshot_id: Snapshot UUID.

        Returns:
            True when a record existed and was deleted, otherwise False.

        Raises:
            TypeError: If snapshot_id has an invalid type.
            ValueError: If snapshot_id is empty or invalid.
            RunConfigSnapshotRepositoryError: If the delete operation fails.
        """

        identifier = self._normalize_uuid_like(snapshot_id, "snapshot_id")

        existing = self.get_by_id(identifier)
        if existing is None:
            return False

        try:
            response = (
                self._client.schema(self._SCHEMA)
                .table(self._TABLE)
                .delete()
                .eq("id", identifier)
                .execute()
            )

            if isinstance(response.data, list):
                return len(response.data) > 0

            return True
        except Exception as exc:
            raise RunConfigSnapshotRepositoryError(
                "Failed to delete run config snapshot."
            ) from exc

    @staticmethod
    def _first_or_none(rows: Any) -> dict[str, Any] | None:
        """Return the first row from a list-like API response or None."""

        if isinstance(rows, list) and rows:
            first_row = rows[0]
            if isinstance(first_row, dict):
                return first_row
        return None

    @staticmethod
    def _validate_required_mapping(value: object, field_name: str) -> None:
        """Validate a required JSON mapping field."""

        if not isinstance(value, Mapping):
            raise TypeError(f"{field_name} must be a mapping.")

    @staticmethod
    def _normalize_text_or_none(value: object, field_name: str) -> str | None:
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
