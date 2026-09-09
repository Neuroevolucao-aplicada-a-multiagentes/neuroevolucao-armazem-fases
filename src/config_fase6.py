from simulador import CenarioConfig

# Fase 6 - topologia de corredor.
#
# As fases 1 a 5 treinaram com retangulos ISOLADOS em espaco aberto. O
# armazem real tem paredes longas com aberturas, que e outra topologia:
# alcancar um alvo do outro lado de uma fileira exige AFASTAR-SE dele
# temporariamente para chegar ao corredor transversal.
#
# Tres termos da aptidao foram calibrados para campo aberto, onde distancia
# euclidiana e distancia real coincidem. Em corredor eles divergem e o
# criterio passa a premiar o comportamento errado:
#
#   peso_progresso        12.0 -> 2.0
#       Somava (dist_antes - dist_depois) a cada passo. Contornar aumenta a
#       distancia euclidiana no curto prazo, entao o shaping penalizava
#       exatamente a manobra correta. Mantido baixo, so para nao remover todo
#       o gradiente das primeiras geracoes.
#
#   bonus_proximidade_max 1500 -> 0
#       Premiava quem NAO entregou conforme a proximidade final. Num corredor,
#       quem fica grudado na parede mais proxima do alvo pontuava mais que
#       quem contorna corretamente sem terminar. Recompensava o modo de falha.
#
#   peso_alinhamento      0.05 -> 0.01
#       Mesma logica: premiava velocidade apontada para o alvo, o que penaliza
#       o desvio necessario.
#
# Duas mudancas de sobrevivencia:
#
#   max_colisoes_morte    4 -> 12
#       Com 4, o agente morre antes de ter chance de aprender a navegar entre
#       paredes, onde encostar e muito mais frequente que em campo aberto.
#
#   penalidade_colisao_continua  0 -> 60/s
#       Substitui a pressao que a morte precoce exercia: ficar preso passa a
#       custar por tempo, e nao so por evento. E o termo que da gradiente para
#       aprender a se desvencilhar.
#
#       O valor foi calibrado pelo balanco contra o bonus de entrega (2500):
#         2 s em contato ->  120 de custo, entrega ainda vale +2380
#        20 s em contato -> 1200 de custo, entrega ainda vale +1300
#        55 s em contato -> 3300 de custo, resultado liquido negativo
#       Com 120/s testado antes, 20 s de contato ja anulavam quase todo o
#       bonus, e a evolucao passava a preferir nao se mover a entregar.

CONFIG = CenarioConfig(
    nome="Fase 6 - corredores de armazem",
    checkpoint_entrada="melhor_rede_fase5.npz",
    checkpoint_saida="melhor_rede_fase6.npz",

    num_agentes=30,
    duracao_geracao=55.0,
    num_geracoes=250,
    elite=4,

    taxa_mutacao=0.25,
    forca_mutacao=0.30,

    usa_obstaculos=True,
    usa_layout_corredores=True,
    num_fileiras=2,
    espessura_fileira=60,
    largura_corredor_min=110,
    num_transversais=2,
    largura_transversal=120,

    num_robos_moveis=3,
    cenarios_por_geracao=3,
    seed=42,

    peso_progresso=2.0,
    peso_alinhamento=0.01,
    bonus_proximidade_max=0.0,
    penalidade_colisao=300.0,
    penalidade_colisao_continua=60.0,
    max_colisoes_morte=12,
)
