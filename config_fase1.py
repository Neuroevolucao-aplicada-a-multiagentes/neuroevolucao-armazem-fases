from simulador import CenarioConfig

CONFIG = CenarioConfig(
    nome="Fase 1 - alvo unico",
    checkpoint_entrada=None,
    checkpoint_saida="melhor_rede_fase1.npz",

    num_agentes=50,
    duracao_geracao=15.0,
    num_geracoes=150,

    elite=6,
    taxa_mutacao=0.15,
    forca_mutacao=0.25,
    decaimento_mutacao=0.985,
    taxa_mutacao_min=0.05,
    forca_mutacao_min=0.07,

    usa_variacao_posicoes=True,
    usa_obstaculos=False,
    num_robos_moveis=0,

    objetivo_simples=True,
    cenarios_por_geracao=3,
    seed=42,

    bonus_entrega=5000.0,
    bonus_tempo_factor=150.0,
    bonus_proximidade_max=400.0,
    peso_progresso=15.0,
    peso_alinhamento=0.10,
    penalidade_parado=0.15,
    pool_selecao_fracao=0.5,
)
