import json
import os
import sys

import numpy as np
import pygame

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_RAIZ, "src"))

from gerar_golden_vectors import _montar_ambiente, CHECKPOINT
from rede_transfer import RedeNeural
from simulador import Agente

_FIXTURE = os.path.join(_RAIZ, "tests", "golden_vectors.json")

TOL = 1e-6


def _carregar():
    with open(_FIXTURE, encoding="utf-8") as f:
        return json.load(f)


def test_fixture_existe_e_tem_casos():
    dados = _carregar()
    assert dados["casos"], "fixture sem casos"
    assert dados["arquitetura"] == [16, 32, 16, 2], dados["arquitetura"]


def test_inputs_reproduzem_o_fixture():
    dados = _carregar()
    rede = RedeNeural()
    rede.carregar(os.path.join(_RAIZ, CHECKPOINT))
    amb = _montar_ambiente()
    agente = Agente(rede, amb)

    for i, caso in enumerate(dados["casos"]):
        agente.reset_estado()
        agente.pos = pygame.Vector2(*caso["pos"])
        agente.vel = pygame.Vector2(*caso["vel"])
        agente.carregando = caso["carregando"]
        agente.tempo_vivo = caso["tempo_vivo"]

        obtido = agente.montar_inputs()
        np.testing.assert_allclose(
            obtido, np.asarray(caso["inputs"], dtype=np.float32),
            rtol=1e-5, atol=TOL,
            err_msg=f"inputs divergem no caso {i}",
        )

        saida = rede.forward(obtido)
        np.testing.assert_allclose(
            saida, np.asarray(caso["saida"], dtype=np.float32),
            rtol=1e-5, atol=TOL,
            err_msg=f"saida diverge no caso {i}",
        )


def test_invariantes_do_contrato():
    dados = _carregar()
    for i, caso in enumerate(dados["casos"]):
        e = caso["inputs"]
        assert len(e) == 16, f"caso {i}: esperava 16 entradas"
        assert len(caso["saida"]) == 2, f"caso {i}: esperava 2 saidas"

        norma_alvo = (e[0] ** 2 + e[1] ** 2) ** 0.5
        norma_ent = (e[4] ** 2 + e[5] ** 2) ** 0.5
        assert abs(norma_alvo - 1.0) < 1e-3, f"caso {i}: dir. alvo nao unitaria"
        assert abs(norma_ent - 1.0) < 1e-3, f"caso {i}: dir. entrega nao unitaria"

        assert 0.0 <= e[2] <= 1.0, f"caso {i}: dist normalizada fora de [0,1]"
        assert e[3] in (0.0, 1.0), f"caso {i}: flag carregando invalida"
        assert 0.0 <= e[6] <= 1.0, f"caso {i}: |v| fora de [0,1]"
        assert 0.0 <= e[7] <= 1.0, f"caso {i}: tempo normalizado fora de [0,1]"
        for j, r in enumerate(e[8:]):
            assert 0.0 <= r <= 1.0, f"caso {i}: raio {j} fora de [0,1]"


if __name__ == "__main__":
    test_fixture_existe_e_tem_casos()
    test_inputs_reproduzem_o_fixture()
    test_invariantes_do_contrato()
    print("OK")
