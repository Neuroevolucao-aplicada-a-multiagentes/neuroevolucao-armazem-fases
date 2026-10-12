"""Substituto do TrainingPersistenceService para treinar sem o Supabase.

Mesma interface publica, sem nenhuma chamada de rede. Os artefatos locais da
run (metricas.csv, melhor_rede.npz e graficos) continuam sendo gravados pelo
Logger, entao nada do resultado se perde: so deixa de existir a copia no banco.

Existe para lotes longos, como multi-seed e ablacao. O servico real interrompe
o treino quando nao consegue gravar o checkpoint, entao uma oscilacao de rede
no meio de uma run de varias horas perde a run inteira.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4


def _registro(**campos: Any) -> dict[str, Any]:
    return {"id": str(uuid4()), **campos}


class PersistenciaLocal:
    def start_experiment(self, **campos: Any) -> dict[str, Any]:
        return _registro(**campos)

    def start_run(self, **campos: Any) -> dict[str, Any]:
        return _registro(**campos)

    def save_run_config_snapshot(self, **campos: Any) -> dict[str, Any]:
        return _registro()

    def start_generation(self, **campos: Any) -> dict[str, Any]:
        return _registro(**campos)

    def finish_generation(self, **campos: Any) -> dict[str, Any]:
        return _registro()

    def save_individual(self, **campos: Any) -> dict[str, Any]:
        return _registro()

    def save_checkpoint(self, **campos: Any) -> dict[str, Any]:
        return _registro()

    def update_checkpoint(self, checkpoint_id: UUID | str, **campos: Any) -> dict[str, Any]:
        return {"id": str(checkpoint_id)}

    def complete_run(self, **campos: Any) -> dict[str, Any]:
        return _registro()

    def fail_run(self, **campos: Any) -> dict[str, Any]:
        return _registro()
