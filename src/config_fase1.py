from simulador import CenarioConfig

CONFIG = CenarioConfig(
    nome="Fase 1 - alvo unico",
    checkpoint_entrada=None,
    checkpoint_saida="melhor_rede_fase1.npz",

    num_agentes=30,
    duracao_geracao=20.0,
    num_geracoes=120,

    elite=4,
    taxa_mutacao=0.20,
    forca_mutacao=0.30,
    decaimento_mutacao=0.97,
    taxa_mutacao_min=0.05,
    forca_mutacao_min=0.05,

    usa_variacao_posicoes=True,
    usa_obstaculos=False,
    num_robos_moveis=0,

    objetivo_simples=True,
    cenarios_por_geracao=4,
    seed=42,

    bonus_entrega=8000.0,
    bonus_tempo_factor=200.0,
    bonus_proximidade_max=0.0,
    peso_progresso=10.0,
    peso_alinhamento=0.15,
    peso_gradiente_inverso=0.5,
    penalidade_parado=0.05,
    pool_selecao_fracao=0.5,
)
