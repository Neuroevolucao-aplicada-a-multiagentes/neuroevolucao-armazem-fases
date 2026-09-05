"""Gera o fixture de referencia do contrato de I/O da rede.

Constroi um mundo totalmente deterministico (obstaculos e robos fixos,
sem RNG), calcula o vetor de 16 entradas e a saida da rede para varios
estados do agente, e grava tudo em tests/golden_vectors.json.

O arquivo serve para validar qualquer reimplementacao do controlador em
outra linguagem (GDScript no Godot): dado o mesmo mundo e o mesmo estado,
a implementacao tem de reproduzir os mesmos 16 inputs e a mesma saida.

Rodar: python src/gerar_golden_vectors.py
"""
import json
import os
import sys

import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rede_transfer import RedeNeural
from simulador import (
    ALCANCE_RAY, ALTURA, DIAGONAL, LARGURA, NUM_RAYS, RAIO_AGENTE,
    RAIO_COLETA, RAIO_ENTREGA, VELOCIDADE,
    Agente, Ambiente, CenarioConfig, RoboMovel,
)

CHECKPOINT = "melhor_rede_fase5.npz"
SAIDA = os.path.join("tests", "golden_vectors.json")

DURACAO_GERACAO = 45.0
OBSTACULOS = [(300, 150, 70, 110), (520, 320, 80, 90), (200, 400, 60, 120)]
ROBOS_MOVEIS = [(430, 250), (660, 180)]
PACOTE = (500, 200)
ENTREGA = (750, 450)
START = (100, 300)

# pos_x, pos_y, vel_x, vel_y, carregando, tempo_vivo
CASOS = [
    (100.0, 300.0, 0.0, 0.0, False, 0.0),
    (250.0, 300.0, 0.8, -0.2, False, 5.0),
    (420.0, 220.0, 0.3, 0.6, False, 12.5),
    (500.0, 200.0, -0.5, 0.5, True, 18.0),
    (610.0, 330.0, 1.0, 0.0, True, 27.5),
    (740.0, 440.0, 0.1, 0.9, True, 44.0),
    (860.0, 60.0, -0.7, 0.7, False, 33.0),
    (60.0, 560.0, 0.0, -1.0, True, 45.0),
]


def _montar_ambiente() -> Ambiente:
    cfg = CenarioConfig(
        nome="golden",
        duracao_geracao=DURACAO_GERACAO,
        usa_obstaculos=True,
        obstaculos_fixos=list(OBSTACULOS),
        pacote_fixo=PACOTE,
        entrega_fixa=ENTREGA,
        start_fixo=START,
        num_robos_moveis=0,
        seed=0,
    )
    amb = Ambiente(cfg)
    amb.obstaculos = [pygame.Rect(*o) for o in OBSTACULOS]
    amb.robos_moveis = [
        RoboMovel(pygame.Vector2(x, y), pygame.Vector2(x, y), velocidade=0.0)
        for x, y in ROBOS_MOVEIS
    ]
    return amb


def gerar() -> dict:
    rede = RedeNeural()
    rede.carregar(CHECKPOINT)

    amb = _montar_ambiente()
    agente = Agente(rede, amb)

    casos = []
    for px, py, vx, vy, carregando, tempo in CASOS:
        agente.reset_estado()
        agente.pos = pygame.Vector2(px, py)
        agente.vel = pygame.Vector2(vx, vy)
        agente.carregando = carregando
        agente.tempo_vivo = tempo

        entradas = agente.montar_inputs()
        saida = rede.forward(entradas)

        casos.append({
            "pos": [px, py],
            "vel": [vx, vy],
            "carregando": carregando,
            "tempo_vivo": tempo,
            "inputs": [round(float(v), 9) for v in entradas],
            "saida": [round(float(v), 9) for v in saida],
        })

    return {
        "checkpoint": CHECKPOINT,
        "arquitetura": [int(rede.input_size), int(rede.hidden_1),
                        int(rede.hidden_2), int(rede.output_size)],
        "constantes": {
            "largura": LARGURA,
            "altura": ALTURA,
            "diagonal": round(DIAGONAL, 9),
            "num_rays": NUM_RAYS,
            "alcance_ray": ALCANCE_RAY,
            "passo_ray": 6.0,
            "raio_agente": RAIO_AGENTE,
            "raio_coleta": RAIO_COLETA,
            "raio_entrega": RAIO_ENTREGA,
            "velocidade": VELOCIDADE,
            "duracao_geracao": DURACAO_GERACAO,
        },
        "mundo": {
            "obstaculos": [list(o) for o in OBSTACULOS],
            "robos_moveis": [[x, y, 12] for x, y in ROBOS_MOVEIS],
            "pacote": list(PACOTE),
            "entrega": list(ENTREGA),
        },
        "casos": casos,
    }


if __name__ == "__main__":
    dados = gerar()
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)
    print(f"{len(dados['casos'])} casos gravados em {SAIDA}")
    for i, c in enumerate(dados["casos"]):
        print(f"  caso {i}: carregando={int(c['carregando'])} "
              f"-> vx={c['saida'][0]:+.4f} vy={c['saida'][1]:+.4f}")
