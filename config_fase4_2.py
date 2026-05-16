from simulador import CenarioConfig

CONFIG = CenarioConfig(
    nome="Fase 4.2 - obstaculos aleatorios",
    checkpoint_entrada="melhor_rede_fase4_1.npz",
    checkpoint_saida="melhor_rede_fase4_2.npz",
    num_agentes=30,
    duracao_geracao=40.0,
    num_geracoes=200,
    elite=4,
    taxa_mutacao=0.25,
    forca_mutacao=0.35,
    usa_variacao_posicoes=True,
    usa_obstaculos=True,
    num_robos_moveis=0,
    obstaculos_fixos=[],
    cenarios_por_geracao=3,
    seed=42,
)
