"""Application service to orchestrate training persistence repositories."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Mapping
from uuid import UUID

from repositories.checkpoint_repository import CheckpointRepository
from repositories.experiment_repository import ExperimentRepository
from repositories.generation_repository import GenerationRepository
from repositories.individual_evaluation_repository import IndividualEvaluationRepository
from repositories.individual_repository import IndividualRepository
from repositories.run_config_snapshot_repository import RunConfigSnapshotRepository
from repositories.run_repository import RunRepository


Numeric = int | float


class TrainingPersistenceService:
    """Coordinates repository operations for training lifecycle persistence."""

    def __init__(
        self,
        *,
        experiment_repository: ExperimentRepository | None = None,
        run_repository: RunRepository | None = None,
        generation_repository: GenerationRepository | None = None,
        individual_repository: IndividualRepository | None = None,
        run_config_snapshot_repository: RunConfigSnapshotRepository | None = None,
        individual_evaluation_repository: IndividualEvaluationRepository | None = None,
        checkpoint_repository: CheckpointRepository | None = None,
    ) -> None:
        self.experiment_repository = experiment_repository or ExperimentRepository()
        self.run_repository = run_repository or RunRepository()
        self.generation_repository = generation_repository or GenerationRepository()
        self.individual_repository = individual_repository or IndividualRepository()
        self.run_config_snapshot_repository = (
            run_config_snapshot_repository or RunConfigSnapshotRepository()
        )
        # Kept for forward-compatible use when individual-level evaluation
        # events are available in the training flow.
        self.individual_evaluation_repository = (
            individual_evaluation_repository or IndividualEvaluationRepository()
        )
        self.checkpoint_repository = checkpoint_repository or CheckpointRepository()

    def start_experiment(
        self,
        *,
        name: str,
        description: str | None = None,
        environment: str | None = None,
        status: str = "running",
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.experiment_repository.create(
            name=name,
            description=description,
            environment=environment,
            status=status,
            metadata=metadata,
        )

    def start_run(
        self,
        *,
        experiment_id: UUID | str,
        phase_code: str,
        run_label: str | None = None,
        seed: int | None = None,
        status: str = "running",
        started_at: str | None = None,
        finished_at: str | None = None,
        summary_metrics: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.run_repository.create(
            experiment_id=experiment_id,
            phase_code=phase_code,
            run_label=run_label,
            seed=seed,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            summary_metrics=summary_metrics,
            metadata=metadata,
        )

    def save_run_config_snapshot(
        self,
        *,
        run_id: UUID | str,
        config: Mapping[str, Any] | Any,
        config_hash: str | None = None,
    ) -> dict[str, Any]:
        config_payload = self._serialize_config(config)
        return self.run_config_snapshot_repository.create(
            run_id=run_id,
            config=config_payload,
            config_hash=config_hash,
        )

    def start_generation(
        self,
        *,
        run_id: UUID | str,
        generation_number: int,
        population_size: int,
        started_at: str | None = None,
        metrics: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.generation_repository.create(
            run_id=run_id,
            generation_number=generation_number,
            population_size=population_size,
            started_at=started_at,
            metrics=metrics,
        )

    def finish_generation(
        self,
        *,
        generation_id: UUID | str,
        metrics: Mapping[str, Any],
        finished_at: str | None = None,
    ) -> dict[str, Any] | None:
        best_fitness = self._to_optional_number(metrics.get("fit_melhor"))
        average_fitness = self._to_optional_number(metrics.get("fit_medio"))
        worst_fitness = self._to_optional_number(metrics.get("fit_pior"))
        median_fitness = self._to_optional_number(metrics.get("fit_mediana"))

        if median_fitness is None:
            median_fitness = self._to_optional_number(metrics.get("median_fitness"))

        return self.generation_repository.update(
            generation_id,
            best_fitness=best_fitness,
            average_fitness=average_fitness,
            worst_fitness=worst_fitness,
            median_fitness=median_fitness,
            finished_at=finished_at,
            metrics=metrics,
        )

    def save_individual(
        self,
        *,
        generation_id: UUID | str,
        individual_index: int,
        parent_1_id: UUID | str | None = None,
        parent_2_id: UUID | str | None = None,
        fitness: Numeric | None = None,
        rank: int | None = None,
        is_elite: bool = False,
        genome: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.individual_repository.create(
            generation_id=generation_id,
            individual_index=individual_index,
            parent_1_id=parent_1_id,
            parent_2_id=parent_2_id,
            fitness=fitness,
            rank=rank,
            is_elite=is_elite,
            genome=genome,
            metadata=metadata,
        )

    def save_checkpoint(
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
        return self.checkpoint_repository.create(
            run_id=run_id,
            generation_id=generation_id,
            storage_path=storage_path,
            checkpoint_type=checkpoint_type,
            individual_id=individual_id,
            storage_bucket=storage_bucket,
            fitness=fitness,
            metrics=metrics,
        )

    def complete_run(
        self,
        *,
        run_id: UUID | str,
        finished_at: str | None = None,
        summary_metrics: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return self.run_repository.update(
            run_id,
            status="completed",
            finished_at=finished_at,
            summary_metrics=summary_metrics,
            metadata=metadata,
        )

    def fail_run(
        self,
        *,
        run_id: UUID | str,
        finished_at: str | None = None,
        summary_metrics: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return self.run_repository.update(
            run_id,
            status="failed",
            finished_at=finished_at,
            summary_metrics=summary_metrics,
            metadata=metadata,
        )

    def _serialize_config(self, config: Mapping[str, Any] | Any) -> dict[str, Any]:
        if isinstance(config, Mapping):
            raw = dict(config)
        elif is_dataclass(config):
            raw = asdict(config)
        elif hasattr(config, "__dict__"):
            raw = {
                key: value
                for key, value in vars(config).items()
                if not key.startswith("_") and not callable(value)
            }
        else:
            raise TypeError("config must be a mapping or an object with serializable fields.")

        normalized = self._normalize_json_value(raw)
        if not isinstance(normalized, dict):
            raise TypeError("config must be serializable to a JSON object.")
        return normalized

    def _normalize_json_value(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, bool, int, float)):
            return value
        if isinstance(value, Mapping):
            return {str(k): self._normalize_json_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._normalize_json_value(v) for v in value]
        raise TypeError(
            f"Unsupported value type for JSON serialization: {type(value).__name__}."
        )

    @staticmethod
    def _to_optional_number(value: Any) -> Numeric | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return value
