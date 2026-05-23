import os
import random

import matplotlib.pyplot as plt
import matplotlib.patches as mp

from config_fase3 import CONFIG
from simulador import Ambiente, LARGURA, ALTURA


def desenhar(ax, ambiente, idx):
    ax.set_xlim(0, LARGURA)
    ax.set_ylim(ALTURA, 0)
    ax.set_aspect("equal")
    ax.set_facecolor("#1e242d")
    ax.set_title(f"Cenario {idx + 1}", color="#fff", fontsize=10)
    for x in range(0, LARGURA, 75):
        ax.axvline(x, color="#2a313c", linewidth=0.4)
    for y in range(0, ALTURA, 75):
        ax.axhline(y, color="#2a313c", linewidth=0.4)

    for obs in ambiente.obstaculos:
        ax.add_patch(mp.Rectangle((obs.x, obs.y), obs.width, obs.height,
                                  facecolor="#a04040", edgecolor="#ff8080", linewidth=1.2))

    ax.plot([ambiente.start_pos.x, ambiente.pacote_pos.x],
            [ambiente.start_pos.y, ambiente.pacote_pos.y],
            color="#5a6478", linestyle="--", linewidth=1, alpha=0.6)
    ax.plot([ambiente.pacote_pos.x, ambiente.entrega_pos.x],
            [ambiente.pacote_pos.y, ambiente.entrega_pos.y],
            color="#5a6478", linestyle="--", linewidth=1, alpha=0.6)

    ax.add_patch(mp.Circle((ambiente.start_pos.x, ambiente.start_pos.y),
                           10, edgecolor="#9090aa", facecolor="none", linewidth=2))
    ax.text(ambiente.start_pos.x + 12, ambiente.start_pos.y - 12, "S",
            color="#9090aa", fontsize=9, fontweight="bold")

    ax.add_patch(mp.Circle((ambiente.pacote_pos.x, ambiente.pacote_pos.y),
                           14, edgecolor="#60b0ff", facecolor="none", linewidth=2))
    ax.text(ambiente.pacote_pos.x + 14, ambiente.pacote_pos.y - 12, "P",
            color="#60b0ff", fontsize=9, fontweight="bold")

    ax.add_patch(mp.Circle((ambiente.entrega_pos.x, ambiente.entrega_pos.y),
                           18, edgecolor="#ff7878", facecolor="none", linewidth=2))
    ax.text(ambiente.entrega_pos.x + 18, ambiente.entrega_pos.y - 12, "E",
            color="#ff7878", fontsize=9, fontweight="bold")

    ax.set_xticks([])
    ax.set_yticks([])


fig, axes = plt.subplots(2, 3, figsize=(15, 7), facecolor="#101418")
fig.suptitle("Fase 3 - posicoes aleatorias e obstaculos NO CAMINHO",
             color="#fff", fontsize=13, fontweight="bold")

for i, ax in enumerate(axes.flatten()):
    rng = random.Random(100 + i)
    amb = Ambiente(CONFIG, rng=rng)
    desenhar(ax, amb, i)

os.makedirs("figuras", exist_ok=True)
out = "figuras/fase3_cenarios_exemplo.png"
plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(out, dpi=140, facecolor="#101418")
print(f"[ok] {out}")
