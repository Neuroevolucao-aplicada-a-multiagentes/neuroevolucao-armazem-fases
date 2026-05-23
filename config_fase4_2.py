"""Fase 4.2 — armazem real: 6 obstaculos espalhados, sem padrao.

Dimensao nova vs fase 4.1: sem garantia de obstaculo no caminho ideal.
Agora a rede precisa fazer o que um robo real faz: navegar em um armazem
com prateleiras distribuidas. Algumas rotas serao retas (sorte), outras
exigirao varios desvios encadeados.
"""
from simulador import CenarioConfig

CONFIG = CenarioConfig(
    nome="Fase 4.2 - armazem real",
    checkpoint_entrada="melhor_rede_fase4_1.npz",
    checkpoint_saida="melhor_rede_fase4_2.npz",

    num_agentes=40,
    duracao_geracao=42.0,
    num_geracoes=220,

    elite=5,
    taxa_mutacao=0.16,
    forca_mutacao=0.25,
    decaimento_mutacao=0.98,
    taxa_mutacao_min=0.05,
    forca_mutacao_min=0.06,

    usa_variacao_posicoes=True,
    usa_obstaculos=True,
    num_robos_moveis=0,

    obstaculos_fixos=[],
    num_obstaculos=0,
    num_obstaculos_extra_livres=6,
    obstaculos_no_caminho=False,
    offset_obstaculo_perpendicular=30,

    cenarios_por_geracao=4,
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
