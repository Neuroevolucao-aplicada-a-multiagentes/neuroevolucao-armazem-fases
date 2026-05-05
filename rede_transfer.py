import os
import numpy as np

INPUT_SIZE = 10
HIDDEN_SIZE_1 = 24
HIDDEN_SIZE_2 = 12
OUTPUT_SIZE = 2


class RedeNeural:
    def __init__(self):
        self.w1 = np.random.randn(INPUT_SIZE, HIDDEN_SIZE_1) * np.sqrt(1 / INPUT_SIZE)
        self.w2 = np.random.randn(HIDDEN_SIZE_1, HIDDEN_SIZE_2) * np.sqrt(1 / HIDDEN_SIZE_1)
        self.w3 = np.random.randn(HIDDEN_SIZE_2, OUTPUT_SIZE) * np.sqrt(1 / HIDDEN_SIZE_2)

        self.b1 = np.zeros(HIDDEN_SIZE_1)
        self.b2 = np.zeros(HIDDEN_SIZE_2)
        self.b3 = np.zeros(OUTPUT_SIZE)

    def forward(self, x):
        x = np.array(x, dtype=float)

        h1 = np.tanh(x @ self.w1 + self.b1)
        h2 = np.tanh(h1 @ self.w2 + self.b2)
        saida = np.tanh(h2 @ self.w3 + self.b3)

        return saida

    def copy(self):
        nova = RedeNeural()

        nova.w1 = self.w1.copy()
        nova.w2 = self.w2.copy()
        nova.w3 = self.w3.copy()

        nova.b1 = self.b1.copy()
        nova.b2 = self.b2.copy()
        nova.b3 = self.b3.copy()

        return nova

    def crossover(self, outra):
        filho = self.copy()

        for attr in ["w1", "w2", "w3", "b1", "b2", "b3"]:
            a = getattr(self, attr)
            b = getattr(outra, attr)

            mask = np.random.rand(*a.shape) > 0.5
            setattr(filho, attr, np.where(mask, a, b))

        return filho

    def mutate(self, rate=0.1, strength=0.2):
        for m in [self.w1, self.w2, self.w3, self.b1, self.b2, self.b3]:
            mask = np.random.rand(*m.shape) < rate
            m += mask * np.random.randn(*m.shape) * strength

    def salvar(self, caminho):
        np.savez(
            caminho,
            w1=self.w1,
            w2=self.w2,
            w3=self.w3,
            b1=self.b1,
            b2=self.b2,
            b3=self.b3
        )

    def carregar(self, caminho):
        dados = np.load(caminho)

        self.w1 = dados["w1"]
        self.w2 = dados["w2"]
        self.w3 = dados["w3"]

        self.b1 = dados["b1"]
        self.b2 = dados["b2"]
        self.b3 = dados["b3"]


def carregar_rede_base(caminho):
    if caminho and os.path.exists(caminho):
        rede = RedeNeural()
        rede.carregar(caminho)
        print(f"Rede carregada de {caminho}")
        return rede

    return None


def salvar_melhor(agentes, caminho):
    melhor = max(agentes, key=lambda a: a.fitness)
    melhor.brain.salvar(caminho)
    print(f"Melhor rede salva em {caminho} | fitness={melhor.fitness:.1f}")