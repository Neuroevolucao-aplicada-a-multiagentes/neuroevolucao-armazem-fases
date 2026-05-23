import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np


COR_INPUT = "#4a90e2"
COR_HIDDEN = "#e8a87c"
COR_OUTPUT = "#85c88a"
COR_TXT = "#1a1a1a"
COR_LINHA = "#666"
COR_BOX = "#2c3e50"
COR_BOX_BG = "#ecf0f1"
COR_FLECHA = "#34495e"


def desenhar_neuronio(ax, x, y, r, cor, label=None, label_size=8):
    c = patches.Circle((x, y), r, facecolor=cor, edgecolor="#333", linewidth=1.0, zorder=3)
    ax.add_patch(c)
    if label is not None:
        ax.text(x, y, label, ha="center", va="center", fontsize=label_size,
                fontweight="bold", color="white", zorder=4)


def desenhar_conexoes(ax, x1, ys1, x2, ys2, alpha=0.12):
    for y1 in ys1:
        for y2 in ys2:
            ax.plot([x1, x2], [y1, y2], color=COR_LINHA, linewidth=0.5,
                    alpha=alpha, zorder=1)


def figura_arquitetura_rede(out_path: str):
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(-1, 11)
    ax.axis("off")

    titulo = "Arquitetura da rede neural — MLP feedforward de 3 camadas"
    fig.suptitle(titulo, fontsize=14, fontweight="bold", y=0.97)

    input_labels = [
        "dx_alvo (norm)", "dy_alvo (norm)", "dist_alvo (norm)", "carregando (0/1)",
        "dx_entrega (norm)", "dy_entrega (norm)", "|v| (modulo vel)", "tempo_norm",
        "ray_0 (frente)", "ray_1 (+45°)", "ray_2 (+90°)", "ray_3 (+135°)",
        "ray_4 (atras)", "ray_5 (-135°)", "ray_6 (-90°)", "ray_7 (-45°)",
    ]
    n_in = len(input_labels)
    n_h1 = 32
    n_h2 = 16
    n_out = 2

    x_in, x_h1, x_h2, x_out = 1.5, 5.0, 8.5, 12.0
    r_in, r_h, r_out = 0.18, 0.13, 0.30
    y_in = np.linspace(0.5, 10, n_in)
    y_h1 = np.linspace(0.3, 10.2, n_h1)
    y_h2 = np.linspace(0.5, 10, n_h2)
    y_out = [4.3, 6.2]

    desenhar_conexoes(ax, x_in, y_in, x_h1, y_h1, alpha=0.06)
    desenhar_conexoes(ax, x_h1, y_h1, x_h2, y_h2, alpha=0.10)
    desenhar_conexoes(ax, x_h2, y_h2, x_out, y_out, alpha=0.25)

    for y, lbl in zip(y_in, input_labels):
        desenhar_neuronio(ax, x_in, y, r_in, COR_INPUT)
        ax.text(x_in - 0.35, y, lbl, ha="right", va="center",
                fontsize=8, color=COR_TXT)

    for y in y_h1:
        desenhar_neuronio(ax, x_h1, y, r_h, COR_HIDDEN)
    for y in y_h2:
        desenhar_neuronio(ax, x_h2, y, r_h, COR_HIDDEN)

    for y, lbl in zip(y_out, ["vx", "vy"]):
        desenhar_neuronio(ax, x_out, y, r_out, COR_OUTPUT, label=lbl, label_size=11)

    ax.text(x_in, -0.5, "Entrada (16)", ha="center", fontsize=11, fontweight="bold")
    ax.text(x_h1, -0.5, "Oculta 1 (32)\ntanh", ha="center", fontsize=11, fontweight="bold")
    ax.text(x_h2, -0.5, "Oculta 2 (16)\ntanh", ha="center", fontsize=11, fontweight="bold")
    ax.text(x_out, -0.5, "Saida (2)\nlinear", ha="center", fontsize=11, fontweight="bold")

    n_params = 16 * 32 + 32 + 32 * 16 + 16 + 16 * 2 + 2
    info_txt = (
        f"Parametros treinaveis: {n_params:,}\n"
        f"Pesos inicializados via Xavier (sqrt(1/n_in))\n"
        f"Treinamento por neuroevolucao (algoritmo genetico)\n"
        f"Sem backpropagation"
    )
    ax.text(7, 10.6, info_txt, ha="center", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.4", facecolor=COR_BOX_BG,
                      edgecolor=COR_BOX, linewidth=1))

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(out_path, dpi=160, bbox_inches="tight")
    print(f"[ok] {out_path}")
    plt.close(fig)


def _caixa(ax, x, y, w, h, titulo, linhas, cor_borda=COR_BOX, cor_bg="#fafafa"):
    fb = FancyBboxPatch((x, y), w, h,
                        boxstyle="round,pad=0.04,rounding_size=0.15",
                        facecolor=cor_bg, edgecolor=cor_borda, linewidth=1.5)
    ax.add_patch(fb)
    ax.text(x + w / 2, y + h - 0.30, titulo, ha="center", va="top",
            fontsize=11, fontweight="bold", color=cor_borda)
    for i, ln in enumerate(linhas):
        ax.text(x + w / 2, y + h - 0.75 - i * 0.32, ln, ha="center", va="top",
                fontsize=9, color="#222")


def _flecha(ax, x1, y1, x2, y2, label=None, label_above=True, cor=COR_FLECHA, lw=2.0):
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                            arrowstyle="-|>", mutation_scale=22,
                            color=cor, linewidth=lw, zorder=2)
    ax.add_patch(arrow)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if label_above:
            ax.text(mx, my + 0.20, label, ha="center", va="bottom",
                    fontsize=8.5, color=cor, fontweight="bold")
        else:
            ax.text(mx, my - 0.20, label, ha="center", va="top",
                    fontsize=8.5, color=cor, fontweight="bold")


def figura_fluxo_sistema(out_path: str):
    fig, ax = plt.subplots(figsize=(15, 8.5))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 10)
    ax.axis("off")

    fig.suptitle("Fluxo de dados no sistema — neuroevolucao para agentes logisticos",
                 fontsize=14, fontweight="bold", y=0.98)

    _caixa(ax, 0.3, 6.0, 3.5, 3.4, "1. Ambiente (Pygame)", [
        "armazem 900x600 px",
        "obstaculos (prateleiras)",
        "pacotes e ponto de entrega",
        "outros robos moveis",
        "pos. agente: (x, y), v",
    ], cor_borda="#2980b9")

    _caixa(ax, 4.5, 6.0, 3.7, 3.4, "2. Sensores do agente", [
        "vetor relativo ao alvo",
        "vetor ate ponto de entrega",
        "estado (carregando, |v|, t)",
        "8 raycasts (360°, alcance 220 px)",
        "saida: 16 inputs normalizados",
    ], cor_borda="#27ae60")

    _caixa(ax, 8.9, 6.0, 4.2, 3.4, "3. Rede neural (MLP)", [
        "16 -> 32 -> 16 -> 2",
        "tanh nas ocultas",
        "saida linear (vx, vy)",
        "~1.1k parametros",
        "forward em numpy",
    ], cor_borda="#c0392b")

    _caixa(ax, 13.8, 6.0, 3.9, 3.4, "4. Acao no ambiente", [
        "vel = (vx, vy) * VEL_MAX * dt",
        "normaliza se |vel| > 1",
        "checa colisao -> bloqueia",
        "atualiza posicao",
        "verifica coleta/entrega",
    ], cor_borda="#8e44ad")

    _flecha(ax, 3.85, 7.7, 4.45, 7.7, "estado")
    _flecha(ax, 8.25, 7.7, 8.85, 7.7, "input 16d")
    _flecha(ax, 13.15, 7.7, 13.75, 7.7, "(vx, vy)")

    _caixa(ax, 13.8, 1.8, 3.9, 3.3, "5. Avaliacao (fitness)", [
        "+ progresso ao alvo",
        "+ alinhamento de velocidade",
        "+ bonus entrega (e tempo)",
        "- colisao, - parado",
        "fitness do agente",
    ], cor_borda="#e67e22")

    _caixa(ax, 8.0, 1.8, 5.0, 3.3, "6. Algoritmo genetico", [
        "ranking por fitness na geracao",
        "elite -> proxima populacao",
        "crossover por neuronio (coluna)",
        "mutacao gaussiana (rate, strength)",
        "nova geracao de redes",
    ], cor_borda="#16a085")

    _caixa(ax, 0.3, 1.8, 5.5, 3.3, "7. Metricas + logging", [
        "metricas.csv por geracao",
        "checkpoint melhor rede (.npz)",
        "gerar_graficos.py -> resultados.png",
        "transfer learning: rede da fase N",
        "vira ponto de partida da fase N+1",
    ], cor_borda="#34495e")

    _flecha(ax, 15.75, 6.0, 15.75, 5.1, "trajetoria", label_above=False)
    _flecha(ax, 13.8, 3.45, 13.0, 3.45, "fitness por agente")
    _flecha(ax, 8.0, 3.45, 5.8, 3.45, "logs", label_above=False)
    _flecha(ax, 8.0, 4.5, 5.8, 4.5, "checkpoint", label_above=True)

    _flecha(ax, 10.5, 5.1, 10.5, 6.0, "rede nova", label_above=False)

    _flecha(ax, 2.0, 5.1, 2.0, 6.0, label=None)
    ax.text(2.15, 5.55, "novo cenario", fontsize=8.5, color=COR_FLECHA, fontweight="bold")

    info = ("Loop de treinamento: a cada geracao, todos os agentes da populacao executam o\n"
            "fluxo (1->4) em paralelo no mesmo ambiente. O resultado e a fitness (5).\n"
            "O algoritmo genetico (6) gera a proxima populacao. O ciclo se repete por N geracoes.")
    ax.text(9, 0.6, info, ha="center", fontsize=8.5, style="italic", color="#444",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#fefefe",
                      edgecolor="#888", linewidth=0.8))

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(out_path, dpi=160, bbox_inches="tight")
    print(f"[ok] {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs("figuras", exist_ok=True)
    figura_arquitetura_rede("figuras/arquitetura_rede.png")
    figura_fluxo_sistema("figuras/fluxo_sistema.png")
    print("\nFiguras geradas em figuras/")
