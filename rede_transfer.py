"""
Rede neural feedforward para controle de agente.

Decisoes de arquitetura (apos diagnostico):
- 2 camadas escondidas com tanh (estavel para neuroevolucao)
- SAIDA LINEAR (sem tanh) - permite qualquer direcao/magnitude
- Inicializacao Xavier (ganho 1.0) - evita saturar tanh no inicio
- Atenuacao moderada dos pesos para inputs de raycast (0.3) -
  raycasts ficam irrelevantes na fase 1 (sem obstaculos),
  mas precisam estar disponiveis para fases 3+
- Crossover por NEURONIO (coluna) - preserva funcionalidades aprendidas
- Clip de pesos para evitar explosao apos varias geracoes de mutacao
"""
import os
import numpy as np

INPUT_SIZE = 16
HIDDEN_SIZE_1 = 32
HIDDEN_SIZE_2 = 16
OUTPUT_SIZE = 2

WEIGHT_CLIP = 4.0


class RedeNeural:
    def __init__(self, input_size=INPUT_SIZE, hidden_1=HIDDEN_SIZE_1,
                 hidden_2=HIDDEN_SIZE_2, output_size=OUTPUT_SIZE):
        self.input_size = input_size
        self.hidden_1 = hidden_1
        self.hidden_2 = hidden_2
        self.output_size = output_size

        self.w1 = np.random.randn(input_size, hidden_1) * np.sqrt(1.0 / input_size)
        self.w2 = np.random.randn(hidden_1, hidden_2) * np.sqrt(1.0 / hidden_1)
        self.w3 = np.random.randn(hidden_2, output_size) * np.sqrt(1.0 / hidden_2)

        if input_size > 8:
            self.w1[8:, :] *= 0.3

        self.b1 = np.zeros(hidden_1)
        self.b2 = np.zeros(hidden_2)
        self.b3 = np.zeros(output_size)

    def forward(self, x):
        x = np.asarray(x, dtype=np.float32)
        h1 = np.tanh(x @ self.w1 + self.b1)
        h2 = np.tanh(h1 @ self.w2 + self.b2)
        return h2 @ self.w3 + self.b3

    def copy(self):
        nova = RedeNeural(self.input_size, self.hidden_1, self.hidden_2, self.output_size)
        nova.w1 = self.w1.copy()
        nova.w2 = self.w2.copy()
        nova.w3 = self.w3.copy()
        nova.b1 = self.b1.copy()
        nova.b2 = self.b2.copy()
        nova.b3 = self.b3.copy()
        return nova

    def crossover(self, outra):
        """Crossover por neuronio: cada coluna (neuronio inteiro) vem de um pai.
        O bias do neuronio acompanha sua coluna."""
        filho = self.copy()
        for w_attr, b_attr in [("w1", "b1"), ("w2", "b2"), ("w3", "b3")]:
            wa = getattr(self, w_attr)
            wb = getattr(outra, w_attr)
            ba = getattr(self, b_attr)
            bb = getattr(outra, b_attr)
            mask_col = np.random.rand(wa.shape[1]) > 0.5
            new_w = np.where(mask_col[np.newaxis, :], wa, wb)
            new_b = np.where(mask_col, ba, bb)
            setattr(filho, w_attr, new_w)
            setattr(filho, b_attr, new_b)
        return filho

    def mutate(self, rate=0.1, strength=0.2):
        for nome in ["w1", "w2", "w3", "b1", "b2", "b3"]:
            m = getattr(self, nome)
            mask = np.random.rand(*m.shape) < rate
            ruido = np.random.randn(*m.shape) * strength
            m[mask] += ruido[mask]
            np.clip(m, -WEIGHT_CLIP, WEIGHT_CLIP, out=m)

    def salvar(self, caminho):
        np.savez(
            caminho,
            w1=self.w1, w2=self.w2, w3=self.w3,
            b1=self.b1, b2=self.b2, b3=self.b3,
            meta=np.array([self.input_size, self.hidden_1, self.hidden_2, self.output_size]),
        )

    def carregar(self, caminho):
        dados = np.load(caminho)
        if "meta" in dados.files:
            meta = dados["meta"]
            self.input_size = int(meta[0])
            self.hidden_1 = int(meta[1])
            self.hidden_2 = int(meta[2])
            self.output_size = int(meta[3])
        self.w1 = dados["w1"]
        self.w2 = dados["w2"]
        self.w3 = dados["w3"]
        self.b1 = dados["b1"]
        self.b2 = dados["b2"]
        self.b3 = dados["b3"]


def carregar_rede_base(caminho, input_size=INPUT_SIZE):
    if caminho and os.path.exists(caminho):
        rede = RedeNeural(input_size=input_size)
        rede.carregar(caminho)
        if rede.input_size != input_size:
            print(f"[AVISO] checkpoint tem input_size={rede.input_size} mas configurado={input_size}. Iniciando do zero.")
            return None
        print(f"Rede carregada de {caminho} (inputs={rede.input_size})")
        return rede
    return None


def salvar_melhor(agentes, caminho):
    melhor = max(agentes, key=lambda a: a.fitness)
    melhor.brain.salvar(caminho)
    print(f"Melhor rede salva em {caminho} | fitness={melhor.fitness:.1f}")
