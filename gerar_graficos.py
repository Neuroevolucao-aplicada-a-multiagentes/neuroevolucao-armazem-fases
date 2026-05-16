import argparse
import glob
import os
import sys

import matplotlib.pyplot as plt
import pandas as pd


PAINEIS = [
    ("fit_medio", "Fitness medio", "fitness"),
    ("fit_melhor", "Fitness melhor", "fitness"),
    ("taxa_coleta", "Taxa de coleta", "proporcao"),
    ("taxa_entrega", "Taxa de entrega", "proporcao"),
    ("colisoes", "Colisoes (total da geracao)", "qtd"),
    ("melhor_tempo", "Melhor tempo de entrega (s)", "segundos"),
    ("tempo_medio_entrega", "Tempo medio de entrega (s)", "segundos"),
    ("distancia_media_entrega", "Distancia media percorrida", "px"),
    ("fit_std", "Desvio-padrao do fitness", "fitness"),
]


def _ema(serie: pd.Series, alpha: float = 0.2) -> pd.Series:
    return serie.ewm(alpha=alpha, adjust=False).mean()


def plotar_run(run_dir: str, mostrar: bool = False) -> str:
    csv_path = os.path.join(run_dir, "metricas.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"metricas.csv nao encontrado em {run_dir}")

    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError(f"metricas.csv esta vazio em {run_dir}")

    fig, axes = plt.subplots(3, 3, figsize=(15, 10))
    fig.suptitle(f"Resultados — {os.path.basename(run_dir)}", fontsize=14, fontweight="bold")

    for ax, (coluna, titulo, ylabel) in zip(axes.flatten(), PAINEIS):
        if coluna not in df.columns:
            ax.set_visible(False)
            continue
        ax.plot(df["geracao"], df[coluna], color="#a0c4ff", linewidth=1.0,
                alpha=0.6, label="bruto")
        ax.plot(df["geracao"], _ema(df[coluna]), color="#0353a4", linewidth=2.0,
                label="EMA")
        ax.set_title(titulo, fontsize=11)
        ax.set_xlabel("Geracao")
        ax.set_ylabel(ylabel)
        ax.grid(True, linestyle="--", alpha=0.3)
        ax.legend(loc="best", fontsize=8)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(run_dir, "resultados.png")
    plt.savefig(out, dpi=130)
    print(f"[graficos] salvo em {out}")
    if mostrar:
        plt.show()
    plt.close(fig)
    return out


def plotar_comparacao(raiz_runs: str, mostrar: bool = False) -> str:
    runs = sorted(glob.glob(os.path.join(raiz_runs, "*")))
    runs = [r for r in runs if os.path.isfile(os.path.join(r, "metricas.csv"))]
    if not runs:
        raise FileNotFoundError(f"nenhuma run encontrada em {raiz_runs}")

    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    fig.suptitle("Comparativo entre runs", fontsize=14, fontweight="bold")
    metricas_comparar = [
        ("fit_medio", "Fitness medio"),
        ("taxa_entrega", "Taxa de entrega"),
        ("colisoes", "Colisoes"),
        ("melhor_tempo", "Melhor tempo (s)"),
    ]
    for ax, (coluna, titulo) in zip(axes.flatten(), metricas_comparar):
        for run in runs:
            df = pd.read_csv(os.path.join(run, "metricas.csv"))
            if coluna not in df.columns or df.empty:
                continue
            ax.plot(df["geracao"], _ema(df[coluna]), label=os.path.basename(run), linewidth=1.5)
        ax.set_title(titulo)
        ax.set_xlabel("Geracao")
        ax.grid(True, linestyle="--", alpha=0.3)
        ax.legend(fontsize=7, loc="best")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(raiz_runs, "comparativo.png")
    plt.savefig(out, dpi=130)
    print(f"[graficos] comparativo salvo em {out}")
    if mostrar:
        plt.show()
    plt.close(fig)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", nargs="?", default=None,
                        help="Pasta da run (ex.: runs/Fase_1_..._2026-...)")
    parser.add_argument("--ultima", action="store_true", help="Usar a run mais recente em runs/")
    parser.add_argument("--comparar", metavar="RAIZ", help="Gerar comparativo de todas as runs em RAIZ")
    parser.add_argument("--mostrar", action="store_true", help="Abrir janela ao gerar")
    args = parser.parse_args()

    if args.comparar:
        plotar_comparacao(args.comparar, mostrar=args.mostrar)
        return

    run_dir = args.run_dir
    if args.ultima or run_dir is None:
        candidatas = sorted(glob.glob("runs/*"), key=os.path.getmtime)
        if not candidatas:
            print("Nenhuma run encontrada em runs/.")
            sys.exit(1)
        run_dir = candidatas[-1]
        print(f"[graficos] usando a run mais recente: {run_dir}")

    plotar_run(run_dir, mostrar=args.mostrar)


if __name__ == "__main__":
    main()
