from simulador import CenarioConfig

CONFIG = CenarioConfig(
    nome="Fase 5 - armazem completo (robos moveis)",
    checkpoint_entrada="melhor_rede_fase4_2.npz",
    checkpoint_saida="melhor_rede_fase5.npz",
    num_agentes=30,
    duracao_geracao=45.0,
    num_geracoes=250,
    elite=4,
    taxa_mutacao=0.30,
    forca_mutacao=0.35,
    usa_variacao_posicoes=True,
    usa_obstaculos=True,
    num_robos_moveis=4,
    obstaculos_fixos=[],
    cenarios_por_geracao=3,
    seed=42,
    penalidade_colisao=300.0,
    max_colisoes_morte=4,
)
