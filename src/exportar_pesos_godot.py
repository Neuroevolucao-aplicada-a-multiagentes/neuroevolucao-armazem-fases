"""Exporta do Supabase os pesos do melhor individuo de uma fase para o Godot.

Roda na maquina de treino, antes da apresentacao, e nao dentro do jogo. Assim
a chave service_role nunca entra no executavel do Godot e a demonstracao nao
depende de rede: o Godot le apenas o JSON gerado aqui.

Caminho dos dados no banco:
    core.run (phase_code, status completed)
      -> core.checkpoint (checkpoint_type best)
        -> core.individual.genome

Uso:
    python src/exportar_pesos_godot.py --fase 5
    python src/exportar_pesos_godot.py --run <uuid>
    python src/exportar_pesos_godot.py --fase 5 --saida caminho/arquivo.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from typing import Any

import numpy as np

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ASSETS_GODOT = os.path.join(os.path.dirname(_RAIZ), "godot-3d", "assets")

# Entrada e saida fazem parte do contrato do ambiente; as camadas ocultas nao.
ENTRADAS = 16
SAIDAS = 2


class ErroExportacao(RuntimeError):
    pass


def codigo_da_fase(fase: str) -> str:
    return "fase_" + fase.replace(".", "_")


def _meta_como_lista(meta: Any) -> list[int]:
    if isinstance(meta, dict):
        chaves = ("input_size", "hidden_1", "hidden_2", "output_size")
        if any(k not in meta for k in chaves):
            raise ErroExportacao(f"meta incompleta: {meta}")
        return [int(meta[k]) for k in chaves]
    if isinstance(meta, (list, tuple)) and len(meta) == 4:
        return [int(v) for v in meta]
    raise ErroExportacao(f"meta em formato desconhecido: {meta!r}")


def genoma_para_godot(genoma: dict[str, Any], origem: dict[str, Any]) -> dict[str, Any]:
    """Valida o genoma gravado no banco e converte para o formato do Godot.

    O Godot le apenas w1..b3; meta e origem viajam junto para rastreabilidade.
    """
    faltando = [k for k in ("meta", "w1", "w2", "w3", "b1", "b2", "b3") if k not in genoma]
    if faltando:
        raise ErroExportacao(f"genoma sem as chaves {faltando}")

    entradas, oculta_1, oculta_2, saidas = _meta_como_lista(genoma["meta"])
    if entradas != ENTRADAS or saidas != SAIDAS:
        raise ErroExportacao(
            f"rede {entradas}->{saidas} viola o contrato {ENTRADAS}->{SAIDAS}")

    formas = {
        "w1": (entradas, oculta_1), "b1": (oculta_1,),
        "w2": (oculta_1, oculta_2), "b2": (oculta_2,),
        "w3": (oculta_2, saidas), "b3": (saidas,),
    }
    saida: dict[str, Any] = {"meta": [entradas, oculta_1, oculta_2, saidas]}
    for nome, forma in formas.items():
        matriz = np.asarray(genoma[nome], dtype=np.float64)
        if matriz.shape != forma:
            raise ErroExportacao(f"{nome} tem forma {matriz.shape}, esperado {forma}")
        if not np.all(np.isfinite(matriz)):
            raise ErroExportacao(f"{nome} contem NaN ou infinito")
        saida[nome] = matriz.tolist()

    saida["origem"] = origem
    return saida


def _uma_linha(resposta: Any) -> dict[str, Any] | None:
    linhas = resposta.data or []
    return linhas[0] if linhas else None


def buscar_genoma(cliente: Any, *, fase: str | None = None,
                  run_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Localiza o melhor individuo da run e devolve (genoma, origem)."""
    core = cliente.schema("core")

    if run_id is not None:
        run = _uma_linha(core.table("run").select("*").eq("id", run_id).limit(1).execute())
        if run is None:
            raise ErroExportacao(f"run {run_id} nao existe no banco")
    else:
        codigo = codigo_da_fase(fase)
        runs = (core.table("run").select("id,phase_code,run_label,status,started_at")
                .eq("phase_code", codigo).order("started_at", desc=True).execute().data or [])
        concluidas = [r for r in runs if r.get("status") == "completed"]
        if not concluidas:
            estados = ", ".join(sorted({str(r.get("status")) for r in runs})) or "nenhuma run"
            raise ErroExportacao(
                f"nenhuma run concluida da {codigo} no banco (encontrado: {estados})")
        run = concluidas[0]
        if len(concluidas) > 1:
            print(f"[exportar] {len(concluidas)} runs concluidas da {codigo}; usando a mais recente.")
            print("[exportar] para fixar outra, use --run com um destes ids:")
            for r in concluidas:
                print(f"    {r['id']}  {str(r.get('started_at'))[:16]}  {r.get('run_label')}")

    checkpoints = (core.table("checkpoint").select("*").eq("run_id", run["id"])
                   .eq("checkpoint_type", "best").execute().data or [])
    if not checkpoints:
        raise ErroExportacao(f"run {run['id']} nao tem checkpoint best")
    checkpoint = max(checkpoints, key=lambda c: c.get("fitness") or -math.inf)
    if not checkpoint.get("individual_id"):
        raise ErroExportacao(f"checkpoint {checkpoint['id']} nao aponta para um individuo")

    individuo = _uma_linha(core.table("individual").select("id,genome,fitness")
                           .eq("id", checkpoint["individual_id"]).limit(1).execute())
    if individuo is None or not individuo.get("genome"):
        raise ErroExportacao(
            f"individuo {checkpoint['individual_id']} sem genoma gravado")

    origem = {
        "fase": run.get("phase_code"),
        "run_id": run["id"],
        "run_label": run.get("run_label"),
        "checkpoint_id": checkpoint["id"],
        "individual_id": individuo["id"],
        "fitness": individuo.get("fitness"),
        "exportado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return individuo["genome"], origem


def conferir_contra_npz(rede: dict[str, Any], caminho_npz: str) -> float | None:
    """Maior desvio absoluto entre os pesos exportados e o checkpoint local."""
    if not os.path.exists(caminho_npz):
        return None
    local = np.load(caminho_npz)
    return max(float(np.abs(np.asarray(rede[k]) - local[k]).max())
               for k in ("w1", "w2", "w3", "b1", "b2", "b3"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    alvo = parser.add_mutually_exclusive_group(required=True)
    alvo.add_argument("--fase", help="fase do curriculo, por exemplo 5 ou 4_2")
    alvo.add_argument("--run", help="id de uma run especifica")
    parser.add_argument("--saida", help="arquivo JSON de destino")
    args = parser.parse_args()

    from database.connection import get_supabase_client

    try:
        genoma, origem = buscar_genoma(get_supabase_client(), fase=args.fase, run_id=args.run)
        rede = genoma_para_godot(genoma, origem)
    except ErroExportacao as e:
        print(f"[exportar] ERRO: {e}")
        return 1

    sufixo = (origem["fase"] or "").replace("fase_", "")
    destino = args.saida
    if destino is None:
        if not os.path.isdir(_ASSETS_GODOT):
            print(f"[exportar] ERRO: {_ASSETS_GODOT} nao existe; informe --saida")
            return 1
        destino = os.path.join(_ASSETS_GODOT, f"melhor_rede_fase{sufixo}.json")

    with open(destino, "w", encoding="utf-8") as f:
        json.dump(rede, f)

    print(f"[exportar] {origem['fase']} | run {origem['run_label']}")
    print(f"[exportar] fitness {origem['fitness']} | individuo {origem['individual_id']}")
    print(f"[exportar] gravado em {destino}")

    desvio = conferir_contra_npz(rede, os.path.join(_RAIZ, f"melhor_rede_fase{sufixo}.npz"))
    if desvio is None:
        print("[exportar] sem checkpoint local para conferir")
    elif desvio == 0.0:
        print("[exportar] identico ao checkpoint local da fase")
    else:
        print(f"[exportar] ATENCAO: difere do checkpoint local (desvio max {desvio:.3e}).")
        print("[exportar] Rode o teste de paridade do Godot antes de apresentar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
