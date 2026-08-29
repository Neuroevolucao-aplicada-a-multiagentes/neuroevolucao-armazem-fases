import argparse
import csv
import datetime
import os
import random
import sys
from typing import List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from rede_transfer import RedeNeural
from simulador import Ambiente, CenarioConfig, rodar_operacao_multiagente
from operar import _checkpoint_default, _montar_config_operacao


NS_PADRAO = [1, 2, 4, 8, 12, 16]
SEEDS_POR_N_PADRAO = 3


def rodar_um(brain, num_robos: int, duracao: float, seed: int,
             obstaculos: bool, robos_moveis_scripted: int) -> dict:
    rng = random.Random(seed)
    np.random.seed(seed)
    cfg = _montar_config_operacao(obstaculos, robos_moveis_scripted, seed)
    ambiente = Ambiente(cfg, rng=rng)
    _, metricas = rodar_operacao_multiagente(brain, num_robos, ambiente, duracao=duracao)
    metricas["seed"] = seed
    return metricas


def executar(rede_path: str, ns: List[int], seeds_por_n: int, duracao: float,
             obstaculos: bool, robos_moveis_scripted: int) -> str:
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dir_exp = os.path.join("runs", f"escalabilidade_{ts}")
    os.makedirs(dir_exp, exist_ok=True)
    csv_path = os.path.join(dir_exp, "escalabilidade.csv")

    brain = RedeNeural()
    brain.carregar(rede_path)
    print(f"[escalabilidade] rede: {rede_path} | duracao: {duracao}s | seeds/N: {seeds_por_n}")

    linhas = []
    for n in ns:
        for s in range(seeds_por_n):
            seed = 1000 * n + s
            m = rodar_um(brain, n, duracao, seed, obstaculos, robos_moveis_scripted)
            print(f"  N={n:2d} seed={seed} | entregas={m['total_entregas']:3d} | "
                  f"throughput={m['throughput_entregas_por_seg']:.2f}/s | "
                  f"col_robo={m['colisoes_inter_robo']:2d}")
            linhas.append(m)

    cols = list(linhas[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for L in linhas:
            w.writerow([L[c] for c in cols])
    print(f"[escalabilidade] csv salvo em {csv_path}")

    plotar(dir_exp)
    return dir_exp


def plotar(dir_exp: str) -> str:
    df = pd.read_csv(os.path.join(dir_exp, "escalabilidade.csv"))
    agreg = df.groupby("num_robos").agg(
        throughput=("throughput_entregas_por_seg", "mean"),
        throughput_std=("throughput_entregas_por_seg", "std"),
        tput_por_robo=("throughput_por_robo", "mean"),
        tput_por_robo_std=("throughput_por_robo", "std"),
        col_inter=("colisoes_inter_robo", "mean"),
        col_inter_std=("colisoes_inter_robo", "std"),
        col_obs=("colisoes_obstaculo", "mean"),
        tempo_ciclo=("tempo_medio_ciclo", "mean"),
        tempo_ciclo_std=("tempo_medio_ciclo", "std"),
    ).reset_index()

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle("Escalabilidade do sistema multiagente", fontsize=14, fontweight="bold")

    ax = axes[0, 0]
    ax.errorbar(agreg["num_robos"], agreg["throughput"],
                 yerr=agreg["throughput_std"], marker="o", color="#0353a4",
                 capsize=4, linewidth=2)
    ax.set_title("Throughput total (entregas/segundo)")
    ax.set_xlabel("Numero de robos")
    ax.set_ylabel("entregas/s")
    ax.grid(True, linestyle="--", alpha=0.4)

    ax = axes[0, 1]
    ax.errorbar(agreg["num_robos"], agreg["tput_por_robo"],
                 yerr=agreg["tput_por_robo_std"], marker="o", color="#1e8a4b",
                 capsize=4, linewidth=2)
    ax.set_title("Throughput por robo (mede saturacao)")
    ax.set_xlabel("Numero de robos")
    ax.set_ylabel("entregas/(s . robo)")
    ax.grid(True, linestyle="--", alpha=0.4)

    ax = axes[1, 0]
    ax.errorbar(agreg["num_robos"], agreg["col_inter"],
                 yerr=agreg["col_inter_std"], marker="o", color="#c1121f",
                 capsize=4, linewidth=2, label="inter-robo")
    ax.plot(agreg["num_robos"], agreg["col_obs"], marker="s",
             linestyle="--", color="#8d99ae", label="com obstaculo")
    ax.set_title("Colisoes")
    ax.set_xlabel("Numero de robos")
    ax.set_ylabel("colisoes")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)

    ax = axes[1, 1]
    ax.errorbar(agreg["num_robos"], agreg["tempo_ciclo"],
                 yerr=agreg["tempo_ciclo_std"], marker="o", color="#7b2cbf",
                 capsize=4, linewidth=2)
    ax.set_title("Tempo medio de ciclo (coleta+entrega)")
    ax.set_xlabel("Numero de robos")
    ax.set_ylabel("segundos")
    ax.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(dir_exp, "escalabilidade.png")
    plt.savefig(out, dpi=130)
    plt.close(fig)
    print(f"[escalabilidade] grafico salvo em {out}")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rede", default=None)
    p.add_argument("--ns", type=int, nargs="+", default=NS_PADRAO,
                    help="Valores de N para testar (ex.: --ns 1 2 4 8)")
    p.add_argument("--seeds", type=int, default=SEEDS_POR_N_PADRAO,
                    help="Quantas repeticoes por valor de N")
    p.add_argument("--duracao", type=float, default=60.0)
    p.add_argument("--obstaculos", action="store_true")
    p.add_argument("--robos-moveis", type=int, default=0)
    args = p.parse_args()

    rede = args.rede or _checkpoint_default()
    executar(rede, args.ns, args.seeds, args.duracao, args.obstaculos, args.robos_moveis)


if __name__ == "__main__":
    main()
