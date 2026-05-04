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
DURACAO_GERACAO = 35
ELITE = 4
TAXA_MUTACAO = 0.25
FORCA_MUTACAO = 0.35

START_POS = pygame.Vector2(100, 300)
RAIO_COLETA = 20
RAIO_ENTREGA = 35

CHECKPOINT_ENTRADA = 'melhor_rede_fase3.npz'
CHECKPOINT_SAIDA = 'melhor_rede_fase4.npz'

FASE_NOME = 'Fase 4 — 3 obstáculos com checkpoint'
USA_VARIACAO = False
USA_OBSTACULOS = True

PACOTE_FIXO = pygame.Vector2(500, 200)
ENTREGA_FIXA = pygame.Vector2(750, 450)

OBSTACULOS = [pygame.Rect(570, 285, 70, 120), pygame.Rect(360, 330, 70, 120), pygame.Rect(650, 120, 70, 110)]


def gerar_posicoes():
    if not USA_VARIACAO:
        return pygame.Vector2(PACOTE_FIXO), pygame.Vector2(ENTREGA_FIXA)

    pacote = pygame.Vector2(
        random.randint(450, 550),
        random.randint(160, 240)
    )
    entrega = pygame.Vector2(
        random.randint(700, 800),
        random.randint(400, 500)
    )
    return pacote, entrega


PACOTE_POS, ENTREGA_POS = gerar_posicoes()


class Agente:
    def __init__(self, rede_base=None, mutar=False):
        self.pos = pygame.Vector2(START_POS)
        self.vel = pygame.Vector2(0, 0)
        self.brain = rede_base.copy() if rede_base is not None else RedeNeural()

        if mutar:
            self.brain.mutate(rate=0.15, strength=0.20)

        self.fitness = 0.0
        self.carregando = False
        self.coletou = False
        self.entregou = False

        self.dist_anterior = None
        self.colisoes = 0
        self.em_colisao = False

        self.tempo_vivo = 0.0
        self.tempo_entrega = None
        self.melhor_dist_alvo = None
        self.distancia_percorrida = 0.0

    def resetar(self):
        self.pos = pygame.Vector2(START_POS)
        self.vel = pygame.Vector2(0, 0)

        self.fitness = 0.0
        self.carregando = False
        self.coletou = False
        self.entregou = False

        self.dist_anterior = None
        self.colisoes = 0
        self.em_colisao = False

        self.tempo_vivo = 0.0
        self.tempo_entrega = None
        self.melhor_dist_alvo = None
        self.distancia_percorrida = 0.0

    def alvo_atual(self):
        return ENTREGA_POS if self.carregando else PACOTE_POS

    def ponto_mais_proximo_obstaculo(self):
        if not USA_OBSTACULOS or len(OBSTACULOS) == 0:
            return pygame.Vector2(self.pos.x + DIAGONAL, self.pos.y)

        menor_dist = float("inf")
        ponto_mais_proximo = pygame.Vector2(0, 0)

        for obstaculo in OBSTACULOS:
            px = max(obstaculo.left, min(self.pos.x, obstaculo.right))
            py = max(obstaculo.top, min(self.pos.y, obstaculo.bottom))
            ponto = pygame.Vector2(px, py)
            dist = self.pos.distance_to(ponto)

            if dist < menor_dist:
                menor_dist = dist
                ponto_mais_proximo = ponto

        return ponto_mais_proximo

    def colidiu_obstaculo(self, nova_pos):
        if not USA_OBSTACULOS:
            return False

        rect = pygame.Rect(int(nova_pos.x - 8), int(nova_pos.y - 8), 16, 16)

        for obstaculo in OBSTACULOS:
            if rect.colliderect(obstaculo):
                return True

        return False

    def montar_inputs(self, alvo):
        dx = alvo.x - self.pos.x
        dy = alvo.y - self.pos.y
        dist = self.pos.distance_to(alvo)

        dx_entrega = ENTREGA_POS.x - self.pos.x
        dy_entrega = ENTREGA_POS.y - self.pos.y

        ponto_obst = self.ponto_mais_proximo_obstaculo()
        dx_obst = ponto_obst.x - self.pos.x
        dy_obst = ponto_obst.y - self.pos.y
        dist_obst = self.pos.distance_to(ponto_obst)

        return [
            dx / LARGURA,
            dy / ALTURA,
            dist / DIAGONAL,
            1.0 if self.carregando else 0.0,
            dx_entrega / LARGURA,
            dy_entrega / ALTURA,
            dist_obst / DIAGONAL,
            dx_obst / LARGURA,
            dy_obst / ALTURA,
            self.vel.length()
        ], dist

    def mover(self, dt):
        if self.entregou:
            return

        self.tempo_vivo += dt
        alvo = self.alvo_atual()
        inputs, dist = self.montar_inputs(alvo)

        output = self.brain.forward(inputs)
        nova_vel = pygame.Vector2(float(output[0]), float(output[1]))

        if nova_vel.length() > 1:
            nova_vel = nova_vel.normalize()

        self.vel = nova_vel
        deslocamento = self.vel * VELOCIDADE * dt

        colidiu = False

        nova_pos_x = pygame.Vector2(self.pos.x + deslocamento.x, self.pos.y)
        nova_pos_x.x = max(10, min(LARGURA - 10, nova_pos_x.x))

        if self.colidiu_obstaculo(nova_pos_x):
            colidiu = True
        else:
            self.pos.x = nova_pos_x.x

        nova_pos_y = pygame.Vector2(self.pos.x, self.pos.y + deslocamento.y)
        nova_pos_y.y = max(10, min(ALTURA - 10, nova_pos_y.y))

        if self.colidiu_obstaculo(nova_pos_y):
            colidiu = True
        else:
            self.pos.y = nova_pos_y.y

        if not colidiu:
            self.distancia_percorrida += deslocamento.length()

        if colidiu and not self.em_colisao:
            self.colisoes += 1
            self.fitness -= 220
            self.em_colisao = True

        if not colidiu:
            self.em_colisao = False

        dist_nova = self.pos.distance_to(alvo)

        if self.melhor_dist_alvo is None:
            self.melhor_dist_alvo = dist_nova

        if dist_nova < self.melhor_dist_alvo:
            ganho = self.melhor_dist_alvo - dist_nova
            self.fitness += ganho * 12
            self.melhor_dist_alvo = dist_nova

        if self.vel.length() < 0.05:
            self.fitness -= 0.03

        if self.carregando:
            self.fitness += 0.05

        if not self.carregando and not self.coletou:
            if self.pos.distance_to(PACOTE_POS) <= RAIO_COLETA:
                self.carregando = True
                self.coletou = True
                self.fitness += 700
                self.dist_anterior = None
                self.melhor_dist_alvo = None

        elif self.carregando:
            if self.pos.distance_to(ENTREGA_POS) <= RAIO_ENTREGA:
                self.carregando = False
                self.entregou = True
                self.tempo_entrega = self.tempo_vivo

                bonus_tempo = max(0, DURACAO_GERACAO - self.tempo_vivo) * 50
                penalidade_rota = self.distancia_percorrida * 0.02

                self.fitness += 2500 + bonus_tempo
                self.fitness -= penalidade_rota

                self.dist_anterior = None
                self.melhor_dist_alvo = None

        if self.colisoes > 0:
            self.fitness -= self.colisoes * 0.2

    def desenhar(self, screen):
        if self.entregou:
            cor = (80, 255, 120)
        elif self.carregando:
            cor = (255, 210, 60)
        else:
            cor = (70, 140, 230)

        pygame.draw.circle(screen, cor, (int(self.pos.x), int(self.pos.y)), 8)

        if self.vel.length() > 0.01:
            fim = self.pos + self.vel * 18
            pygame.draw.line(screen, (255, 255, 255), self.pos, fim, 1)


def criar_populacao(rede_base=None):
    agentes = []
    for i in range(NUM_AGENTES):
        agente = Agente(rede_base, mutar=(rede_base is not None and i > 0))
        agentes.append(agente)
    return agentes


def nova_geracao(agentes, geracao):
    agentes.sort(
        key=lambda a: (
            a.entregou,
            a.coletou,
            -a.colisoes,
            -a.tempo_entrega if a.tempo_entrega is not None else -999,
            a.fitness
        ),
        reverse=True
    )

    taxa = max(0.05, TAXA_MUTACAO * (0.97 ** geracao))
    forca = max(0.08, FORCA_MUTACAO * (0.97 ** geracao))

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
pygame.display.set_caption(FASE_NOME)
clock = pygame.time.Clock()
font_sm = pygame.font.SysFont(None, 22)

rede_base = carregar_rede_base(CHECKPOINT_ENTRADA)
agentes = criar_populacao(rede_base)

geracao = 1
tempo = 0.0

historico_fitness = []
historico_coletas = []
historico_entregas = []
historico_colisoes = []
historico_melhor_tempo = []

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

    pygame.draw.line(screen, (50, 60, 80), START_POS, PACOTE_POS, 1)
    pygame.draw.line(screen, (50, 60, 80), PACOTE_POS, ENTREGA_POS, 1)

    for obstaculo in OBSTACULOS:
        pygame.draw.rect(screen, (160, 80, 80), obstaculo)
        pygame.draw.rect(screen, (255, 120, 120), obstaculo, 2)

    pygame.draw.circle(screen, (100, 100, 140), START_POS, 8, 2)
    screen.blit(font_sm.render("START", True, (100, 100, 140)), (int(START_POS.x) + 10, int(START_POS.y) - 8))

    pygame.draw.circle(screen, (80, 180, 255), PACOTE_POS, RAIO_COLETA, 2)
    pygame.draw.rect(screen, (100, 180, 255), pygame.Rect(int(PACOTE_POS.x) - 8, int(PACOTE_POS.y) - 8, 16, 16), 2)
    screen.blit(font_sm.render("PACOTE", True, (100, 180, 255)), (int(PACOTE_POS.x) + 10, int(PACOTE_POS.y) - 8))

    pygame.draw.circle(screen, (220, 80, 80), ENTREGA_POS, RAIO_ENTREGA, 2)
    pygame.draw.circle(screen, (255, 120, 120), ENTREGA_POS, 6)
    screen.blit(font_sm.render("ENTREGA", True, (255, 120, 120)), (int(ENTREGA_POS.x) + 8, int(ENTREGA_POS.y) - 8))

    for a in agentes:
        a.desenhar(screen)

    coletaram = sum(1 for a in agentes if a.coletou)
    entregaram = sum(1 for a in agentes if a.entregou)
    colisoes = sum(a.colisoes for a in agentes)
    fit_medio = sum(a.fitness for a in agentes) / NUM_AGENTES
    fit_melhor = max(a.fitness for a in agentes)
    taxa_atual = max(0.05, TAXA_MUTACAO * (0.97 ** geracao))

    tempos_entrega = [a.tempo_entrega for a in agentes if a.tempo_entrega is not None]
    melhor_tempo = min(tempos_entrega) if tempos_entrega else 0

    linhas = [
        f"Geração: {geracao}",
        f"Tempo: {tempo:.1f}s / {DURACAO_GERACAO}s",
        f"Coletaram: {coletaram} / {NUM_AGENTES}",
        f"Entregaram: {entregaram} / {NUM_AGENTES}",
        f"Colisões: {colisoes}",
        f"Fitness médio: {fit_medio:.1f}",
        f"Fitness melhor: {fit_melhor:.1f}",
        f"Melhor tempo: {melhor_tempo:.1f}s",
        f"Taxa mutação: {taxa_atual:.3f}",
        FASE_NOME,
        f"Carrega: {CHECKPOINT_ENTRADA}",
        f"Salva: {CHECKPOINT_SAIDA}",
        "SPACE = pular geração",
    ]

    hud = pygame.Surface((390, len(linhas) * 22 + 10), pygame.SRCALPHA)
    hud.fill((0, 0, 0, 150))
    screen.blit(hud, (5, 5))

    for i, texto in enumerate(linhas):
        screen.blit(font_sm.render(texto, True, (230, 230, 230)), (12, 10 + i * 22))

    if historico_fitness:
        gw, gh = 230, 130
        gx, gy = LARGURA - gw - 8, 8

        pygame.draw.rect(screen, (20, 25, 35), pygame.Rect(gx, gy, gw, gh))
        pygame.draw.rect(screen, (70, 75, 90), pygame.Rect(gx, gy, gw, gh), 1)
        screen.blit(font_sm.render("Fitness / Coletas / Entregas", True, (160, 160, 180)), (gx + 6, gy + 6))

        def desenhar_curva(valores, cor, maximo):
            if len(valores) < 2 or maximo <= 0:
                return

            valores = valores[-30:]
            pontos = []
            for i, v in enumerate(valores):
                x = gx + 8 + int(i * (gw - 16) / max(len(valores) - 1, 1))
                y = gy + gh - 12 - int((v / maximo) * (gh - 35))
                pontos.append((x, y))

            if len(pontos) > 1:
                pygame.draw.lines(screen, cor, False, pontos, 2)

        max_fitness = max(max(historico_fitness), 1)
        escala_eventos = max_fitness / NUM_AGENTES

        desenhar_curva(historico_fitness, (100, 200, 255), max_fitness)
        desenhar_curva([c * escala_eventos for c in historico_coletas], (255, 220, 80), max_fitness)
        desenhar_curva([e * escala_eventos for e in historico_entregas], (80, 255, 120), max_fitness)

        pygame.draw.line(screen, (100, 200, 255), (gx + 8, gy + gh - 8), (gx + 28, gy + gh - 8), 2)
        screen.blit(font_sm.render("fit", True, (100, 200, 255)), (gx + 32, gy + gh - 15))
        pygame.draw.line(screen, (255, 220, 80), (gx + 70, gy + gh - 8), (gx + 90, gy + gh - 8), 2)
        screen.blit(font_sm.render("coleta", True, (255, 220, 80)), (gx + 94, gy + gh - 15))
        pygame.draw.line(screen, (80, 255, 120), (gx + 145, gy + gh - 8), (gx + 165, gy + gh - 8), 2)
        screen.blit(font_sm.render("entrega", True, (80, 255, 120)), (gx + 169, gy + gh - 15))

    pygame.display.flip()

    if tempo >= DURACAO_GERACAO:
        fit_medio_f = sum(a.fitness for a in agentes) / NUM_AGENTES
        coletas_f = sum(1 for a in agentes if a.coletou)
        entregas_f = sum(1 for a in agentes if a.entregou)
        colisoes_f = sum(a.colisoes for a in agentes)
        tempos_entrega_f = [a.tempo_entrega for a in agentes if a.tempo_entrega is not None]
        melhor_tempo_f = min(tempos_entrega_f) if tempos_entrega_f else 0

        historico_fitness.append(fit_medio_f)
        historico_coletas.append(coletas_f)
        historico_entregas.append(entregas_f)
        historico_colisoes.append(colisoes_f)
        historico_melhor_tempo.append(melhor_tempo_f)

        print(
            f"Geração {geracao:3d} | "
            f"Fit médio: {fit_medio_f:8.1f} | "
            f"Melhor: {max(a.fitness for a in agentes):8.1f} | "
            f"Coletaram: {coletas_f:2d} | "
            f"Entregaram: {entregas_f:2d} | "
            f"Colisões: {colisoes_f:3d} | "
            f"Melhor tempo: {melhor_tempo_f:.1f}s"
        )

        salvar_melhor(agentes, CHECKPOINT_SAIDA)
        agentes = nova_geracao(agentes, geracao)

        if USA_VARIACAO:
            PACOTE_POS, ENTREGA_POS = gerar_posicoes()

        geracao += 1
        tempo = 0.0

pygame.quit()
print("\\nSimulação encerrada.")
