from simulador import CenarioConfig

CONFIG = CenarioConfig(
    nome="Fase 3 - 1 obstaculo",
    checkpoint_entrada="melhor_rede_fase2.npz",
    checkpoint_saida="melhor_rede_fase3.npz",
    num_agentes=30,
    duracao_geracao=30.0,
    num_geracoes=120,
    elite=4,
    taxa_mutacao=0.25,
    forca_mutacao=0.35,
    usa_variacao_posicoes=False,
    usa_obstaculos=True,
    num_robos_moveis=0,
    obstaculos_fixos=[(600, 310, 70, 120)],
    pacote_fixo=(500, 200),
    entrega_fixa=(750, 450),
    cenarios_por_geracao=1,
    seed=42,
)
