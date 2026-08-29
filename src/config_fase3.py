"""Fase 3 — coleta+entrega aleatorios com obstaculos POSICIONADOS NO CAMINHO.

Pacote e entrega aparecem em pontos aleatorios a cada cenario.
Obstaculos sao posicionados perto da linha start->pacote->entrega,
forcando o agente a aprender a desviar (nao consegue ir reto).
"""
from simulador import CenarioConfig

CONFIG = CenarioConfig(
    nome="Fase 3 - obstaculos no caminho",
    checkpoint_entrada="melhor_rede_fase2.npz",
    checkpoint_saida="melhor_rede_fase3.npz",

    num_agentes=40,
    duracao_geracao=30.0,
    num_geracoes=180,

    elite=5,
    taxa_mutacao=0.20,
    forca_mutacao=0.30,
    decaimento_mutacao=0.98,
    taxa_mutacao_min=0.05,
    forca_mutacao_min=0.06,

    usa_variacao_posicoes=True,
    usa_obstaculos=True,
    num_robos_moveis=0,

    obstaculos_fixos=[],
    num_obstaculos=2,
    obstaculos_no_caminho=True,
    offset_obstaculo_perpendicular=35,

    cenarios_por_geracao=3,
    seed=42,

    bonus_coleta=700.0,
    bonus_entrega=4000.0,
    bonus_tempo_factor=80.0,
    bonus_proximidade_max=0.0,
    peso_progresso=12.0,
    peso_alinhamento=0.10,
    peso_gradiente_inverso=0.3,
    penalidade_parado=0.05,
    penalidade_colisao=250.0,
    max_colisoes_morte=6,
    pool_selecao_fracao=0.5,
)
