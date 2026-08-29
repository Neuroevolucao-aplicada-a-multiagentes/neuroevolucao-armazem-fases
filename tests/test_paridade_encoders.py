import math
import os
import sys

import numpy as np
import pygame

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_RAIZ, "src"))

from rede_transfer import RedeNeural
from simulador import Agente, Ambiente, CenarioConfig, RoboOperacional


def _mundo():
    cfg = CenarioConfig(
        nome="teste-paridade",
        usa_obstaculos=True,
        num_obstaculos=3,
        seed=7,
        duracao_geracao=45.0,
    )
    import random
    return Ambiente(cfg, rng=random.Random(7))


def _sincronizar(agente: Agente, robo: RoboOperacional, pos, vel, tempo, carregando):
    agente.pos = pygame.Vector2(pos)
    agente.vel = pygame.Vector2(vel)
    agente.tempo_vivo = tempo
    agente.carregando = carregando

    robo.pos = pygame.Vector2(pos)
    robo.vel = pygame.Vector2(vel)
    robo.tempo_ciclo_atual = tempo
    robo.carregando = carregando
    robo.pacote_pos = pygame.Vector2(agente.ambiente.pacote_pos)
    robo.entrega_pos = pygame.Vector2(agente.ambiente.entrega_pos)


def _comparar(carregando: bool, pos, vel, tempo):
    amb = _mundo()
    brain = RedeNeural()
    agente = Agente(brain, amb)
    robo = RoboOperacional(0, brain, amb, pygame.Vector2(pos))
    _sincronizar(agente, robo, pos, vel, tempo, carregando)

    inp_treino = agente.montar_inputs()
    inp_operacao = robo.montar_inputs(outros=[])

    assert inp_treino.shape == (16,), f"treino shape {inp_treino.shape}"
    assert inp_operacao.shape == (16,), f"operacao shape {inp_operacao.shape}"
    np.testing.assert_allclose(
        inp_treino, inp_operacao, rtol=1e-5, atol=1e-6,
        err_msg=f"encoders divergem (carregando={carregando})",
    )


def test_paridade_sem_carga():
    _comparar(carregando=False, pos=(150, 300), vel=(0.6, -0.4), tempo=10.0)


def test_paridade_com_carga():
    _comparar(carregando=True, pos=(400, 250), vel=(-0.3, 0.8), tempo=30.0)


def test_paridade_parado_no_inicio():
    _comparar(carregando=False, pos=(100, 300), vel=(0.0, 0.0), tempo=0.0)


def test_direcao_alvo_e_unitaria():
    amb = _mundo()
    brain = RedeNeural()
    agente = Agente(brain, amb)
    agente.pos = pygame.Vector2(200, 200)
    inp = agente.montar_inputs()
    norma = math.sqrt(inp[0] ** 2 + inp[1] ** 2)
    assert abs(norma - 1.0) < 1e-3, f"direcao ao alvo nao e unitaria: {norma}"


if __name__ == "__main__":
    test_paridade_sem_carga()
    test_paridade_com_carga()
    test_paridade_parado_no_inicio()
    test_direcao_alvo_e_unitaria()
    print("OK")
