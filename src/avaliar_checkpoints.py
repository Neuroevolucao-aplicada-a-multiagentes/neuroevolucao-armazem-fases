"""Avalia redes treinadas no mesmo conjunto fixo de cenarios.

A aptidao registrada durante o treino nao serve para comparar redes: cada
geracao sorteia poucos cenarios novos e a entrega media oscila dezenas de
pontos de uma geracao para outra. Aqui todas as redes enfrentam exatamente os
mesmos cenarios, gerados por sementes fixas e distintas das usadas no treino,
e a comparacao entre duas redes e pareada cenario a cenario.

Ambientes:
    fase5       o armazem da fase 5, com obstaculos e robos moveis
    corredores  a topologia de corredores da fase 6, nunca vista no treino

Uso:
    python src/avaliar_checkpoints.py melhor_rede_fase5.npz "runs/Fase_5_*2026-10-13*/melhor_rede.npz"
    python src/avaliar_checkpoints.py --cenarios 60 --ambientes corredores melhor_rede_fase5.npz

A primeira rede da lista e a referencia das comparacoes pareadas.
"""

from __future__ import annotations

import argparse
import csv
import glob
import math
import os
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AMBIENTES = ("fase5", "corredores")


def _config(ambiente: str):
    if ambiente == "fase5":
        import config_fase5
        cfg = config_fase5.CONFIG
    elif ambiente == "corredores":
        import config_fase6
        cfg = config_fase6.CONFIG
        cfg.layouts_fixos = 0
    else:
        raise ValueError(ambiente)
    cfg.cenarios_por_geracao = 1
    return cfg


def _rotulo(caminho: str) -> str:
    pasta = os.path.dirname(os.path.abspath(caminho))
    config_txt = os.path.join(pasta, "config.txt")
    if os.path.basename(pasta).startswith("Fase_") and os.path.exists(config_txt):
        with open(config_txt, encoding="utf-8") as f:
            for linha in f:
                if linha.startswith("seed ="):
                    return f"semente {linha.split('=', 1)[1].strip()}"
        return os.path.basename(pasta)
    return os.path.splitext(os.path.basename(caminho))[0]


def _avaliar(tarefa: tuple[str, str, int, int]) -> dict:
    """Roda uma rede em n cenarios de um ambiente. Executa num processo proprio."""
    caminho, ambiente, n, semente_base = tarefa
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    from rede_transfer import carregar_rede_base
    from simulador import Agente, Ambiente, rodar_geracao

    cfg = _config(ambiente)
    rede = carregar_rede_base(caminho, input_size=16)
    por_cenario = []
    for k in range(n):
        amb = Ambiente(cfg, rng=random.Random(semente_base + k))
        agente = Agente(rede.copy(), amb)
        agente.reset_estado()
        agente.pos = pygame.Vector2(amb.start_pos)
        rodar_geracao([agente], amb, cfg)
        por_cenario.append({
            "coletou": bool(agente.coletou),
            "entregou": bool(agente.entregou),
            "colisoes": int(agente.colisoes),
            "tempo_entrega": agente.tempo_entrega,
        })
    return {"caminho": caminho, "ambiente": ambiente, "cenarios": por_cenario}


def _wilson(sucessos: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = sucessos / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    margem = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centro - margem), min(1.0, centro + margem)


def _mcnemar_exato(so_ref: int, so_cand: int) -> float:
    """p bilateral do teste exato de McNemar para resultados pareados binarios."""
    discordantes = so_ref + so_cand
    if discordantes == 0:
        return 1.0
    menor = min(so_ref, so_cand)
    cauda = sum(math.comb(discordantes, i) for i in range(menor + 1)) / 2 ** discordantes
    return min(1.0, 2 * cauda)


def _resumo(cenarios: list[dict]) -> dict:
    n = len(cenarios)
    entregas = sum(c["entregou"] for c in cenarios)
    tempos = [c["tempo_entrega"] for c in cenarios if c["entregou"] and c["tempo_entrega"] is not None]
    ic_baixo, ic_alto = _wilson(entregas, n)
    return {
        "n": n,
        "entrega": entregas / n,
        "ic_baixo": ic_baixo,
        "ic_alto": ic_alto,
        "coleta": sum(c["coletou"] for c in cenarios) / n,
        "colisoes_media": sum(c["colisoes"] for c in cenarios) / n,
        "tempo_entrega_medio": (sum(tempos) / len(tempos)) if tempos else None,
    }


def _expandir(padroes: list[str]) -> list[str]:
    caminhos = []
    for padrao in padroes:
        achados = sorted(glob.glob(padrao)) or ([padrao] if os.path.exists(padrao) else [])
        if not achados:
            print(f"[avaliar] AVISO: nada encontrado para {padrao}")
        caminhos.extend(a for a in achados if a not in caminhos)
    return caminhos


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("redes", nargs="+", help="arquivos .npz ou padroes com *")
    parser.add_argument("--cenarios", type=int, default=100)
    parser.add_argument("--ambientes", nargs="+", choices=AMBIENTES, default=list(AMBIENTES))
    parser.add_argument("--semente-base", type=int, default=9000,
                        help="cenario k usa a semente base+k; o treino usa outras sementes")
    parser.add_argument("--processos", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = parser.parse_args()

    redes = _expandir(args.redes)
    if not redes:
        print("[avaliar] ERRO: nenhuma rede para avaliar")
        return 1

    tarefas = [(r, a, args.cenarios, args.semente_base) for a in args.ambientes for r in redes]
    print(f"[avaliar] {len(redes)} redes x {len(args.ambientes)} ambientes x "
          f"{args.cenarios} cenarios, sementes {args.semente_base} a "
          f"{args.semente_base + args.cenarios - 1}")
    with ProcessPoolExecutor(max_workers=args.processos) as pool:
        resultados = list(pool.map(_avaliar, tarefas))

    por_chave = {(r["caminho"], r["ambiente"]): r["cenarios"] for r in resultados}
    referencia = redes[0]
    linhas_csv = []

    for ambiente in args.ambientes:
        print(f"\n=== {ambiente} ===")
        print(f"{'rede':<22} {'entrega':>8} {'IC 95%':>16} {'coleta':>7} {'colisoes':>9} "
              f"{'t. entrega':>10}   vs {_rotulo(referencia)}")
        ref = por_chave[(referencia, ambiente)]
        for rede in redes:
            cenarios = por_chave[(rede, ambiente)]
            r = _resumo(cenarios)
            so_ref = sum(a["entregou"] and not b["entregou"] for a, b in zip(ref, cenarios))
            so_cand = sum(b["entregou"] and not a["entregou"] for a, b in zip(ref, cenarios))
            p = _mcnemar_exato(so_ref, so_cand)
            comparacao = ("referencia" if rede == referencia else
                          f"{(r['entrega'] - _resumo(ref)['entrega']) * 100:+5.1f} pp "
                          f"(so ela {so_cand}, so ref {so_ref}, p={p:.2f})")
            tempo = f"{r['tempo_entrega_medio']:.1f} s" if r["tempo_entrega_medio"] is not None else "-"
            print(f"{_rotulo(rede):<22} {r['entrega'] * 100:7.1f}% "
                  f"[{r['ic_baixo'] * 100:5.1f}, {r['ic_alto'] * 100:5.1f}] "
                  f"{r['coleta'] * 100:6.1f}% {r['colisoes_media']:9.1f} {tempo:>10}   {comparacao}")
            linhas_csv.append({
                "rede": _rotulo(rede), "arquivo": os.path.relpath(rede, _RAIZ),
                "ambiente": ambiente, **r,
                "so_rede_entregou": so_cand, "so_referencia_entregou": so_ref, "p_mcnemar": p,
            })

    pasta = os.path.join(_RAIZ, "runs", "avaliacoes")
    os.makedirs(pasta, exist_ok=True)
    saida = os.path.join(pasta, f"avaliacao_{datetime.now():%Y-%m-%d_%H-%M-%S}.csv")
    with open(saida, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linhas_csv[0].keys()))
        escritor.writeheader()
        escritor.writerows(linhas_csv)
    print(f"\n[avaliar] tabela gravada em {os.path.relpath(saida, _RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
