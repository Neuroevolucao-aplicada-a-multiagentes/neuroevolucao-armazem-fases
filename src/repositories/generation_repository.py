"""Persistence layer for the Generation entity using Supabase Data API."""

from __future__ import annotations

from typing import Any, Mapping, cast
from uuid import UUID, uuid4

from supabase import Client

from database.connection import get_supabase_client


Numeric = int | float


class GenerationRepositoryError(RuntimeError):
    """Base error for persistence failures in GenerationRepository."""


class GenerationRepository:
    """Repository responsible for persisting Generation records in Supabase."""

    _SCHEMA = "core"
    _TABLE = "generation"
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
        generation_number: int,
        population_size: int,
        best_fitness: Numeric | None = None,
        average_fitness: Numeric | None = None,
        worst_fitness: Numeric | None = None,
        median_fitness: Numeric | None = None,
        started_at: str | None = None,
        finished_at: str | None = None,
        metrics: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a Generation record and return the persisted row.

        Args:
            run_id: Related run UUID.
            generation_number: Generation sequence number.
            population_size: Population size for the generation.
            best_fitness: Optional best fitness value.
            average_fitness: Optional average fitness value.
            worst_fitness: Optional worst fitness value.
            median_fitness: Optional median fitness value.
            started_at: Optional generation start timestamp.
            finished_at: Optional generation end timestamp.
            metrics: Optional metrics payload.

        Returns:
            The created generation row.

        Raises:
            ValueError: If generation_number or population_size is invalid.
            TypeError: If run_id, numeric fields, timestamps, or JSON payloads
                have an invalid type.
            GenerationRepositoryError: If the operation fails or the inserted
                row cannot be retrieved.
        """

        normalized_run_id = self._normalize_uuid_like(run_id, "run_id")
        self._validate_optional_timestamp(started_at, "started_at")
        self._validate_optional_timestamp(finished_at, "finished_at")
        self._validate_optional_metrics(metrics, "metrics")

        if not isinstance(generation_number, int) or isinstance(generation_number, bool):
            raise TypeError("generation_number must be an int.")
        if generation_number < 1:
            raise ValueError("generation_number must be greater than or equal to 1.")

        if not isinstance(population_size, int) or isinstance(population_size, bool):
            raise TypeError("population_size must be an int.")
        if population_size < 1:
            raise ValueError("population_size must be greater than or equal to 1.")

        self._validate_optional_number(best_fitness, "best_fitness")
        self._validate_optional_number(average_fitness, "average_fitness")
        self._validate_optional_number(worst_fitness, "worst_fitness")
        self._validate_optional_number(median_fitness, "median_fitness")

        payload: dict[str, Any] = {
            "id": str(uuid4()),
            "run_id": normalized_run_id,
            "generation_number": generation_number,
            "population_size": population_size,
            "best_fitness": best_fitness,
            "average_fitness": average_fitness,
            "worst_fitness": worst_fitness,
            "median_fitness": median_fitness,
            "started_at": started_at,
            "finished_at": finished_at,
            "metrics": dict(metrics) if metrics is not None else {},
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
        except GenerationRepositoryError:
            raise
        except Exception as exc:
            raise GenerationRepositoryError("Failed to create generation in Supabase.") from exc

        if created is None:
            raise GenerationRepositoryError(
                "Generation was inserted but could not be retrieved afterward."
            )

        return created

    def get_by_id(self, generation_id: UUID | str) -> dict[str, Any] | None:
        """Fetch one Generation by its UUID identifier.

        Args:
            generation_id: Generation UUID.

        Returns:
            The generation row when found, otherwise None.

        Raises:
            GenerationRepositoryError: If the read operation fails.
        """

        identifier = self._normalize_uuid_like(generation_id, "generation_id")

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
            raise GenerationRepositoryError("Failed to fetch generation by id.") from exc

        return self._first_or_none(response.data)

    def list_by_run(self, run_id: UUID | str) -> list[dict[str, Any]]:
        """List Generation rows associated with a run.

        Args:
            run_id: Run UUID.

        Returns:
            A list of generation rows ordered by generation number.

        Raises:
            GenerationRepositoryError: If the read operation fails.
        """

        try:
            response = (
                self._client.schema(self._SCHEMA)
                .table(self._TABLE)
                .select("*")
                .eq("run_id", self._normalize_uuid_like(run_id, "run_id"))
                .order("generation_number", desc=False)
                .execute()
            )
        except Exception as exc:
            raise GenerationRepositoryError("Failed to list generations by run.") from exc

        rows = response.data or []
        return [row for row in rows if isinstance(row, dict)]

    def list_all(self) -> list[dict[str, Any]]:
        """List all Generation rows ordered by creation timestamp.

        Returns:
            A list of generation rows.

        Raises:
            GenerationRepositoryError: If the read operation fails.
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
            raise GenerationRepositoryError("Failed to list generations.") from exc

        rows = response.data or []
        return [row for row in rows if isinstance(row, dict)]

    def update(
        self,
        generation_id: UUID | str,
        *,
        run_id: UUID | str | object = _UNSET,
        generation_number: int | object = _UNSET,
        population_size: int | object = _UNSET,
        best_fitness: Numeric | None | object = _UNSET,
        average_fitness: Numeric | None | object = _UNSET,
        worst_fitness: Numeric | None | object = _UNSET,
        median_fitness: Numeric | None | object = _UNSET,
        started_at: str | None | object = _UNSET,
        finished_at: str | None | object = _UNSET,
        metrics: Mapping[str, Any] | None | object = _UNSET,
    ) -> dict[str, Any] | None:
        """Update a Generation and return the updated row.

        Args:
            generation_id: Generation UUID.
            run_id: Updated run UUID.
            generation_number: Updated generation number.
            population_size: Updated population size.
            best_fitness: Updated best fitness value.
            average_fitness: Updated average fitness value.
            worst_fitness: Updated worst fitness value.
            median_fitness: Updated median fitness value.
            started_at: Updated start timestamp.
            finished_at: Updated finish timestamp.
            metrics: Updated metrics payload.

        Returns:
            The updated generation row when found, otherwise None.

        Raises:
            ValueError: If no update fields are provided.
            TypeError: If a provided field has an invalid type.
            GenerationRepositoryError: If the update operation fails.
        """

        identifier = self._normalize_uuid_like(generation_id, "generation_id")
        payload: dict[str, Any] = {}

        if run_id is not self._UNSET:
            normalized_run_id = self._normalize_uuid_like(run_id, "run_id")
            payload["run_id"] = normalized_run_id
        if generation_number is not self._UNSET:
            if not isinstance(generation_number, int) or isinstance(generation_number, bool):
                raise TypeError("generation_number must be an int when provided.")
            if generation_number < 1:
                raise ValueError("generation_number must be greater than or equal to 1.")
            payload["generation_number"] = generation_number
        if population_size is not self._UNSET:
            if not isinstance(population_size, int) or isinstance(population_size, bool):
                raise TypeError("population_size must be an int when provided.")
            if population_size < 1:
                raise ValueError("population_size must be greater than or equal to 1.")
            payload["population_size"] = population_size
        if best_fitness is not self._UNSET:
            self._validate_optional_number(best_fitness, "best_fitness")
            payload["best_fitness"] = best_fitness
        if average_fitness is not self._UNSET:
            self._validate_optional_number(average_fitness, "average_fitness")
            payload["average_fitness"] = average_fitness
        if worst_fitness is not self._UNSET:
            self._validate_optional_number(worst_fitness, "worst_fitness")
            payload["worst_fitness"] = worst_fitness
        if median_fitness is not self._UNSET:
            self._validate_optional_number(median_fitness, "median_fitness")
            payload["median_fitness"] = median_fitness
        if started_at is not self._UNSET:
            self._validate_optional_timestamp(started_at, "started_at")
            payload["started_at"] = started_at
        if finished_at is not self._UNSET:
            self._validate_optional_timestamp(finished_at, "finished_at")
            payload["finished_at"] = finished_at
        if metrics is not self._UNSET:
            if metrics is None:
                payload["metrics"] = {}
            else:
                self._validate_optional_metrics(metrics, "metrics")
                payload["metrics"] = dict(cast(Mapping[str, Any], metrics))

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
            raise GenerationRepositoryError("Failed to update generation.") from exc

        return self.get_by_id(identifier)

    def delete(self, generation_id: UUID | str) -> bool:
        """Delete a Generation by UUID.

        Args:
            generation_id: Generation UUID.

        Returns:
            True when a record existed and was deleted, otherwise False.

        Raises:
            GenerationRepositoryError: If the delete operation fails.
        """

        try:
            identifier = self._normalize_uuid_like(generation_id, "generation_id")
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
            raise GenerationRepositoryError("Failed to delete generation.") from exc

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
    def _validate_optional_timestamp(value: object, field_name: str) -> None:
        """Validate an optional timestamp field."""

        if value is None:
            return
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a str or None when provided.")
        if not value.strip():
            raise ValueError(f"{field_name} must not be empty or whitespace.")

    @staticmethod
    def _validate_optional_metrics(value: object, field_name: str) -> None:
        """Validate an optional JSON mapping field."""

        if value is None:
            return
        if not isinstance(value, Mapping):
            raise TypeError(f"{field_name} must be a mapping or None when provided.")

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
