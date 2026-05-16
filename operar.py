import argparse
import csv
import datetime
import math
import os
import random
import sys
from typing import List, Optional

import numpy as np
import pygame

from rede_transfer import RedeNeural
from simulador import (
    ALTURA, ALCANCE_RAY, DIAGONAL, LARGURA, NUM_RAYS, RAIO_AGENTE, RAIO_COLETA, RAIO_ENTREGA, VELOCIDADE,
    Ambiente, CenarioConfig, RoboOperacional, rodar_operacao_multiagente,
)


def _checkpoint_default() -> str:
    candidatos = [
        "melhor_rede_fase5.npz",
        "melhor_rede_fase4_2.npz",
        "melhor_rede_fase4_1.npz",
        "melhor_rede_fase4.npz",
        "melhor_rede_fase3.npz",
        "melhor_rede_fase2.npz",
        "melhor_rede_fase1.npz",
    ]
    for c in candidatos:
        if os.path.exists(c):
            return c
    raise FileNotFoundError("Nenhum checkpoint treinado encontrado. Rode treinar.py 1 primeiro.")


def _montar_config_operacao(obstaculos: bool, robos_moveis_scripted: int,
                            seed: Optional[int]) -> CenarioConfig:
    return CenarioConfig(
        nome="Operacao multiagente",
        num_agentes=1,
        usa_variacao_posicoes=True,
        usa_obstaculos=obstaculos,
        num_robos_moveis=robos_moveis_scripted,
        obstaculos_fixos=[
            (570, 285, 70, 120),
            (360, 330, 70, 120),
            (650, 120, 70, 110),
        ] if obstaculos else [],
        seed=seed,
        objetivo_simples=False,
    )


def _executar_headless(brain, num_robos: int, duracao: float,
                        obstaculos: bool, robos_moveis_scripted: int,
                        seed: Optional[int]) -> dict:
    rng = random.Random(seed) if seed is not None else random.Random()
    if seed is not None:
        np.random.seed(seed)
    cfg = _montar_config_operacao(obstaculos, robos_moveis_scripted, seed)
    ambiente = Ambiente(cfg, rng=rng)
    _, metricas = rodar_operacao_multiagente(brain, num_robos, ambiente, duracao=duracao)
    return metricas


def _executar_visual(brain, num_robos: int, duracao: float,
                      obstaculos: bool, robos_moveis_scripted: int,
                      seed: Optional[int]) -> dict:
    rng = random.Random(seed) if seed is not None else random.Random()
    if seed is not None:
        np.random.seed(seed)
    cfg = _montar_config_operacao(obstaculos, robos_moveis_scripted, seed)
    ambiente = Ambiente(cfg, rng=rng)

    pygame.init()
    screen = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption(f"Operacao multiagente | {num_robos} robos")
    clock = pygame.time.Clock()
    font_sm = pygame.font.SysFont(None, 22)

    margem = 60
    robos: List[RoboOperacional] = []
    for i in range(num_robos):
        for _ in range(100):
            p = pygame.Vector2(rng.randint(margem, LARGURA - margem),
                                rng.randint(margem, ALTURA - margem))
            if ambiente._ponto_em_obstaculo(p, margem=20):
                continue
            if all(p.distance_to(r.pos) > 40 for r in robos):
                robos.append(RoboOperacional(i, brain, ambiente, p))
                break

    cores = _gerar_paleta(num_robos)
    tempo = 0.0
    rodando = True

    while rodando and tempo < duracao:
        dt = clock.tick(60) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                rodando = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                rodando = False

        ambiente.atualizar(dt)
        for r in robos:
            r.passo(dt, robos)
        tempo += dt

        _desenhar(screen, font_sm, ambiente, robos, cores, tempo, duracao)
        pygame.display.flip()

    pygame.quit()

    from simulador import _resumir_operacao
    return _resumir_operacao(robos, tempo)


def _gerar_paleta(n: int) -> list:
    base = [
        (70, 140, 230), (255, 130, 60), (80, 220, 100), (200, 80, 200),
        (255, 200, 60), (60, 200, 220), (220, 70, 90), (180, 130, 240),
        (100, 200, 140), (240, 160, 80), (140, 180, 240), (200, 220, 100),
        (240, 100, 160), (90, 200, 200), (200, 130, 130), (130, 130, 230),
    ]
    while len(base) < n:
        base.append((random.randint(80, 240), random.randint(80, 240), random.randint(80, 240)))
    return base[:n]


def _desenhar(screen, font, ambiente, robos, cores, tempo, duracao):
    screen.fill((30, 35, 45))

    for x in range(0, LARGURA, 75):
        pygame.draw.line(screen, (40, 45, 58), (x, 0), (x, ALTURA))
    for y in range(0, ALTURA, 75):
        pygame.draw.line(screen, (40, 45, 58), (0, y), (LARGURA, y))

    for obs in ambiente.obstaculos:
        pygame.draw.rect(screen, (110, 70, 70), obs)
        pygame.draw.rect(screen, (200, 110, 110), obs, 2)

    for rm in ambiente.robos_moveis:
        pygame.draw.circle(screen, (200, 120, 220),
                           (int(rm.pos.x), int(rm.pos.y)), rm.raio)

    for r, cor in zip(robos, cores):
        pygame.draw.circle(screen, cor, (int(r.pacote_pos.x), int(r.pacote_pos.y)),
                            RAIO_COLETA, 1)
        pygame.draw.rect(screen, cor,
                          pygame.Rect(int(r.pacote_pos.x) - 5, int(r.pacote_pos.y) - 5, 10, 10), 1)
        pygame.draw.circle(screen, cor, (int(r.entrega_pos.x), int(r.entrega_pos.y)),
                            RAIO_ENTREGA, 1)
        pygame.draw.circle(screen, cor, (int(r.entrega_pos.x), int(r.entrega_pos.y)), 4)

    for r, cor in zip(robos, cores):
        pygame.draw.circle(screen, cor, (int(r.pos.x), int(r.pos.y)), r.raio)
        if r.carregando:
            pygame.draw.circle(screen, (255, 240, 80),
                               (int(r.pos.x), int(r.pos.y)), 3)
        if r.vel.length() > 0.01:
            fim = r.pos + r.vel * 18
            pygame.draw.line(screen, (240, 240, 240), r.pos, fim, 1)

    total_entregas = sum(r.total_entregas for r in robos)
    col_obs = sum(r.colisoes_obstaculo for r in robos)
    col_robo = sum(r.colisoes_inter_robo for r in robos)
    throughput = total_entregas / max(tempo, 0.001)

    linhas = [
        f"Robos: {len(robos)}",
        f"Tempo: {tempo:.1f}s / {duracao:.0f}s",
        f"Entregas totais: {total_entregas}",
        f"Throughput: {throughput:.2f} entregas/s",
        f"Colisoes c/ obstaculo: {col_obs}",
        f"Colisoes inter-robo: {col_robo}",
        "ESC = sair",
    ]
    hud = pygame.Surface((310, len(linhas) * 22 + 10), pygame.SRCALPHA)
    hud.fill((0, 0, 0, 160))
    screen.blit(hud, (5, 5))
    for i, t in enumerate(linhas):
        screen.blit(font.render(t, True, (230, 230, 230)), (12, 10 + i * 22))


def _salvar_metricas(metricas: dict, nome_extra: str = "") -> str:
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dir_op = os.path.join("runs", f"operacao_{nome_extra}_{ts}")
    os.makedirs(dir_op, exist_ok=True)
    csv_path = os.path.join(dir_op, "operacao.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metrica", "valor"])
        for k, v in metricas.items():
            w.writerow([k, v])
    print(f"[operar] metricas salvas em {csv_path}")
    return dir_op


def main():
    parser = argparse.ArgumentParser(description="Operacao multiagente com rede treinada")
    parser.add_argument("--rede", default=None, help="Caminho do checkpoint .npz")
    parser.add_argument("--robos", type=int, default=5, help="Numero de robos neurais")
    parser.add_argument("--duracao", type=float, default=60.0, help="Duracao em segundos")
    parser.add_argument("--visual", action="store_true", help="Modo visual com janela pygame")
    parser.add_argument("--obstaculos", action="store_true", help="Habilita obstaculos fixos")
    parser.add_argument("--robos-moveis", type=int, default=0,
                        help="Numero de robos moveis SCRIPTED (obstaculos dinamicos)")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    rede_path = args.rede or _checkpoint_default()
    print(f"[operar] carregando rede de: {rede_path}")
    brain = RedeNeural()
    brain.carregar(rede_path)

    if args.visual:
        metricas = _executar_visual(brain, args.robos, args.duracao,
                                     args.obstaculos, args.robos_moveis, args.seed)
    else:
        metricas = _executar_headless(brain, args.robos, args.duracao,
                                       args.obstaculos, args.robos_moveis, args.seed)

    print("\n=== Resultado operacao multiagente ===")
    for k, v in metricas.items():
        if isinstance(v, float):
            print(f"  {k:30s} = {v:.3f}")
        else:
            print(f"  {k:30s} = {v}")

    _salvar_metricas(metricas, nome_extra=f"N{args.robos}")


if __name__ == "__main__":
    main()
