import pygame
import numpy as np
import random
import math
from rede_transfer import RedeNeural, carregar_rede_base, salvar_melhor

LARGURA = 900
ALTURA = 600
FPS = 60
VELOCIDADE = 200.0
DIAGONAL = math.sqrt(LARGURA**2 + ALTURA**2)

NUM_AGENTES = 30

DURACAO_GERACAO = 20
ELITE = 4
TAXA_MUTACAO = 0.20
FORCA_MUTACAO = 0.30

START_POS = pygame.Vector2(100, 300)
ALVO_POS = pygame.Vector2(700, 300)
ENTREGA_POS = ALVO_POS
RAIO_CHEGADA = 20

CHECKPOINT_ENTRADA = None
CHECKPOINT_SAIDA = "melhor_rede_fase1.npz"


class Agente:
    def __init__(self, rede_base=None, mutar=False):
        self.pos = pygame.Vector2(START_POS)
        self.vel = pygame.Vector2(0, 0)
        self.brain = rede_base.copy() if rede_base is not None else RedeNeural()
        if mutar:
            self.brain.mutate(0.15, 0.20)
        self.fitness = 0.0
        self.chegou = False
        self.dist_anterior = None

    def resetar(self):
        self.pos = pygame.Vector2(START_POS)
        self.vel = pygame.Vector2(0, 0)
        self.fitness = 0.0
        self.chegou = False
        self.dist_anterior = None

    def montar_inputs(self):
        dx = ALVO_POS.x - self.pos.x
        dy = ALVO_POS.y - self.pos.y
        dist = self.pos.distance_to(ALVO_POS)

        return [
            dx / LARGURA,
            dy / ALTURA,
            dist / DIAGONAL,
            0.0,
            dx / LARGURA,
            dy / ALTURA,
            1.0,
            0.0,
            0.0,
            self.vel.length()
        ]

    def mover(self, dt):
        if self.chegou:
            return

        dist_antes = self.pos.distance_to(ALVO_POS)
        output = self.brain.forward(self.montar_inputs())
        self.vel = pygame.Vector2(float(output[0]), float(output[1]))

        if self.vel.length() > 1:
            self.vel = self.vel.normalize()

        if self.vel.length() < 0.05:
            self.fitness -= 0.05

        self.pos += self.vel * VELOCIDADE * dt
        self.pos.x = max(10, min(LARGURA - 10, self.pos.x))
        self.pos.y = max(10, min(ALTURA - 10, self.pos.y))

        dist_depois = self.pos.distance_to(ALVO_POS)
        progresso = dist_antes - dist_depois
        self.fitness += progresso * 10
        self.fitness += 1.0 / (dist_depois + 1)

        if dist_depois <= RAIO_CHEGADA:
            self.chegou = True
            self.fitness += 2000

    def desenhar(self, screen):
        cor = (80, 220, 100) if self.chegou else (70, 140, 230)
        pygame.draw.circle(screen, cor, (int(self.pos.x), int(self.pos.y)), 8)
        if self.vel.length() > 0.01:
            fim = self.pos + self.vel * 20
            pygame.draw.line(screen, (255, 255, 255), self.pos, fim, 1)


def criar_populacao(rede_base=None):
    agentes = []
    for i in range(NUM_AGENTES):
        agentes.append(Agente(rede_base, mutar=(rede_base is not None and i > 0)))
    return agentes


def nova_geracao(agentes, geracao):
    agentes.sort(key=lambda a: a.fitness, reverse=True)
    taxa = max(0.05, TAXA_MUTACAO * (0.97 ** geracao))
    forca = max(0.05, FORCA_MUTACAO * (0.97 ** geracao))

    novos = []
    for a in agentes[:ELITE]:
        novo = Agente()
        novo.brain = a.brain.copy()
        novos.append(novo)

    pool = agentes[:max(NUM_AGENTES // 2, ELITE * 2)]
    while len(novos) < NUM_AGENTES:
        pai1 = random.choice(pool)
        pai2 = random.choice(pool)
        filho = Agente()
        filho.brain = pai1.brain.crossover(pai2.brain)
        filho.brain.mutate(taxa, forca)
        novos.append(filho)

    for a in novos:
        a.resetar()
    return novos


pygame.init()
screen = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Fase 1 — Navegação simples com checkpoint")
clock = pygame.time.Clock()
font_sm = pygame.font.SysFont(None, 22)

rede_base = carregar_rede_base(CHECKPOINT_ENTRADA)
agentes = criar_populacao(rede_base)

geracao = 1
tempo = 0.0
historico_fitness = []

running = True
while running:
    dt = clock.tick(FPS) / 1000
    tempo += dt

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            tempo = DURACAO_GERACAO + 1

    for a in agentes:
        a.mover(dt)

    screen.fill((30, 35, 45))
    for x in range(0, LARGURA, 75):
        pygame.draw.line(screen, (40, 45, 58), (x, 0), (x, ALTURA))
    for y in range(0, ALTURA, 75):
        pygame.draw.line(screen, (40, 45, 58), (0, y), (LARGURA, y))

    pygame.draw.circle(screen, (255, 80, 80), ALVO_POS, RAIO_CHEGADA, 2)
    pygame.draw.circle(screen, (255, 150, 150), ALVO_POS, 6)
    pygame.draw.circle(screen, (100, 100, 140), START_POS, 8, 2)

    for a in agentes:
        a.desenhar(screen)

    chegaram = sum(1 for a in agentes if a.chegou)
    fit_medio = sum(a.fitness for a in agentes) / NUM_AGENTES
    fit_melhor = max(a.fitness for a in agentes)
    taxa_atual = max(0.05, TAXA_MUTACAO * (0.97 ** geracao))

    linhas = [
        f"Geração: {geracao}",
        f"Tempo: {tempo:.1f}s / {DURACAO_GERACAO}s",
        f"Chegaram: {chegaram} / {NUM_AGENTES}",
        f"Fitness médio: {fit_medio:.1f}",
        f"Fitness melhor: {fit_melhor:.1f}",
        f"Taxa mutação: {taxa_atual:.3f}",
        "FASE 1 — rede 10 inputs",
        f"Salva em: {CHECKPOINT_SAIDA}",
        "SPACE = pular geração",
    ]

    hud = pygame.Surface((330, len(linhas) * 22 + 10), pygame.SRCALPHA)
    hud.fill((0, 0, 0, 150))
    screen.blit(hud, (5, 5))
    for i, texto in enumerate(linhas):
        screen.blit(font_sm.render(texto, True, (230, 230, 230)), (12, 10 + i * 22))

    pygame.display.flip()

    if tempo >= DURACAO_GERACAO:
        fit_medio_final = sum(a.fitness for a in agentes) / NUM_AGENTES
        historico_fitness.append(fit_medio_final)
        print(f"Geração {geracao:3d} | Fit médio: {fit_medio_final:8.1f} | Melhor: {max(a.fitness for a in agentes):8.1f} | Chegaram: {chegaram}/{NUM_AGENTES}")

        salvar_melhor(agentes, CHECKPOINT_SAIDA)
        agentes = nova_geracao(agentes, geracao)
        geracao += 1
        tempo = 0.0

pygame.quit()
