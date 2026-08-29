import os
import random
import importlib

import matplotlib.pyplot as plt
import matplotlib.patches as mp

from simulador import Ambiente, LARGURA, ALTURA


FASES = ["config_fase3", "config_fase4", "config_fase4_1", "config_fase4_2"]
ROTULOS = ["Fase 3", "Fase 4", "Fase 4.1", "Fase 4.2"]


def desenhar(ax, ambiente, titulo, subtitulo):
    ax.set_xlim(0, LARGURA)
    ax.set_ylim(ALTURA, 0)
    ax.set_aspect("equal")
    ax.set_facecolor("#1e242d")
    ax.set_title(f"{titulo}\n{subtitulo}", color="#fff", fontsize=10, pad=8)

    for x in range(0, LARGURA, 75):
        ax.axvline(x, color="#2a313c", linewidth=0.3)
    for y in range(0, ALTURA, 75):
        ax.axhline(y, color="#2a313c", linewidth=0.3)

    for obs in ambiente.obstaculos:
        ax.add_patch(mp.Rectangle((obs.x, obs.y), obs.width, obs.height,
                                  facecolor="#a04040", edgecolor="#ff8080", linewidth=1.0))

    ax.plot([ambiente.start_pos.x, ambiente.pacote_pos.x],
            [ambiente.start_pos.y, ambiente.pacote_pos.y],
            color="#5a6478", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.plot([ambiente.pacote_pos.x, ambiente.entrega_pos.x],
            [ambiente.pacote_pos.y, ambiente.entrega_pos.y],
            color="#5a6478", linestyle="--", linewidth=0.8, alpha=0.5)

    ax.add_patch(mp.Circle((ambiente.start_pos.x, ambiente.start_pos.y),
                           10, edgecolor="#9090aa", facecolor="none", linewidth=1.8))
    ax.add_patch(mp.Circle((ambiente.pacote_pos.x, ambiente.pacote_pos.y),
                           12, edgecolor="#60b0ff", facecolor="none", linewidth=1.8))
    ax.add_patch(mp.Circle((ambiente.entrega_pos.x, ambiente.entrega_pos.y),
                           16, edgecolor="#ff7878", facecolor="none", linewidth=1.8))

    ax.set_xticks([])
    ax.set_yticks([])


fig, axes = plt.subplots(2, 4, figsize=(18, 7), facecolor="#101418")
fig.suptitle("Curriculo progressivo - fases 3 a 4.2 (2 cenarios por fase)",
             color="#fff", fontsize=13, fontweight="bold")

for col, (mod_name, rotulo) in enumerate(zip(FASES, ROTULOS)):
    mod = importlib.import_module(mod_name)
    cfg = mod.CONFIG
    subt = (f"n_caminho={cfg.num_obstaculos} | livres={cfg.num_obstaculos_extra_livres} "
            f"| offset={cfg.offset_obstaculo_perpendicular}")
    for row in range(2):
        rng = random.Random(200 + row * 10 + col)
        amb = Ambiente(cfg, rng=rng)
        desenhar(axes[row, col], amb, rotulo, subt if row == 0 else "")

os.makedirs("figuras", exist_ok=True)
out = "figuras/curriculo_fases.png"
plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(out, dpi=140, facecolor="#101418")
print(f"[ok] {out}")
