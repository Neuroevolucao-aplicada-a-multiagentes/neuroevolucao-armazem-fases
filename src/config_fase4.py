"""Fase 4 — manobras apertadas: 4 obstaculos no caminho com offset pequeno.

Dimensao nova vs fase 3: DENSIDADE de obstaculos e PRECISAO de manobra.
Mais obstaculos no caminho (4 contra 2) e offset menor (22 contra 35) —
o agente precisa fazer desvios mais agudos sem perder velocidade.
"""
from simulador import CenarioConfig

CONFIG = CenarioConfig(
    nome="Fase 4 - manobras apertadas",
    checkpoint_entrada="melhor_rede_fase3.npz",
    checkpoint_saida="melhor_rede_fase4.npz",

    num_agentes=40,
    duracao_geracao=35.0,
    num_geracoes=200,

    elite=5,
    taxa_mutacao=0.18,
    forca_mutacao=0.28,
    decaimento_mutacao=0.98,
    taxa_mutacao_min=0.05,
    forca_mutacao_min=0.06,

    usa_variacao_posicoes=True,
    usa_obstaculos=True,
    num_robos_moveis=0,

    obstaculos_fixos=[],
    num_obstaculos=4,
    num_obstaculos_extra_livres=0,
    obstaculos_no_caminho=True,
    offset_obstaculo_perpendicular=22,

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
    penalidade_colisao=280.0,
    max_colisoes_morte=6,
    pool_selecao_fracao=0.5,
)
