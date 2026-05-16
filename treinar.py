import math
import os
import random
import time
from typing import Optional

import numpy as np
import pygame

from simulador import (
    ALTURA, ALCANCE_RAY, DIAGONAL, LARGURA, NUM_RAYS, RAIO_AGENTE, RAIO_COLETA, RAIO_ENTREGA, VELOCIDADE,
    Agente, Ambiente, CenarioConfig, criar_populacao, nova_geracao, resumir_geracao, rodar_geracao,
)
from rede_transfer import RedeNeural, carregar_rede_base, salvar_melhor
from metricas import Logger
from gerar_graficos import plotar_run


def _input_size() -> int:
    return 8 + NUM_RAYS


def _setup_rng(seed: Optional[int]):
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
    return random.Random(seed) if seed is not None else random.Random()


def _avaliar_em_cenarios(agentes, ambiente: Ambiente, cfg: CenarioConfig, dt: float = 1.0 / 60.0) -> dict:
    if cfg.cenarios_por_geracao <= 1:
        return rodar_geracao(agentes, ambiente, cfg, dt_fixo=dt)

    fits_acum = np.zeros(len(agentes), dtype=np.float64)
    resumos = []
    for _ in range(cfg.cenarios_por_geracao):
        for a in agentes:
            a.reset_estado()
        ambiente.resetar_cenario()
        for a in agentes:
            a.pos = pygame.Vector2(ambiente.start_pos)
        resumo = rodar_geracao(agentes, ambiente, cfg, dt_fixo=dt)
        resumos.append(resumo)
        for i, a in enumerate(agentes):
            fits_acum[i] += a.fitness

    for i, a in enumerate(agentes):
        a.fitness = fits_acum[i] / cfg.cenarios_por_geracao

    chaves = list(resumos[0].keys())
    chaves_int = {"coletas", "entregas", "colisoes", "mortos"}
    media = {}
    for k in chaves:
        v = float(np.mean([r[k] for r in resumos]))
        media[k] = int(round(v)) if k in chaves_int else v
    media["fit_medio"] = float(np.mean([a.fitness for a in agentes]))
    media["fit_melhor"] = float(np.max([a.fitness for a in agentes]))
    media["fit_pior"] = float(np.min([a.fitness for a in agentes]))
    media["fit_std"] = float(np.std([a.fitness for a in agentes]))
    return media


def treinar(cfg: CenarioConfig, modo: str = "headless"):
    assert modo in ("headless", "visual")
    rng = _setup_rng(cfg.seed)

    rede_base = carregar_rede_base(cfg.checkpoint_entrada, input_size=_input_size())

    ambiente = Ambiente(cfg, rng=rng)
    agentes = criar_populacao(cfg, ambiente, rede_base, input_size=_input_size())

    logger = Logger(cfg.nome)
    logger.salvar_config(cfg)

    melhor_fit_global = -float("inf")

    if modo == "visual":
        _treinar_visual(cfg, ambiente, agentes, logger, melhor_fit_global)
    else:
        _treinar_headless(cfg, ambiente, agentes, logger, melhor_fit_global)

    try:
        plotar_run(logger.dir)
    except Exception as e:
        print(f"[treinar] falhou gerando grafico: {e}")

    logger.copiar_para(cfg.checkpoint_saida)
    return logger.dir


def _treinar_headless(cfg, ambiente, agentes, logger, melhor_fit_global):
    print(f"[treinar] modo headless | {cfg.num_geracoes} geracoes")
    for geracao in range(1, cfg.num_geracoes + 1):
        for a in agentes:
            a.reset_estado()
        if cfg.usa_variacao_posicoes or cfg.usa_obstaculos and not cfg.obstaculos_fixos:
            ambiente.resetar_cenario()
            for a in agentes:
                a.pos = pygame.Vector2(ambiente.start_pos)

        t0 = time.time()
        metricas = _avaliar_em_cenarios(agentes, ambiente, cfg)
        dt_real = time.time() - t0

        melhor_idx = int(np.argmax([a.fitness for a in agentes]))
        if agentes[melhor_idx].fitness > melhor_fit_global:
            melhor_fit_global = agentes[melhor_idx].fitness
            agentes[melhor_idx].brain.salvar(logger.caminho_checkpoint())

        agentes, taxa, forca = nova_geracao(agentes, geracao, cfg, ambiente)
        logger.registrar(geracao, metricas, taxa, forca, dt_real)

    print(f"[treinar] concluido. melhor fitness global: {melhor_fit_global:.1f}")


def _treinar_visual(cfg, ambiente, agentes, logger, melhor_fit_global):
    pygame.init()
    screen = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption(cfg.nome)
    clock = pygame.time.Clock()
    font_sm = pygame.font.SysFont(None, 22)

    historico_fitness, historico_coletas, historico_entregas = [], [], []
    geracao = 1
    tempo = 0.0
    rodando = True

    while rodando and geracao <= cfg.num_geracoes:
        dt = clock.tick(60) / 1000
        tempo += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                rodando = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    tempo = cfg.duracao_geracao + 1
                if event.key == pygame.K_ESCAPE:
                    rodando = False

        ambiente.atualizar(dt)
        for a in agentes:
            a.passo(dt)

        _desenhar_cena(screen, font_sm, cfg, ambiente, agentes, geracao, tempo,
                       historico_fitness, historico_coletas, historico_entregas)
        pygame.display.flip()

        if tempo >= cfg.duracao_geracao or all(a.entregou or a.morto for a in agentes):
            t0 = time.time()
            metricas = resumir_geracao(agentes, cfg)
            dt_real = time.time() - t0

            melhor_idx = int(np.argmax([a.fitness for a in agentes]))
            if agentes[melhor_idx].fitness > melhor_fit_global:
                melhor_fit_global = agentes[melhor_idx].fitness
                agentes[melhor_idx].brain.salvar(logger.caminho_checkpoint())

            historico_fitness.append(metricas["fit_medio"])
            historico_coletas.append(metricas["coletas"])
            historico_entregas.append(metricas["entregas"])

            agentes, taxa, forca = nova_geracao(agentes, geracao, cfg, ambiente)
            logger.registrar(geracao, metricas, taxa, forca, dt_real)

            if cfg.usa_variacao_posicoes or (cfg.usa_obstaculos and not cfg.obstaculos_fixos):
                ambiente.resetar_cenario()
                for a in agentes:
                    a.pos = pygame.Vector2(ambiente.start_pos)

            geracao += 1
            tempo = 0.0

    pygame.quit()
    print(f"[treinar] modo visual encerrado | melhor: {melhor_fit_global:.1f}")


def _desenhar_cena(screen, font, cfg, ambiente, agentes, geracao, tempo,
                   hist_fit, hist_col, hist_ent):
    screen.fill((30, 35, 45))
    for x in range(0, LARGURA, 75):
        pygame.draw.line(screen, (40, 45, 58), (x, 0), (x, ALTURA))
    for y in range(0, ALTURA, 75):
        pygame.draw.line(screen, (40, 45, 58), (0, y), (LARGURA, y))

    for obs in ambiente.obstaculos:
        pygame.draw.rect(screen, (160, 80, 80), obs)
        pygame.draw.rect(screen, (255, 120, 120), obs, 2)

    for robo in ambiente.robos_moveis:
        pygame.draw.circle(screen, (200, 120, 220),
                           (int(robo.pos.x), int(robo.pos.y)), robo.raio)
        pygame.draw.circle(screen, (240, 180, 255),
                           (int(robo.pos.x), int(robo.pos.y)), robo.raio, 2)

    pygame.draw.line(screen, (50, 60, 80), ambiente.start_pos, ambiente.pacote_pos, 1)
    pygame.draw.line(screen, (50, 60, 80), ambiente.pacote_pos, ambiente.entrega_pos, 1)

    pygame.draw.circle(screen, (100, 100, 140), ambiente.start_pos, 8, 2)
    screen.blit(font.render("START", True, (100, 100, 140)),
                (int(ambiente.start_pos.x) + 10, int(ambiente.start_pos.y) - 8))

    pygame.draw.circle(screen, (80, 180, 255), ambiente.pacote_pos, RAIO_COLETA, 2)
    pygame.draw.rect(screen, (100, 180, 255),
                     pygame.Rect(int(ambiente.pacote_pos.x) - 8, int(ambiente.pacote_pos.y) - 8, 16, 16), 2)
    screen.blit(font.render("PACOTE", True, (100, 180, 255)),
                (int(ambiente.pacote_pos.x) + 10, int(ambiente.pacote_pos.y) - 8))

    pygame.draw.circle(screen, (220, 80, 80), ambiente.entrega_pos, RAIO_ENTREGA, 2)
    pygame.draw.circle(screen, (255, 120, 120), ambiente.entrega_pos, 6)
    screen.blit(font.render("ENTREGA", True, (255, 120, 120)),
                (int(ambiente.entrega_pos.x) + 8, int(ambiente.entrega_pos.y) - 8))

    for a in agentes:
        if a.morto:
            cor = (90, 90, 100)
        elif a.entregou:
            cor = (80, 255, 120)
        elif a.carregando:
            cor = (255, 210, 60)
        else:
            cor = (70, 140, 230)
        pygame.draw.circle(screen, cor, (int(a.pos.x), int(a.pos.y)), 8)
        if a.vel.length() > 0.01:
            fim = a.pos + a.vel * 18
            pygame.draw.line(screen, (255, 255, 255), a.pos, fim, 1)

    coletaram = sum(1 for a in agentes if a.coletou)
    entregaram = sum(1 for a in agentes if a.entregou)
    colisoes = sum(a.colisoes for a in agentes)
    fit_medio = sum(a.fitness for a in agentes) / len(agentes)
    fit_melhor = max(a.fitness for a in agentes)

    linhas = [
        f"Geracao: {geracao} / {cfg.num_geracoes}",
        f"Tempo: {tempo:.1f}s / {cfg.duracao_geracao}s",
        f"Coletaram: {coletaram}/{cfg.num_agentes}",
        f"Entregaram: {entregaram}/{cfg.num_agentes}",
        f"Colisoes: {colisoes}",
        f"Fit medio: {fit_medio:.1f}",
        f"Fit melhor: {fit_melhor:.1f}",
        cfg.nome,
        f"Carrega: {cfg.checkpoint_entrada or '-'}",
        f"Salva: {cfg.checkpoint_saida}",
        "SPACE = pular geracao | ESC = sair",
    ]
    hud = pygame.Surface((390, len(linhas) * 22 + 10), pygame.SRCALPHA)
    hud.fill((0, 0, 0, 150))
    screen.blit(hud, (5, 5))
    for i, t in enumerate(linhas):
        screen.blit(font.render(t, True, (230, 230, 230)), (12, 10 + i * 22))

    if hist_fit:
        gw, gh = 230, 130
        gx, gy = LARGURA - gw - 8, 8
        pygame.draw.rect(screen, (20, 25, 35), pygame.Rect(gx, gy, gw, gh))
        pygame.draw.rect(screen, (70, 75, 90), pygame.Rect(gx, gy, gw, gh), 1)
        screen.blit(font.render("Fitness / Coletas / Entregas", True, (160, 160, 180)),
                    (gx + 6, gy + 6))

        def curva(vals, cor, maximo):
            if len(vals) < 2 or maximo <= 0:
                return
            vals = vals[-30:]
            pts = []
            for i, v in enumerate(vals):
                x = gx + 8 + int(i * (gw - 16) / max(len(vals) - 1, 1))
                y = gy + gh - 12 - int((v / maximo) * (gh - 35))
                pts.append((x, y))
            pygame.draw.lines(screen, cor, False, pts, 2)

        max_fit = max(max(hist_fit), 1)
        esc = max_fit / cfg.num_agentes
        curva(hist_fit, (100, 200, 255), max_fit)
        curva([c * esc for c in hist_col], (255, 220, 80), max_fit)
        curva([e * esc for e in hist_ent], (80, 255, 120), max_fit)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("fase", choices=["1", "2", "3", "4", "4_1", "4_2", "5"])
    parser.add_argument("--visual", action="store_true", help="Modo visual com janela pygame")
    parser.add_argument("--geracoes", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    import importlib
    mod = importlib.import_module(f"config_fase{args.fase}")
    cfg: CenarioConfig = mod.CONFIG
    if args.geracoes is not None:
        cfg.num_geracoes = args.geracoes
    if args.seed is not None:
        cfg.seed = args.seed

    treinar(cfg, modo="visual" if args.visual else "headless")
