"""Application services for training orchestration and persistence."""

from services.persistencia_local import PersistenciaLocal
from services.training_persistence_service import TrainingPersistenceService

__all__ = ["PersistenciaLocal", "TrainingPersistenceService"]
