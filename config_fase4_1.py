from simulador import CenarioConfig

CONFIG = CenarioConfig(
    nome="Fase 4.1 - obstaculos + posicoes variaveis",
    checkpoint_entrada="melhor_rede_fase4.npz",
    checkpoint_saida="melhor_rede_fase4_1.npz",
    num_agentes=30,
    duracao_geracao=35.0,
    num_geracoes=180,
    elite=4,
    taxa_mutacao=0.25,
    forca_mutacao=0.35,
    usa_variacao_posicoes=True,
    usa_obstaculos=True,
    num_robos_moveis=0,
    obstaculos_fixos=[
        (570, 285, 70, 120),
        (360, 330, 70, 120),
        (650, 120, 70, 110),
    ],
    cenarios_por_geracao=3,
    seed=42,
)
