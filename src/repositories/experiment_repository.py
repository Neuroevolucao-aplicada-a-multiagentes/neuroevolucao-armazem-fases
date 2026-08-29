"""Persistence layer for the Experiment entity using Supabase Data API."""

from __future__ import annotations

from typing import Any, Mapping, cast
from uuid import UUID, uuid4

from supabase import Client

from database.connection import get_supabase_client


class ExperimentRepositoryError(RuntimeError):
    """Base error for persistence failures in ExperimentRepository."""


class ExperimentRepository:
    """Repository responsible for persisting Experiment records in Supabase."""

    _SCHEMA = "core"
    _TABLE = "experiment"
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
        name: str,
        description: str | None = None,
        environment: str | None = None,
        status: str = "draft",
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create an Experiment record and return the persisted row.

        Args:
            name: Unique experiment name.
            description: Optional experiment description.
            environment: Optional environment label.
            status: Initial experiment status.
            metadata: Optional metadata payload.

        Returns:
            The created experiment row.

        Raises:
            ExperimentRepositoryError: If the operation fails or the inserted
                row cannot be retrieved.
            ValueError: If name is empty or only whitespace.
        """

        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("name must not be empty or whitespace.")

        experiment_id = str(uuid4())
        payload: dict[str, Any] = {
            "id": experiment_id,
            "name": normalized_name,
            "description": description,
            "environment": environment,
            "status": status,
            "metadata": dict(metadata) if metadata is not None else {},
        }

        try:
            response = (
                self._client.schema(self._SCHEMA)
                .table(self._TABLE)
                .insert(payload)
                .execute()
            )
            created = self._first_or_none(response.data)
            if created is None:
                created = self.get_by_id(experiment_id)
        except ExperimentRepositoryError:
            raise
        except Exception as exc:
            raise ExperimentRepositoryError(
                "Failed to create experiment in Supabase."
            ) from exc

        if created is None:
            raise ExperimentRepositoryError(
                "Experiment was inserted but could not be retrieved afterward."
            )

        return created

    def get_by_id(self, experiment_id: UUID | str) -> dict[str, Any] | None:
        """Fetch one Experiment by its UUID identifier.

        Args:
            experiment_id: Experiment UUID.

        Returns:
            The experiment row when found, otherwise None.

        Raises:
            ExperimentRepositoryError: If the read operation fails.
        """

        identifier = str(experiment_id)

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
            raise ExperimentRepositoryError("Failed to fetch experiment by id.") from exc

        return self._first_or_none(response.data)

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Fetch one Experiment by its unique name.

        Args:
            name: Experiment name.

        Returns:
            The experiment row when found, otherwise None.

        Raises:
            ExperimentRepositoryError: If the read operation fails.
        """

        try:
            response = (
                self._client.schema(self._SCHEMA)
                .table(self._TABLE)
                .select("*")
                .eq("name", name)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise ExperimentRepositoryError("Failed to fetch experiment by name.") from exc

        return self._first_or_none(response.data)

    def list_all(self) -> list[dict[str, Any]]:
        """List all Experiment rows ordered by creation timestamp.

        Returns:
            A list of experiment rows.

        Raises:
            ExperimentRepositoryError: If the read operation fails.
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
            raise ExperimentRepositoryError("Failed to list experiments.") from exc

        rows = response.data or []
        return [row for row in rows if isinstance(row, dict)]

    def update(
        self,
        experiment_id: UUID | str,
        *,
        name: str | object = _UNSET,
        description: str | None | object = _UNSET,
        environment: str | None | object = _UNSET,
        status: str | object = _UNSET,
        metadata: Mapping[str, Any] | None | object = _UNSET,
    ) -> dict[str, Any] | None:
        """Update an Experiment and return the updated row.

        Args:
            experiment_id: Experiment UUID.
            name: Updated name.
            description: Updated description.
            environment: Updated environment.
            status: Updated status.
            metadata: Updated metadata.

        Returns:
            The updated experiment row when found, otherwise None.

        Raises:
            ValueError: If no update fields are provided.
            ValueError: If name is provided but empty or only whitespace.
            ExperimentRepositoryError: If the update operation fails.
        """

        identifier = str(experiment_id)
        payload: dict[str, Any] = {}

        if name is not self._UNSET:
            if not isinstance(name, str):
                raise TypeError("name must be a str when provided.")
            normalized_name = name.strip()
            if not normalized_name:
                raise ValueError("name must not be empty or whitespace.")
            payload["name"] = normalized_name
        if description is not self._UNSET:
            payload["description"] = description
        if environment is not self._UNSET:
            payload["environment"] = environment
        if status is not self._UNSET:
            if not isinstance(status, str):
                raise TypeError("status must be a str when provided.")
            payload["status"] = status
        if metadata is not self._UNSET:
            if metadata is None:
                payload["metadata"] = None
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
            raise ExperimentRepositoryError("Failed to update experiment.") from exc

        return self.get_by_id(identifier)

    def delete(self, experiment_id: UUID | str) -> bool:
        """Delete an Experiment by UUID.

        Args:
            experiment_id: Experiment UUID.

        Returns:
            True when a record existed and was deleted, otherwise False.

        Raises:
            ExperimentRepositoryError: If the delete operation fails.
        """

        try:
            identifier = str(experiment_id)
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
            raise ExperimentRepositoryError("Failed to delete experiment.") from exc

    @staticmethod
    def _first_or_none(rows: Any) -> dict[str, Any] | None:
        """Return the first row from a list-like API response or None."""

        if isinstance(rows, list) and rows:
            first_row = rows[0]
            if isinstance(first_row, dict):
                return first_row
        return None
