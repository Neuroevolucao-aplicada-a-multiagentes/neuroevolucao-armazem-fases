from simulador import CenarioConfig

CONFIG = CenarioConfig(
    nome="Fase 2 - coleta e entrega",
    checkpoint_entrada="melhor_rede_fase1.npz",
    checkpoint_saida="melhor_rede_fase2.npz",
    num_agentes=30,
    duracao_geracao=25.0,
    num_geracoes=100,
    elite=4,
    taxa_mutacao=0.20,
    forca_mutacao=0.30,
    usa_variacao_posicoes=True,
    usa_obstaculos=False,
    num_robos_moveis=0,
    cenarios_por_geracao=2,
    seed=42,
)
