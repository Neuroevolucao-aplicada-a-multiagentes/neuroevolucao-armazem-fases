import math
import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

import numpy as np
import pygame

LARGURA = 900
ALTURA = 600
DIAGONAL = math.sqrt(LARGURA ** 2 + ALTURA ** 2)
VELOCIDADE = 200.0
RAIO_AGENTE = 8
RAIO_COLETA = 20
RAIO_ENTREGA = 35

NUM_RAYS = 8
ALCANCE_RAY = 220.0


@dataclass
class CenarioConfig:
    nome: str
    checkpoint_entrada: Optional[str] = None
    checkpoint_saida: str = "melhor_rede.npz"

    num_agentes: int = 30
    duracao_geracao: float = 25.0
    num_geracoes: int = 100

    elite: int = 4
    taxa_mutacao: float = 0.20
    forca_mutacao: float = 0.30
    decaimento_mutacao: float = 0.98
    taxa_mutacao_min: float = 0.05
    forca_mutacao_min: float = 0.08

    usa_variacao_posicoes: bool = False
    usa_obstaculos: bool = False
    num_robos_moveis: int = 0

    obstaculos_fixos: List[Tuple[int, int, int, int]] = field(default_factory=list)
    pacote_fixo: Tuple[int, int] = (500, 200)
    entrega_fixa: Tuple[int, int] = (750, 450)
    start_fixo: Tuple[int, int] = (100, 300)

    cenarios_por_geracao: int = 1
    seed: Optional[int] = None

    objetivo_simples: bool = False

    bonus_coleta: float = 700.0
    bonus_entrega: float = 2500.0
    bonus_tempo_factor: float = 50.0
    peso_progresso: float = 12.0
    peso_alinhamento: float = 0.05
    peso_gradiente_inverso: float = 0.0
    penalidade_colisao: float = 220.0
    penalidade_parado: float = 0.05
    penalidade_distancia_factor: float = 0.02
    max_colisoes_morte: int = 5

    bonus_proximidade_max: float = 1500.0
    pool_selecao_fracao: float = 0.5

    num_obstaculos: int = 3
    obstaculos_no_caminho: bool = False
    offset_obstaculo_perpendicular: int = 40
    num_obstaculos_extra_livres: int = 0


def _vec(x, y) -> pygame.Vector2:
    return pygame.Vector2(float(x), float(y))


def gerar_obstaculos_aleatorios(n: int, rng: random.Random,
                                exclude_zones: List[Tuple[int, int, int]] = None) -> List[pygame.Rect]:
    obstaculos = []
    exclude_zones = exclude_zones or []
    tentativas = 0
    while len(obstaculos) < n and tentativas < 500:
        tentativas += 1
        w = rng.randint(50, 90)
        h = rng.randint(60, 130)
        x = rng.randint(180, LARGURA - w - 60)
        y = rng.randint(80, ALTURA - h - 80)
        rect = pygame.Rect(x, y, w, h)
        rect_inflado = rect.inflate(40, 40)

        ok = True
        for zx, zy, zr in exclude_zones:
            if rect_inflado.collidepoint(zx, zy):
                ok = False
                break
        for outro in obstaculos:
            if rect_inflado.colliderect(outro.inflate(20, 20)):
                ok = False
                break
        if ok:
            obstaculos.append(rect)
    return obstaculos


def gerar_obstaculos_no_caminho(segmentos: List[Tuple[pygame.Vector2, pygame.Vector2]],
                                n_por_segmento: int,
                                rng: random.Random,
                                exclude_zones: List[Tuple[int, int, int]] = None,
                                offset_perp: int = 40) -> List[pygame.Rect]:
    """Posiciona obstaculos PERTO do caminho start->pacote->entrega para forcar desvio.

    Para cada segmento (origem, destino), n_por_segmento obstaculos sao colocados
    em pontos ao longo do segmento, com deslocamento perpendicular aleatorio
    (+/- offset_perp px) - o agente NAO consegue ir reto, mas sempre tem espaco
    para contornar por um dos lados.

    Argumentos:
        segmentos: lista de pares (origem, destino) que definem o caminho ideal.
        n_por_segmento: quantos obstaculos por trecho.
        rng: gerador de aleatorios para reprodutibilidade.
        exclude_zones: lista de (cx, cy, raio) que nao podem ter obstaculo em cima.
        offset_perp: deslocamento maximo perpendicular ao segmento (px).
    """
    obstaculos: List[pygame.Rect] = []
    exclude_zones = exclude_zones or []
    margem_borda = 50

    for origem, destino in segmentos:
        dx = destino.x - origem.x
        dy = destino.y - origem.y
        comprimento = math.sqrt(dx * dx + dy * dy)
        if comprimento < 50:
            continue
        ux, uy = dx / comprimento, dy / comprimento
        perp_x, perp_y = -uy, ux

        if n_por_segmento == 1:
            ts = [0.5]
        else:
            espaco = 0.6 / max(n_por_segmento - 1, 1)
            inicio = 0.5 - 0.3
            ts = [inicio + i * espaco for i in range(n_por_segmento)]

        for t in ts:
            colocado = False
            for tentativa in range(40):
                t_real = t + rng.uniform(-0.04, 0.04)
                offset = rng.uniform(-offset_perp, offset_perp)
                if abs(offset) < 12:
                    offset = 12 * (1 if offset >= 0 else -1)

                cx = origem.x + dx * t_real + perp_x * offset
                cy = origem.y + dy * t_real + perp_y * offset

                w = rng.randint(45, 75)
                h = rng.randint(55, 100)
                x = int(cx - w / 2)
                y = int(cy - h / 2)

                if x < margem_borda or x + w > LARGURA - margem_borda:
                    continue
                if y < margem_borda or y + h > ALTURA - margem_borda:
                    continue

                rect = pygame.Rect(x, y, w, h)
                rect_check = rect.inflate(30, 30)

                raio_obs = max(w, h) / 2
                cx_obs, cy_obs = rect.centerx, rect.centery
                colisao_zona = False
                for zx, zy, zr in exclude_zones:
                    dist = math.sqrt((cx_obs - zx) ** 2 + (cy_obs - zy) ** 2)
                    if dist < zr + raio_obs + 15:
                        colisao_zona = True
                        break
                if colisao_zona:
                    continue

                colisao_outro = False
                for outro in obstaculos:
                    if rect_check.colliderect(outro.inflate(25, 25)):
                        colisao_outro = True
                        break
                if colisao_outro:
                    continue

                obstaculos.append(rect)
                colocado = True
                break

    return obstaculos


class RoboMovel:
    def __init__(self, p1: pygame.Vector2, p2: pygame.Vector2, velocidade: float = 80.0):
        self.p1 = pygame.Vector2(p1)
        self.p2 = pygame.Vector2(p2)
        self.pos = pygame.Vector2(p1)
        self.alvo = pygame.Vector2(p2)
        self.velocidade = velocidade
        self.raio = 12

    def atualizar(self, dt: float):
        direcao = self.alvo - self.pos
        if direcao.length() < 5:
            self.alvo = self.p1 if self.alvo == self.p2 else self.p2
        else:
            self.pos += direcao.normalize() * self.velocidade * dt

    def rect(self) -> pygame.Rect:
        r = self.raio
        return pygame.Rect(int(self.pos.x - r), int(self.pos.y - r), 2 * r, 2 * r)


class Ambiente:
    def __init__(self, config: CenarioConfig, rng: Optional[random.Random] = None):
        self.config = config
        self.rng = rng or random.Random()
        self.obstaculos: List[pygame.Rect] = []
        self.robos_moveis: List[RoboMovel] = []
        self.pacote_pos = _vec(*config.pacote_fixo)
        self.entrega_pos = _vec(*config.entrega_fixa)
        self.start_pos = _vec(*config.start_fixo)
        self.resetar_cenario()

    def resetar_cenario(self):
        cfg = self.config

        self.start_pos = _vec(*cfg.start_fixo)
        self.obstaculos = []
        if cfg.usa_variacao_posicoes:
            self.pacote_pos, self.entrega_pos = self._gerar_posicoes_validas()
        else:
            self.pacote_pos = _vec(*cfg.pacote_fixo)
            self.entrega_pos = _vec(*cfg.entrega_fixa)

        if cfg.usa_obstaculos and cfg.obstaculos_fixos:
            self.obstaculos = [pygame.Rect(*o) for o in cfg.obstaculos_fixos]
        elif cfg.usa_obstaculos:
            zonas = [
                (self.start_pos.x, self.start_pos.y, 60),
                (self.pacote_pos.x, self.pacote_pos.y, 50),
                (self.entrega_pos.x, self.entrega_pos.y, 60),
            ]
            obstaculos_caminho: List[pygame.Rect] = []
            if cfg.obstaculos_no_caminho and cfg.num_obstaculos > 0:
                segmentos = [
                    (self.start_pos, self.pacote_pos),
                    (self.pacote_pos, self.entrega_pos),
                ]
                if cfg.objetivo_simples:
                    segmentos = [(self.start_pos, self.pacote_pos)]
                n_por_seg = max(1, cfg.num_obstaculos // len(segmentos))
                obstaculos_caminho = gerar_obstaculos_no_caminho(
                    segmentos, n_por_seg, self.rng, zonas,
                    offset_perp=cfg.offset_obstaculo_perpendicular,
                )
            elif (not cfg.obstaculos_no_caminho) and cfg.num_obstaculos > 0:
                obstaculos_caminho = gerar_obstaculos_aleatorios(
                    cfg.num_obstaculos, self.rng, zonas,
                )

            obstaculos_livres: List[pygame.Rect] = []
            if cfg.num_obstaculos_extra_livres > 0:
                zonas_estendidas = zonas + [
                    (o.centerx, o.centery, max(o.width, o.height) / 2 + 20)
                    for o in obstaculos_caminho
                ]
                obstaculos_livres = gerar_obstaculos_aleatorios(
                    cfg.num_obstaculos_extra_livres, self.rng, zonas_estendidas,
                )

            self.obstaculos = obstaculos_caminho + obstaculos_livres

        self.robos_moveis = []
        for _ in range(cfg.num_robos_moveis):
            p1 = _vec(self.rng.randint(150, LARGURA - 150), self.rng.randint(100, ALTURA - 100))
            p2 = _vec(self.rng.randint(150, LARGURA - 150), self.rng.randint(100, ALTURA - 100))
            self.robos_moveis.append(RoboMovel(p1, p2, velocidade=self.rng.uniform(40, 90)))

    def _gerar_posicoes_validas(self) -> Tuple[pygame.Vector2, pygame.Vector2]:
        for _ in range(200):
            pacote = _vec(self.rng.randint(200, LARGURA - 200), self.rng.randint(100, ALTURA - 100))
            if self._ponto_em_obstaculo(pacote, margem=30):
                continue
            if pacote.distance_to(_vec(*self.config.start_fixo)) < 150:
                continue
            if self.config.objetivo_simples:
                return pacote, pacote
            entrega = _vec(self.rng.randint(200, LARGURA - 200), self.rng.randint(100, ALTURA - 100))
            if entrega.distance_to(pacote) < 200:
                continue
            if self._ponto_em_obstaculo(entrega, margem=30):
                continue
            return pacote, entrega
        return _vec(*self.config.pacote_fixo), _vec(*self.config.entrega_fixa)

    def _ponto_em_obstaculo(self, p: pygame.Vector2, margem: int = 0) -> bool:
        for obs in self.obstaculos:
            if obs.inflate(margem * 2, margem * 2).collidepoint(p.x, p.y):
                return True
        return False

    def atualizar(self, dt: float):
        for robo in self.robos_moveis:
            robo.atualizar(dt)

    def colide_com_obstaculo(self, pos: pygame.Vector2, raio: int = RAIO_AGENTE) -> bool:
        rect = pygame.Rect(int(pos.x - raio), int(pos.y - raio), 2 * raio, 2 * raio)
        for obs in self.obstaculos:
            if rect.colliderect(obs):
                return True
        return False

    def colide_com_robo(self, pos: pygame.Vector2, raio: int = RAIO_AGENTE) -> bool:
        for robo in self.robos_moveis:
            if pos.distance_to(robo.pos) < raio + robo.raio:
                return True
        return False

    def raycast(self, origem: pygame.Vector2, angulo_rad: float, alcance: float = ALCANCE_RAY) -> float:
        passo = 6.0
        dx = math.cos(angulo_rad) * passo
        dy = math.sin(angulo_rad) * passo
        x, y = origem.x, origem.y
        n_passos = int(alcance / passo)
        for i in range(1, n_passos + 1):
            x += dx
            y += dy
            if x < 0 or x > LARGURA or y < 0 or y > ALTURA:
                return i * passo
            for obs in self.obstaculos:
                if obs.collidepoint(x, y):
                    return i * passo
            for robo in self.robos_moveis:
                if (x - robo.pos.x) ** 2 + (y - robo.pos.y) ** 2 <= robo.raio ** 2:
                    return i * passo
        return alcance


class Agente:
    def __init__(self, brain, ambiente: Ambiente):
        self.brain = brain
        self.ambiente = ambiente
        self.pos = pygame.Vector2(ambiente.start_pos)
        self.vel = pygame.Vector2(0, 0)
        self.reset_estado()

    def reset_estado(self):
        self.pos = pygame.Vector2(self.ambiente.start_pos)
        self.vel = pygame.Vector2(0, 0)
        self.fitness = 0.0
        self.carregando = False
        self.coletou = False
        self.entregou = False
        self.morto = False
        self.colisoes = 0
        self.em_colisao = False
        self.tempo_vivo = 0.0
        self.tempo_entrega: Optional[float] = None
        self.melhor_dist_alvo: Optional[float] = None
        self.distancia_percorrida = 0.0
        self.passos_parado = 0

    def alvo_atual(self) -> pygame.Vector2:
        if self.ambiente.config.objetivo_simples:
            return self.ambiente.pacote_pos
        return self.ambiente.entrega_pos if self.carregando else self.ambiente.pacote_pos

    def montar_inputs(self) -> np.ndarray:
        amb = self.ambiente
        alvo = self.alvo_atual()
        dx_alvo = alvo.x - self.pos.x
        dy_alvo = alvo.y - self.pos.y
        dist_alvo = self.pos.distance_to(alvo)

        dir_alvo_x = dx_alvo / (dist_alvo + 1e-6)
        dir_alvo_y = dy_alvo / (dist_alvo + 1e-6)

        if amb.config.objetivo_simples:
            dir_ent_x = dir_alvo_x
            dir_ent_y = dir_alvo_y
        else:
            dx_ent = amb.entrega_pos.x - self.pos.x
            dy_ent = amb.entrega_pos.y - self.pos.y
            dist_ent = math.sqrt(dx_ent * dx_ent + dy_ent * dy_ent)
            dir_ent_x = dx_ent / (dist_ent + 1e-6)
            dir_ent_y = dy_ent / (dist_ent + 1e-6)

        rays = []
        if self.vel.length() > 0.01:
            heading = math.atan2(self.vel.y, self.vel.x)
        else:
            heading = math.atan2(dy_alvo, dx_alvo) if (dx_alvo or dy_alvo) else 0.0

        for i in range(NUM_RAYS):
            ang = heading + (i / NUM_RAYS) * 2 * math.pi
            dist = amb.raycast(self.pos, ang)
            rays.append(dist / ALCANCE_RAY)

        inputs = [
            dir_alvo_x,
            dir_alvo_y,
            dist_alvo / DIAGONAL,
            1.0 if self.carregando else 0.0,
            dir_ent_x,
            dir_ent_y,
            self.vel.length(),
            min(self.tempo_vivo / self.ambiente.config.duracao_geracao, 1.0),
        ] + rays

        return np.asarray(inputs, dtype=np.float32)

    def passo(self, dt: float):
        if self.entregou or self.morto:
            return

        self.tempo_vivo += dt
        cfg = self.ambiente.config
        alvo = self.alvo_atual()
        dist_antes = self.pos.distance_to(alvo)

        output = self.brain.forward(self.montar_inputs())
        nova_vel = pygame.Vector2(float(output[0]), float(output[1]))
        if nova_vel.length() > 1:
            nova_vel = nova_vel.normalize()
        self.vel = nova_vel

        deslocamento = self.vel * VELOCIDADE * dt
        colidiu = False

        nova_x = pygame.Vector2(self.pos.x + deslocamento.x, self.pos.y)
        nova_x.x = max(RAIO_AGENTE, min(LARGURA - RAIO_AGENTE, nova_x.x))
        if self.ambiente.colide_com_obstaculo(nova_x) or self.ambiente.colide_com_robo(nova_x):
            colidiu = True
        else:
            self.pos.x = nova_x.x

        nova_y = pygame.Vector2(self.pos.x, self.pos.y + deslocamento.y)
        nova_y.y = max(RAIO_AGENTE, min(ALTURA - RAIO_AGENTE, nova_y.y))
        if self.ambiente.colide_com_obstaculo(nova_y) or self.ambiente.colide_com_robo(nova_y):
            colidiu = True
        else:
            self.pos.y = nova_y.y

        if not colidiu:
            self.distancia_percorrida += deslocamento.length()
            self.em_colisao = False
        else:
            if not self.em_colisao:
                self.colisoes += 1
                self.fitness -= cfg.penalidade_colisao
                self.em_colisao = True
                if self.colisoes >= cfg.max_colisoes_morte:
                    self.morto = True
                    return

        dist_depois = self.pos.distance_to(alvo)

        if dist_antes > 0 and self.vel.length() > 0:
            direcao = pygame.Vector2(alvo.x - self.pos.x, alvo.y - self.pos.y)
            if direcao.length() > 0:
                alinhamento = self.vel.normalize().dot(direcao.normalize())
                self.fitness += alinhamento * cfg.peso_alinhamento

        progresso_delta = dist_antes - dist_depois
        self.fitness += progresso_delta * cfg.peso_progresso

        if self.melhor_dist_alvo is None or dist_depois < self.melhor_dist_alvo:
            self.melhor_dist_alvo = dist_depois

        if cfg.peso_gradiente_inverso > 0:
            self.fitness += cfg.peso_gradiente_inverso / (dist_depois + 1.0)

        if self.vel.length() < 0.05:
            self.passos_parado += 1
            self.fitness -= cfg.penalidade_parado
        else:
            self.passos_parado = 0

        if cfg.objetivo_simples:
            if self.pos.distance_to(self.ambiente.pacote_pos) <= RAIO_COLETA:
                self.coletou = True
                self.entregou = True
                self.tempo_entrega = self.tempo_vivo
                bonus_tempo = max(0, cfg.duracao_geracao - self.tempo_vivo) * cfg.bonus_tempo_factor
                penalidade_rota = self.distancia_percorrida * cfg.penalidade_distancia_factor
                self.fitness += cfg.bonus_entrega + bonus_tempo - penalidade_rota
                self.melhor_dist_alvo = None
        elif not self.carregando and not self.coletou:
            if self.pos.distance_to(self.ambiente.pacote_pos) <= RAIO_COLETA:
                self.carregando = True
                self.coletou = True
                self.fitness += cfg.bonus_coleta
                self.melhor_dist_alvo = None
        elif self.carregando:
            if self.pos.distance_to(self.ambiente.entrega_pos) <= RAIO_ENTREGA:
                self.carregando = False
                self.entregou = True
                self.tempo_entrega = self.tempo_vivo
                bonus_tempo = max(0, cfg.duracao_geracao - self.tempo_vivo) * cfg.bonus_tempo_factor
                penalidade_rota = self.distancia_percorrida * cfg.penalidade_distancia_factor
                self.fitness += cfg.bonus_entrega + bonus_tempo - penalidade_rota
                self.melhor_dist_alvo = None


def criar_populacao(cfg: CenarioConfig, ambiente: Ambiente, rede_base, input_size: int):
    from rede_transfer import RedeNeural
    agentes = []
    for i in range(cfg.num_agentes):
        if rede_base is not None:
            brain = rede_base.copy()
            if i > 0:
                brain.mutate(rate=0.15, strength=0.20)
        else:
            brain = RedeNeural(input_size=input_size)
        agentes.append(Agente(brain, ambiente))
    return agentes


def nova_geracao(agentes: List[Agente], geracao: int, cfg: CenarioConfig, ambiente: Ambiente):
    agentes.sort(
        key=lambda a: (
            int(a.entregou),
            int(a.coletou),
            -a.colisoes,
            -(a.tempo_entrega if a.tempo_entrega is not None else 9999),
            a.fitness,
        ),
        reverse=True,
    )

    taxa = max(cfg.taxa_mutacao_min, cfg.taxa_mutacao * (cfg.decaimento_mutacao ** geracao))
    forca = max(cfg.forca_mutacao_min, cfg.forca_mutacao * (cfg.decaimento_mutacao ** geracao))

    novos: List[Agente] = []
    for a in agentes[: cfg.elite]:
        novos.append(Agente(a.brain.copy(), ambiente))

    tamanho_pool = max(int(cfg.num_agentes * cfg.pool_selecao_fracao), cfg.elite * 2)
    pool = agentes[:tamanho_pool]
    while len(novos) < cfg.num_agentes:
        pai1 = random.choice(pool)
        pai2 = random.choice(pool)
        filho_brain = pai1.brain.crossover(pai2.brain)
        filho_brain.mutate(taxa, forca)
        novos.append(Agente(filho_brain, ambiente))

    for a in novos:
        a.reset_estado()
    return novos, taxa, forca


def rodar_geracao(agentes: List[Agente], ambiente: Ambiente, cfg: CenarioConfig,
                  dt_fixo: float = 1.0 / 60.0, on_step: Optional[Callable] = None) -> dict:
    tempo = 0.0
    max_passos = int(cfg.duracao_geracao / dt_fixo) + 1
    for passo in range(max_passos):
        if tempo >= cfg.duracao_geracao:
            break
        ambiente.atualizar(dt_fixo)
        for a in agentes:
            a.passo(dt_fixo)
        if on_step is not None:
            interromper = on_step(passo, tempo)
            if interromper:
                break
        tempo += dt_fixo
        if all(a.entregou or a.morto for a in agentes):
            break

    _aplicar_bonus_proximidade(agentes, ambiente, cfg)
    return resumir_geracao(agentes, cfg)


def _aplicar_bonus_proximidade(agentes: List[Agente], ambiente: Ambiente, cfg: CenarioConfig):
    if cfg.bonus_proximidade_max <= 0:
        return
    raio_efetivo = 200.0
    for a in agentes:
        if a.entregou:
            continue
        alvo = a.alvo_atual()
        dist = a.pos.distance_to(alvo)
        if dist >= raio_efetivo:
            continue
        prox = 1.0 - dist / raio_efetivo
        a.fitness += cfg.bonus_proximidade_max * (prox ** 2)


def resumir_geracao(agentes: List[Agente], cfg: CenarioConfig) -> dict:
    n = len(agentes)
    fits = [a.fitness for a in agentes]
    coletas = sum(1 for a in agentes if a.coletou)
    entregas = sum(1 for a in agentes if a.entregou)
    colisoes = sum(a.colisoes for a in agentes)
    mortos = sum(1 for a in agentes if a.morto)
    tempos = [a.tempo_entrega for a in agentes if a.tempo_entrega is not None]
    distancias = [a.distancia_percorrida for a in agentes if a.entregou]

    return {
        "fit_medio": float(np.mean(fits)),
        "fit_melhor": float(np.max(fits)),
        "fit_pior": float(np.min(fits)),
        "fit_std": float(np.std(fits)),
        "coletas": coletas,
        "entregas": entregas,
        "colisoes": colisoes,
        "mortos": mortos,
        "taxa_coleta": coletas / n,
        "taxa_entrega": entregas / n,
        "melhor_tempo": float(min(tempos)) if tempos else 0.0,
        "tempo_medio_entrega": float(np.mean(tempos)) if tempos else 0.0,
        "distancia_media_entrega": float(np.mean(distancias)) if distancias else 0.0,
    }


class RoboOperacional:
    def __init__(self, idx: int, brain, ambiente: Ambiente, pos_inicial: pygame.Vector2):
        self.id = idx
        self.brain = brain
        self.ambiente = ambiente
        self.pos = pygame.Vector2(pos_inicial)
        self.vel = pygame.Vector2(0, 0)
        self.raio = RAIO_AGENTE

        self.pacote_pos, self.entrega_pos = self._sortear_par()
        self.carregando = False

        self.total_entregas = 0
        self.colisoes_obstaculo = 0
        self.colisoes_inter_robo = 0
        self.em_colisao_obs = False
        self.em_colisao_robo = False
        self.tempos_ciclo: List[float] = []
        self.tempo_ciclo_atual = 0.0
        self.distancia_total = 0.0

    def _sortear_par(self) -> Tuple[pygame.Vector2, pygame.Vector2]:
        rng = self.ambiente.rng
        for _ in range(200):
            p = _vec(rng.randint(120, LARGURA - 120), rng.randint(80, ALTURA - 80))
            if self.ambiente._ponto_em_obstaculo(p, margem=20):
                continue
            e = _vec(rng.randint(120, LARGURA - 120), rng.randint(80, ALTURA - 80))
            if self.ambiente._ponto_em_obstaculo(e, margem=20):
                continue
            if e.distance_to(p) < 200:
                continue
            return p, e
        return _vec(*self.ambiente.config.pacote_fixo), _vec(*self.ambiente.config.entrega_fixa)

    def alvo_atual(self) -> pygame.Vector2:
        return self.entrega_pos if self.carregando else self.pacote_pos

    def _raycast_com_robos(self, angulo_rad: float, outros: List["RoboOperacional"],
                           alcance: float = ALCANCE_RAY) -> float:
        passo = 6.0
        dx = math.cos(angulo_rad) * passo
        dy = math.sin(angulo_rad) * passo
        x, y = self.pos.x, self.pos.y
        n_passos = int(alcance / passo)
        for i in range(1, n_passos + 1):
            x += dx
            y += dy
            if x < 0 or x > LARGURA or y < 0 or y > ALTURA:
                return i * passo
            for obs in self.ambiente.obstaculos:
                if obs.collidepoint(x, y):
                    return i * passo
            for robo_m in self.ambiente.robos_moveis:
                if (x - robo_m.pos.x) ** 2 + (y - robo_m.pos.y) ** 2 <= robo_m.raio ** 2:
                    return i * passo
            for outro in outros:
                if outro is self:
                    continue
                if (x - outro.pos.x) ** 2 + (y - outro.pos.y) ** 2 <= outro.raio ** 2:
                    return i * passo
        return alcance

    def montar_inputs(self, outros: List["RoboOperacional"]) -> np.ndarray:
        alvo = self.alvo_atual()
        dx_alvo = alvo.x - self.pos.x
        dy_alvo = alvo.y - self.pos.y
        dist_alvo = self.pos.distance_to(alvo)

        dx_ent = self.entrega_pos.x - self.pos.x
        dy_ent = self.entrega_pos.y - self.pos.y

        if self.vel.length() > 0.01:
            heading = math.atan2(self.vel.y, self.vel.x)
        else:
            heading = math.atan2(dy_alvo, dx_alvo) if (dx_alvo or dy_alvo) else 0.0

        rays = []
        for i in range(NUM_RAYS):
            ang = heading + (i / NUM_RAYS) * 2 * math.pi
            dist = self._raycast_com_robos(ang, outros)
            rays.append(dist / ALCANCE_RAY)

        return np.asarray([
            dx_alvo / LARGURA,
            dy_alvo / ALTURA,
            dist_alvo / DIAGONAL,
            1.0 if self.carregando else 0.0,
            dx_ent / LARGURA,
            dy_ent / ALTURA,
            self.vel.length(),
            0.5,
        ] + rays, dtype=np.float32)

    def passo(self, dt: float, outros: List["RoboOperacional"]):
        self.tempo_ciclo_atual += dt

        output = self.brain.forward(self.montar_inputs(outros))
        nova_vel = pygame.Vector2(float(output[0]), float(output[1]))
        if nova_vel.length() > 1:
            nova_vel = nova_vel.normalize()
        self.vel = nova_vel

        desloc = self.vel * VELOCIDADE * dt

        colidiu_obs = False
        colidiu_robo = False

        nova_x = pygame.Vector2(self.pos.x + desloc.x, self.pos.y)
        nova_x.x = max(self.raio, min(LARGURA - self.raio, nova_x.x))
        if self.ambiente.colide_com_obstaculo(nova_x) or self.ambiente.colide_com_robo(nova_x):
            colidiu_obs = True
        elif self._colide_com_outro_robo(nova_x, outros):
            colidiu_robo = True
        else:
            self.pos.x = nova_x.x

        nova_y = pygame.Vector2(self.pos.x, self.pos.y + desloc.y)
        nova_y.y = max(self.raio, min(ALTURA - self.raio, nova_y.y))
        if self.ambiente.colide_com_obstaculo(nova_y) or self.ambiente.colide_com_robo(nova_y):
            colidiu_obs = True
        elif self._colide_com_outro_robo(nova_y, outros):
            colidiu_robo = True
        else:
            self.pos.y = nova_y.y

        if not colidiu_obs and not colidiu_robo:
            self.distancia_total += desloc.length()

        if colidiu_obs and not self.em_colisao_obs:
            self.colisoes_obstaculo += 1
            self.em_colisao_obs = True
        elif not colidiu_obs:
            self.em_colisao_obs = False

        if colidiu_robo and not self.em_colisao_robo:
            self.colisoes_inter_robo += 1
            self.em_colisao_robo = True
        elif not colidiu_robo:
            self.em_colisao_robo = False

        if not self.carregando:
            if self.pos.distance_to(self.pacote_pos) <= RAIO_COLETA:
                self.carregando = True
        else:
            if self.pos.distance_to(self.entrega_pos) <= RAIO_ENTREGA:
                self.carregando = False
                self.total_entregas += 1
                self.tempos_ciclo.append(self.tempo_ciclo_atual)
                self.tempo_ciclo_atual = 0.0
                self.pacote_pos, self.entrega_pos = self._sortear_par()

    def _colide_com_outro_robo(self, nova_pos: pygame.Vector2,
                                outros: List["RoboOperacional"]) -> bool:
        for outro in outros:
            if outro is self:
                continue
            if nova_pos.distance_to(outro.pos) < self.raio + outro.raio:
                return True
        return False


def rodar_operacao_multiagente(brain, num_robos: int, ambiente: Ambiente,
                                duracao: float = 60.0, dt: float = 1.0 / 60.0,
                                on_step: Optional[Callable] = None) -> Tuple[List[RoboOperacional], dict]:
    robos: List[RoboOperacional] = []
    rng = ambiente.rng
    margem = 60
    for i in range(num_robos):
        for _ in range(100):
            p = _vec(rng.randint(margem, LARGURA - margem), rng.randint(margem, ALTURA - margem))
            if ambiente._ponto_em_obstaculo(p, margem=20):
                continue
            if all(p.distance_to(r.pos) > 40 for r in robos):
                robos.append(RoboOperacional(i, brain, ambiente, p))
                break
        else:
            robos.append(RoboOperacional(i, brain, ambiente,
                                          _vec(rng.randint(margem, LARGURA - margem),
                                               rng.randint(margem, ALTURA - margem))))

    tempo = 0.0
    max_passos = int(duracao / dt) + 1
    for passo in range(max_passos):
        if tempo >= duracao:
            break
        ambiente.atualizar(dt)
        for r in robos:
            r.passo(dt, robos)
        if on_step is not None:
            if on_step(passo, tempo, robos):
                break
        tempo += dt

    return robos, _resumir_operacao(robos, duracao)


def _resumir_operacao(robos: List[RoboOperacional], duracao: float) -> dict:
    total_entregas = sum(r.total_entregas for r in robos)
    col_obs = sum(r.colisoes_obstaculo for r in robos)
    col_robo = sum(r.colisoes_inter_robo for r in robos)
    todos_ciclos = [t for r in robos for t in r.tempos_ciclo]
    dist_total = sum(r.distancia_total for r in robos)

    throughput = total_entregas / duracao if duracao > 0 else 0.0
    throughput_por_robo = throughput / len(robos) if robos else 0.0

    return {
        "num_robos": len(robos),
        "duracao_seg": duracao,
        "total_entregas": total_entregas,
        "throughput_entregas_por_seg": throughput,
        "throughput_por_robo": throughput_por_robo,
        "colisoes_obstaculo": col_obs,
        "colisoes_inter_robo": col_robo,
        "tempo_medio_ciclo": float(np.mean(todos_ciclos)) if todos_ciclos else 0.0,
        "tempo_min_ciclo": float(np.min(todos_ciclos)) if todos_ciclos else 0.0,
        "tempo_max_ciclo": float(np.max(todos_ciclos)) if todos_ciclos else 0.0,
        "distancia_total_px": dist_total,
        "ciclos_completos": len(todos_ciclos),
    }
