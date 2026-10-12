"""Registra no banco um checkpoint treinado antes da persistencia existir.

As fases 1 a 5 foram treinadas em maio, antes da camada de persistencia entrar
na main, e por isso so existem como arquivos .npz. Este script cria para uma
delas o mesmo conjunto de registros que um treino atual criaria: experimento,
run, snapshot da configuracao, as geracoes com suas metricas, o melhor
individuo com o genoma e o checkpoint best. A partir dai o exportador do Godot
le essa fase do banco como qualquer outra.

A procedencia e verificada, nao presumida: o .npz da fase precisa ser identico,
byte a byte, ao melhor_rede.npz da pasta de run indicada, e e do metricas.csv
dessa pasta que saem a aptidao e a geracao do melhor individuo.

Uso:
    python src/registrar_checkpoint.py --fase 5 --run-dir "runs/Fase_5_-_..."
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _md5(caminho: str) -> str:
    with open(caminho, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def _iso_mtime(caminho: str) -> str:
    return datetime.fromtimestamp(os.path.getmtime(caminho), timezone.utc).isoformat()


def _numerico(linha: dict[str, str]) -> dict[str, Any]:
    saida: dict[str, Any] = {}
    for chave, valor in linha.items():
        try:
            numero = float(valor)
            saida[chave] = int(numero) if chave == "geracao" else numero
        except (TypeError, ValueError):
            saida[chave] = valor
    return saida


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--fase", required=True, help="por exemplo 5 ou 4_2")
    parser.add_argument("--run-dir", required=True, help="pasta em runs/ que gerou o checkpoint")
    args = parser.parse_args()

    from rede_transfer import RedeNeural
    from services import TrainingPersistenceService
    from treinar import _derive_phase_code, _genome_json
    from database.connection import get_supabase_client

    cfg = importlib.import_module(f"config_fase{args.fase}").CONFIG
    npz = os.path.join(_RAIZ, cfg.checkpoint_saida)
    run_dir = os.path.abspath(os.path.join(_RAIZ, args.run_dir))
    npz_run = os.path.join(run_dir, "melhor_rede.npz")
    csv_run = os.path.join(run_dir, "metricas.csv")

    for caminho in (npz, npz_run, csv_run):
        if not os.path.exists(caminho):
            print(f"[registrar] ERRO: {caminho} nao existe")
            return 1

    md5 = _md5(npz)
    if _md5(npz_run) != md5:
        print(f"[registrar] ERRO: {cfg.checkpoint_saida} difere do melhor_rede.npz de {args.run_dir}")
        return 1

    fase = _derive_phase_code(cfg)
    ja = (get_supabase_client().schema("core").table("run").select("id,status,metadata")
          .eq("phase_code", fase).eq("status", "completed").execute().data or [])
    if any((r.get("metadata") or {}).get("checkpoint_md5") == md5 for r in ja):
        print(f"[registrar] {fase} com este checkpoint ja esta no banco; nada a fazer")
        return 0

    with open(csv_run, encoding="utf-8") as f:
        linhas = [_numerico(l) for l in csv.DictReader(f)]
    melhor = max(linhas, key=lambda l: l["fit_melhor"])

    rede = RedeNeural()
    rede.carregar(npz)
    genoma = _genome_json(SimpleNamespace(brain=rede))

    metadados = {
        "importado": True,
        "origem": "checkpoint treinado antes da persistencia, registrado a partir do arquivo",
        "run_dir": os.path.relpath(run_dir, _RAIZ),
        "checkpoint_saida": cfg.checkpoint_saida,
        "checkpoint_md5": md5,
        "geracao_do_melhor": melhor["geracao"],
    }

    servico = TrainingPersistenceService()
    run_id = None
    try:
        experimento = servico.start_experiment(
            name=f"{cfg.nome} | {os.path.basename(run_dir)}",
            description="Checkpoint registrado a partir do arquivo de treino",
            environment="pygame",
            status="completed",
            metadata=metadados,
        )
        run = servico.start_run(
            experiment_id=experimento["id"],
            phase_code=fase,
            run_label=os.path.basename(run_dir),
            seed=cfg.seed,
            started_at=_iso_mtime(os.path.join(run_dir, "config.txt")),
            metadata=metadados,
        )
        run_id = str(run["id"])
        servico.save_run_config_snapshot(run_id=run_id, config=cfg)

        id_geracao_melhor = None
        for linha in linhas:
            geracao = servico.start_generation(
                run_id=run_id,
                generation_number=linha["geracao"],
                population_size=cfg.num_agentes,
            )
            servico.finish_generation(generation_id=geracao["id"], metrics=linha)
            if linha is melhor:
                id_geracao_melhor = str(geracao["id"])

        individuo = servico.save_individual(
            generation_id=id_geracao_melhor,
            individual_index=1,
            fitness=float(melhor["fit_melhor"]),
            rank=1,
            is_elite=True,
            genome=genoma,
            metadata={"importado": True},
        )
        servico.save_checkpoint(
            run_id=run_id,
            generation_id=id_geracao_melhor,
            storage_path=cfg.checkpoint_saida,
            checkpoint_type="best",
            individual_id=str(individuo["id"]),
            fitness=float(melhor["fit_melhor"]),
            metrics=melhor,
        )
        servico.complete_run(
            run_id=run_id,
            finished_at=_iso_mtime(csv_run),
            summary_metrics=linhas[-1],
            metadata=metadados,
        )
    except Exception:
        if run_id is not None:
            try:
                servico.fail_run(run_id=run_id, metadata=metadados)
            except Exception:
                pass
        raise

    print(f"[registrar] {fase} registrada: run {run_id}")
    print(f"[registrar] {len(linhas)} geracoes, melhor individuo na geracao "
          f"{melhor['geracao']} com aptidao {melhor['fit_melhor']:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
