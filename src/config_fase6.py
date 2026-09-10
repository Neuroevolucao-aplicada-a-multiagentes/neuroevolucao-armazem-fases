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

    # Refinar uma rede ja boa exige menos perturbacao que explorar do zero.
    # Com 0.25/0.30, 26 dos 30 individuos por geracao eram produto de
    # crossover + mutacao, e quando a selecao nao consegue distinguir os bons
    # isso vira passeio aleatorio ladeira abaixo - foi o que a sondagem de
    # 25 geracoes mostrou, com a entrega caindo de 70,6% para 30,8%.
    taxa_mutacao=0.12,
    forca_mutacao=0.15,

    usa_obstaculos=True,
    usa_layout_corredores=True,
    num_fileiras=2,
    espessura_fileira=60,
    largura_corredor_min=110,
    num_transversais=2,
    largura_transversal=120,

    num_robos_moveis=3,
    # Seis layouts FIXOS, os mesmos em todas as geracoes. Sorteando a cada
    # geracao a aptidao fica nao estacionaria e a selecao persegue sorteio de
    # cenario: medimos 18,8 pp de desvio na taxa de entrega entre geracoes
    # vizinhas, o que afogava qualquer sinal de melhora. Seis em vez de tres
    # tambem reduz o risco de sobreajuste a um layout especifico.
    cenarios_por_geracao=6,
    layouts_fixos=6,
    seed=42,

    peso_progresso=2.0,
    peso_alinhamento=0.01,
    # Zerar este termo foi o erro da primeira tentativa: era ele que dava
    # gradiente para quem NAO entregou. Sem ele, num cenario onde so ~30%
    # completam, os outros 70% pontuavam igual e a selecao virava ruido.
    # Restaurado a 800 (era 1500) e agora medido pela MELHOR aproximacao
    # alcancada, nao pela posicao final - o que preserva o gradiente sem
    # premiar terminar encostado na parede perto do alvo.
    bonus_proximidade_max=800.0,
    proximidade_por_melhor_aproximacao=True,
    penalidade_colisao=300.0,
    penalidade_colisao_continua=60.0,
    max_colisoes_morte=12,
)
