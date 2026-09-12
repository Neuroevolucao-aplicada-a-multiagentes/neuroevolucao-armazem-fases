"""Gera um grafico LIMPO para o slide de "Curva de aprendizado" da apresentacao.

Recorta APENAS os 2 paineis mais importantes:
  1. Fitness medio ao longo das geracoes
  2. Taxa de entrega ao longo das geracoes

Diferente do resultados.png (9 paineis, denso), este e otimizado pra
apresentacao: fontes grandes, cores chamativas, layout 2x1, sem grid pesado.

Uso:
    python gerar_grafico_slide.py <pasta_da_run>
    python gerar_grafico_slide.py --melhor   (auto-detecta a melhor run)
"""

import argparse
import glob
import os

import matplotlib.pyplot as plt
import pandas as pd


def _ema(serie, alpha=0.15):
    return serie.ewm(alpha=alpha, adjust=False).mean()


def gerar_para_slide(run_dir: str, out_path: str = None, titulo: str = None):
    csv_path = os.path.join(run_dir, "metricas.csv")
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError(f"CSV vazio em {csv_path}")

    if titulo is None:
        titulo = f"Curva de aprendizado — {os.path.basename(run_dir)}"

    plt.rcParams.update({
        "font.size": 14,
        "axes.titlesize": 16,
        "axes.labelsize": 14,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 12,
        "figure.facecolor": "white",
    })

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))
    fig.suptitle(titulo, fontsize=17, fontweight="bold", y=1.02)

    ax1.plot(df["geracao"], df["fit_medio"],
             color="#a0c4ff", linewidth=1.2, alpha=0.55,
             label="Por geração")
    ax1.plot(df["geracao"], _ema(df["fit_medio"]),
             color="#0353a4", linewidth=3.2,
             label="Tendência (EMA)")
    ax1.set_title("Fitness médio da população", pad=10)
    ax1.set_xlabel("Geração")
    ax1.set_ylabel("Fitness")
    ax1.grid(True, linestyle="--", alpha=0.25)
    ax1.legend(loc="lower right", framealpha=0.9)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    taxa_pct = df["taxa_entrega"] * 100
    ax2.plot(df["geracao"], taxa_pct,
             color="#b6e2a1", linewidth=1.2, alpha=0.55,
             label="Por geração")
    ax2.plot(df["geracao"], _ema(taxa_pct),
             color="#2d6a4f", linewidth=3.2,
             label="Tendência (EMA)")
    ax2.set_title("Taxa de entrega da população", pad=10)
    ax2.set_xlabel("Geração")
    ax2.set_ylabel("Entregas (%)")
    ax2.set_ylim(-3, 105)
    ax2.grid(True, linestyle="--", alpha=0.25)
    ax2.legend(loc="lower right", framealpha=0.9)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    ger0 = int(df["geracao"].iloc[0])
    gerf = int(df["geracao"].iloc[-1])
    fit0 = float(df["fit_medio"].iloc[0])
    fitf = float(_ema(df["fit_medio"]).iloc[-1])
    tx0 = float(taxa_pct.iloc[0])
    txf = float(_ema(taxa_pct).iloc[-1])

    info = (f"Geração {ger0}:  fit médio = {fit0:.0f}  |  entregas = {tx0:.0f}%\n"
            f"Geração {gerf}:  fit médio = {fitf:.0f}  |  entregas = {txf:.0f}%")
    fig.text(0.5, -0.06, info, ha="center", fontsize=12,
             color="#222", style="italic")

    plt.tight_layout()

    if out_path is None:
        os.makedirs("figuras", exist_ok=True)
        out_path = "figuras/slide_curva_aprendizado.png"
    plt.savefig(out_path, dpi=180, bbox_inches="tight",
                facecolor="white")
    print(f"[ok] salvo em {out_path}")
    plt.close(fig)
    return out_path


def melhor_run() -> str:
    """Escolhe a run com mais geracoes E maior taxa de entrega final."""
    candidatos = []
    for d in glob.glob("runs/*/"):
        csv = os.path.join(d, "metricas.csv")
        if not os.path.exists(csv):
            continue
        try:
            df = pd.read_csv(csv)
            if df.empty or len(df) < 30:
                continue
            score = len(df) * float(df["taxa_entrega"].iloc[-1] + 0.01)
            candidatos.append((score, d))
        except Exception:
            continue
    if not candidatos:
        raise FileNotFoundError("Nenhuma run valida em runs/")
    candidatos.sort(reverse=True)
    return candidatos[0][1].rstrip("/").rstrip("\\")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", nargs="?", default=None)
    parser.add_argument("--melhor", action="store_true",
                        help="Auto-detecta a melhor run")
    parser.add_argument("--titulo", default=None)
    parser.add_argument("--saida", default=None,
                        help="Caminho de saida (default: figuras/slide_curva_aprendizado.png)")
    args = parser.parse_args()

    if args.melhor or args.run_dir is None:
        run = melhor_run()
        print(f"[info] usando: {run}")
    else:
        run = args.run_dir

    gerar_para_slide(run, out_path=args.saida, titulo=args.titulo)
