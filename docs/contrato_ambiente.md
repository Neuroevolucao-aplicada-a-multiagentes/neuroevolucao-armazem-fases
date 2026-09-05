# Contrato do ambiente

Especificação do que **qualquer** ambiente precisa satisfazer para executar a
rede neuroevoluída deste projeto. Vale para o simulador de treino (`src/`), o
armazém 2D em Pygame e o armazém 3D em Godot.

Existe porque o projeto já quebrou três vezes por divergência silenciosa entre
ambientes: o encoder do modo de operação, o spawn de pacotes dentro de racks e
a borda do mapa contando como colisão. Nenhuma delas gerava erro — a rede
simplesmente operava fora da distribuição em que foi treinada.

O contrato é verificável: `tests/golden_vectors.json` fixa entradas e saídas de
referência, e `tests/test_golden_vectors.py` falha se a implementação divergir.

---

## 1. Arquitetura

MLP feedforward `16 → 32 (tanh) → 16 (tanh) → 2 (linear)`, ~1.100 parâmetros.
Pesos em `melhor_rede_faseN.npz` (`w1, w2, w3, b1, b2, b3` + `meta`).

```
h1 = tanh(x · w1 + b1)
h2 = tanh(h1 · w2 + b2)
saida = h2 · w3 + b3        # LINEAR, sem tanh
```

A saída **não** é limitada: magnitudes de 5 a 15 são normais. Ela representa
uma direção, não uma velocidade — quem consome é que normaliza (§4).

---

## 2. Vetor de entrada — 16 valores, nesta ordem

| # | Valor | Fórmula |
|---|---|---|
| 0 | dx até o alvo, unitário | `(alvo.x - pos.x) / (dist_alvo + 1e-6)` |
| 1 | dy até o alvo, unitário | `(alvo.y - pos.y) / (dist_alvo + 1e-6)` |
| 2 | distância ao alvo | `dist_alvo / DIAGONAL` |
| 3 | carregando | `1.0` ou `0.0` |
| 4 | dx até a entrega, unitário | `(entrega.x - pos.x) / (dist_ent + 1e-6)` |
| 5 | dy até a entrega, unitário | `(entrega.y - pos.y) / (dist_ent + 1e-6)` |
| 6 | módulo da velocidade | `|v|`, sempre ≤ 1 por construção (§4) |
| 7 | tempo do ciclo | `min(tempo / DURACAO_GERACAO, 1.0)`, com `DURACAO_GERACAO = 45` |
| 8–15 | 8 raycasts | `distancia / ALCANCE_RAY`, cada um em [0, 1] |

**Alvo** é o pacote quando não está carregando, e o ponto de entrega quando
está. Os índices 4–5 apontam **sempre** para a entrega, mesmo indo buscar o
pacote — é o sinal de antecipação de rota.

O `+ 1e-6` não é cosmético: evita divisão por zero quando o agente está
exatamente sobre o alvo.

### Erros que já aconteceram aqui

- Usar `dx / LARGURA` em vez da direção unitária. Mistura direção com distância
  e fica assimétrico entre x e y (900 vs 600). **Foi o bug crítico do
  `RoboOperacional`.**
- Fixar o índice 7 em `0.5` em vez do tempo real do ciclo.
- Normalizar o tempo pela duração do relógio do ambiente em vez dos 45 s da
  fase 5.

---

## 3. Raycasts

- **8 raios**, distribuídos uniformemente: `heading + (i / 8) * 2π`, com `i` de
  0 a 7. O raio 0 aponta para a frente.
- **Egocêntricos**, relativos ao `heading`, nunca aos eixos do mundo. É isso que
  torna a política invariante a rotação — "obstáculo à frente" gera a mesma
  entrada virado para qualquer lado.
- **Heading** = `atan2(vel.y, vel.x)` quando `|v| > 0,01`; senão, a direção até
  o alvo. Nunca indefinido.
- **Alcance** 220 px, o que equivale a ~20% da diagonal do mapa (1.081 px).
  Em outro mapa, preservar a **proporção**, não o valor absoluto.
- **Passo** de 6 px na marcha do raio (implementação por amostragem).
- Bloqueiam o raio: obstáculos estáticos, **outros agentes** (teste de raio) e
  a borda do mapa.
- Normalização: `distancia / 220`, sempre em [0, 1]. Sem obstrução, vale 1,0.

Em Godot, `RayCast3D` / `intersect_ray` substitui a marcha por amostragem — o
resultado é equivalente e mais barato, desde que a distância retornada tenha a
mesma semântica.

---

## 4. Saída e movimento

```
v = Vector(saida[0], saida[1])
if |v| > 1: v = normalizar(v)
deslocamento = v * VELOCIDADE * dt        # VELOCIDADE = 200 px/s
```

A normalização é o que garante o invariante do índice 6 (`|v| ≤ 1`).

Movimento é resolvido **por eixo separadamente**: tenta x, depois y. Se um eixo
colide, ele é bloqueado e o outro ainda pode avançar — é o que permite deslizar
ao longo de uma parede.

**Plano horizontal.** A rede decide um vetor 2D. Em 3D, isso é o plano X-Z do
Godot; altura, gravidade e apoio no chão ficam fora do controle da rede, e o
`heading` sai da velocidade projetada nesse plano, ignorando Y.

---

## 5. Semântica de borda

A posição é **limitada** (clamp) ao intervalo `[raio, dimensao - raio]`.
Encostar na borda **não** é colisão e **não** gera penalidade.

Tratar a borda como colisão foi uma divergência real do ambiente Pygame:
gerava eventos espúrios e deixava o agente preso contra a parede.

---

## 6. Geometria — os limites medidos

A rede foi treinada com obstáculos retangulares de 45–90 × 55–130 px num mapa
de 900 × 600. A densidade exata por fase:

| Fase | Obstáculos estáticos | Robôs móveis |
|---|---|---|
| 4.2 (`armazém real`) | 6 | 0 |
| **5 (checkpoint final)** | **3** | **4** |

Ou seja: o checkpoint em uso viu apenas **3 obstáculos estáticos** por cenário,
mais 4 robôs móveis. Os 6 vêm da fase 4.2, cujos pesos a fase 5 herdou. O
armazém do MVP, com 6 racks, está no limite superior dessa faixa — o dobro da
densidade estática da fase final. **É uma lacuna de distribuição a considerar
ao configurar a fase 6.**

Os valores abaixo foram **medidos**, não estimados (3 seeds, 120 s, 6 agentes).

| Regra | Valor | Por quê |
|---|---|---|
| Largura mínima de corredor | ≥ 105 px (~6,5× a largura do agente, que é 16 px) | Fendas de 30 px viraram armadilha: o raycast enxerga a passagem, o agente entra e encalha |
| Folga do alvo até o obstáculo | ≥ 55 px | Com 35 px o agente precisava chegar a 15 px do rack para coletar (raio 20) e raspava nele em toda coleta. 55 px rendeu 107 entregas contra 79; 75 px já piora, por jogar o alvo nas faixas de circulação |
| Densidade de obstáculos | 3 a 6 no mapa 900 × 600 | Faixa do treino (ver tabela acima). 12 racks degradaram o desempenho |
| Zona de entrega | ≥ 60 px de qualquer obstáculo | Um rack encostado na zona concentrava 36% de todas as colisões num ponto |
| Alcance do raio | ~20% da diagonal (220 de 1.082 px) | Preservar a proporção ao mudar a escala do mapa |

Ao portar para outra escala (metros no Godot em vez de pixels), o que importa
são as **razões** — tudo no vetor de entrada é normalizado. Manter constante a
relação entre tamanho do agente, largura de corredor, alcance do raio e
diagonal do mapa.

---

## 7. Regras da tarefa

| Evento | Critério |
|---|---|
| Coleta | `dist(agente, pacote) ≤ 20` |
| Entrega | `dist(agente, entrega) ≤ 35` (no Pygame, sobreposição com a zona) |
| Tempo do ciclo | zera a cada entrega |

O raio de coleta precisa bater com o do treino: com 15 px, a rede — que
aprendeu a passar a até 20 px — simplesmente não disparava a coleta.

---

## 8. Como validar uma implementação nova

1. Gerar o fixture: `python src/gerar_golden_vectors.py`
2. Reconstruir na implementação alvo o mundo descrito em `mundo` (obstáculos,
   robôs, pacote, entrega) e as `constantes`
3. Para cada caso, montar o vetor de 16 entradas e comparar com `inputs`
4. Passar pela rede e comparar com `saida`
5. Tolerância: `1e-5` relativa. Divergência maior significa contrato quebrado

Do lado Python, `tests/test_golden_vectors.py` já faz isso e verifica os
invariantes (direções unitárias, faixas [0,1], 16 entradas, 2 saídas).
Confirmado que ele detecta a regressão de trocar a direção unitária por
`dx / LARGURA`.
