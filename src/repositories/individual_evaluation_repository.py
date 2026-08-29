"""Persistence layer for the IndividualEvaluation entity using Supabase Data API."""

from __future__ import annotations

from typing import Any, Mapping, cast
from uuid import UUID, uuid4

from supabase import Client

from database.connection import get_supabase_client


Numeric = int | float


class IndividualEvaluationRepositoryError(RuntimeError):
    """Base error for persistence failures in IndividualEvaluationRepository."""


class IndividualEvaluationRepository:
    """Repository responsible for persisting individual evaluations in Supabase."""

    _SCHEMA = "core"
    _TABLE = "individual_evaluation"
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
        individual_id: UUID | str,
        evaluation_index: int,
        fitness: Numeric,
        success: bool = False,
        scenario_label: str | None = None,
        metrics: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create an individual evaluation record and return the persisted row.

        Args:
            individual_id: Related individual UUID.
            evaluation_index: Sequential evaluation index.
            fitness: Fitness value for the evaluation.
            success: Evaluation success flag.
            scenario_label: Optional scenario label.
            metrics: Optional metrics payload.

        Returns:
            The created evaluation row.

        Raises:
            ValueError: If required values are invalid or constraints are
                violated.
            TypeError: If UUID, numeric, boolean, text, or JSON payloads have an
                invalid type.
            IndividualEvaluationRepositoryError: If the operation fails or the
                inserted row cannot be retrieved.
        """

        normalized_individual_id = self._normalize_uuid_like(individual_id, "individual_id")
        self._validate_required_int(evaluation_index, "evaluation_index", minimum=1)
        self._validate_numeric(fitness, "fitness")
        self._validate_bool(success, "success")
        normalized_scenario_label = self._normalize_text_or_none(
            scenario_label, "scenario_label"
        )
        normalized_metrics = self._normalize_jsonb_mapping(metrics, "metrics")

        payload: dict[str, Any] = {
            "id": str(uuid4()),
            "individual_id": normalized_individual_id,
            "evaluation_index": evaluation_index,
            "scenario_label": normalized_scenario_label,
            "fitness": fitness,
            "success": success,
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
        except IndividualEvaluationRepositoryError:
            raise
        except Exception as exc:
            raise IndividualEvaluationRepositoryError(
                "Failed to create individual evaluation in Supabase."
            ) from exc

        if created is None:
            raise IndividualEvaluationRepositoryError(
                "Individual evaluation was inserted but could not be retrieved afterward."
            )

        return created

    def get_by_id(self, evaluation_id: UUID | str) -> dict[str, Any] | None:
        """Fetch one individual evaluation by its UUID identifier.

        Args:
            evaluation_id: Evaluation UUID.

        Returns:
            The evaluation row when found, otherwise None.

        Raises:
            TypeError: If evaluation_id has an invalid type.
            ValueError: If evaluation_id is empty or invalid.
            IndividualEvaluationRepositoryError: If the read operation fails.
        """

        identifier = self._normalize_uuid_like(evaluation_id, "evaluation_id")

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
            raise IndividualEvaluationRepositoryError(
                "Failed to fetch individual evaluation by id."
            ) from exc

        return self._first_or_none(response.data)

    def list_by_individual(self, individual_id: UUID | str) -> list[dict[str, Any]]:
        """List evaluations associated with an individual.

        Args:
            individual_id: Individual UUID.

        Returns:
            A list of evaluation rows ordered by evaluation index.

        Raises:
            TypeError: If individual_id has an invalid type.
            ValueError: If individual_id is empty or invalid.
            IndividualEvaluationRepositoryError: If the read operation fails.
        """

        identifier = self._normalize_uuid_like(individual_id, "individual_id")

        try:
            response = (
                self._client.schema(self._SCHEMA)
                .table(self._TABLE)
                .select("*")
                .eq("individual_id", identifier)
                .order("evaluation_index", desc=False)
                .execute()
            )
        except Exception as exc:
            raise IndividualEvaluationRepositoryError(
                "Failed to list individual evaluations by individual."
            ) from exc

        rows = response.data or []
        return [row for row in rows if isinstance(row, dict)]

    def list_all(self) -> list[dict[str, Any]]:
        """List all individual evaluations in a deterministic order.

        Returns:
            A list of evaluation rows ordered by individual and evaluation index.

        Raises:
            IndividualEvaluationRepositoryError: If the read operation fails.
        """

        try:
            response = (
                self._client.schema(self._SCHEMA)
                .table(self._TABLE)
                .select("*")
                .order("individual_id", desc=False)
                .order("evaluation_index", desc=False)
                .order("created_at", desc=False)
                .execute()
            )
        except Exception as exc:
            raise IndividualEvaluationRepositoryError(
                "Failed to list individual evaluations."
            ) from exc

        rows = response.data or []
        return [row for row in rows if isinstance(row, dict)]

    def update(
        self,
        evaluation_id: UUID | str,
        *,
        individual_id: UUID | str | object = _UNSET,
        evaluation_index: int | object = _UNSET,
        scenario_label: str | None | object = _UNSET,
        fitness: Numeric | object = _UNSET,
        success: bool | object = _UNSET,
        metrics: Mapping[str, Any] | None | object = _UNSET,
    ) -> dict[str, Any] | None:
        """Update an individual evaluation and return the updated row.

        Args:
            evaluation_id: Evaluation UUID.
            individual_id: Updated individual UUID.
            evaluation_index: Updated evaluation index.
            scenario_label: Updated scenario label.
            fitness: Updated fitness value.
            success: Updated success flag.
            metrics: Updated metrics payload.

        Returns:
            The updated evaluation row when found, otherwise None.

        Raises:
            ValueError: If no update fields are provided.
            TypeError: If a provided field has an invalid type.
            IndividualEvaluationRepositoryError: If the update operation fails.
        """

        identifier = self._normalize_uuid_like(evaluation_id, "evaluation_id")
        payload: dict[str, Any] = {}

        if individual_id is not self._UNSET:
            payload["individual_id"] = self._normalize_uuid_like(individual_id, "individual_id")
        if evaluation_index is not self._UNSET:
            self._validate_required_int(evaluation_index, "evaluation_index", minimum=1)
            payload["evaluation_index"] = evaluation_index
        if scenario_label is not self._UNSET:
            payload["scenario_label"] = self._normalize_text_or_none(
                scenario_label, "scenario_label"
            )
        if fitness is not self._UNSET:
            self._validate_numeric(fitness, "fitness")
            payload["fitness"] = fitness
        if success is not self._UNSET:
            self._validate_bool(success, "success")
            payload["success"] = success
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
        except Exception as exc:
            raise IndividualEvaluationRepositoryError(
                "Failed to update individual evaluation."
            ) from exc

        return self.get_by_id(identifier)

    def delete(self, evaluation_id: UUID | str) -> bool:
        """Delete an individual evaluation by UUID.

        Args:
            evaluation_id: Evaluation UUID.

        Returns:
            True when a record existed and was deleted, otherwise False.

        Raises:
            TypeError: If evaluation_id has an invalid type.
            ValueError: If evaluation_id is empty or invalid.
            IndividualEvaluationRepositoryError: If the delete operation fails.
        """

        identifier = self._normalize_uuid_like(evaluation_id, "evaluation_id")
        existing = self.get_by_id(identifier)
        if existing is None:
            return False

        try:
            self._client.schema(self._SCHEMA).table(self._TABLE).delete().eq("id", identifier).execute()
        except Exception as exc:
            raise IndividualEvaluationRepositoryError(
                "Failed to delete individual evaluation."
            ) from exc

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
    def _validate_required_int(value: object, field_name: str, *, minimum: int | None = None) -> None:
        """Validate a required integer field."""

        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{field_name} must be an int.")
        if minimum is not None and value < minimum:
            raise ValueError(f"{field_name} must be greater than or equal to {minimum}.")

    @staticmethod
    def _validate_numeric(value: object, field_name: str) -> None:
        """Validate a required numeric field."""

        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"{field_name} must be an int or float.")

    @staticmethod
    def _validate_bool(value: object, field_name: str) -> None:
        """Validate a required boolean field."""

        if not isinstance(value, bool):
            raise TypeError(f"{field_name} must be a bool.")

    @staticmethod
    def _normalize_jsonb_mapping(value: object, field_name: str) -> dict[str, Any]:
        """Normalize an optional JSONB mapping field to a dictionary."""

        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise TypeError(f"{field_name} must be a mapping or None when provided.")
        return dict(cast(Mapping[str, Any], value))

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
