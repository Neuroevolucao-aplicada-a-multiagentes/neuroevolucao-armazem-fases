import csv
import datetime
import os
import shutil
from dataclasses import asdict
from typing import Optional


COLUNAS = [
    "geracao",
    "fit_medio", "fit_melhor", "fit_pior", "fit_std",
    "coletas", "entregas", "colisoes", "mortos",
    "taxa_coleta", "taxa_entrega",
    "melhor_tempo", "tempo_medio_entrega",
    "distancia_media_entrega",
    "taxa_mutacao_atual", "forca_mutacao_atual",
    "tempo_real_geracao_seg",
]


class Logger:
    def __init__(self, fase_nome: str, raiz_runs: str = "runs"):
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        slug = fase_nome.replace(" ", "_").replace("/", "-")
        self.dir = os.path.join(raiz_runs, f"{slug}_{ts}")
        os.makedirs(self.dir, exist_ok=True)

        self.csv_path = os.path.join(self.dir, "metricas.csv")
        self.checkpoint_path = os.path.join(self.dir, "melhor_rede.npz")
        self.config_path = os.path.join(self.dir, "config.txt")
        self.log_path = os.path.join(self.dir, "treino.log")

        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(COLUNAS)

        print(f"[logger] run em {self.dir}")

    def salvar_config(self, cfg):
        try:
            d = asdict(cfg)
        except TypeError:
            d = {k: getattr(cfg, k) for k in dir(cfg) if not k.startswith("_")}
        with open(self.config_path, "w", encoding="utf-8") as f:
            for k, v in d.items():
                f.write(f"{k} = {v}\n")

    def registrar(self, geracao: int, metricas: dict, taxa_mut: float, forca_mut: float,
                  tempo_real: float, escrever_log: bool = True):
        linha = [
            geracao,
            metricas["fit_medio"], metricas["fit_melhor"], metricas["fit_pior"], metricas["fit_std"],
            metricas["coletas"], metricas["entregas"], metricas["colisoes"], metricas["mortos"],
            metricas["taxa_coleta"], metricas["taxa_entrega"],
            metricas["melhor_tempo"], metricas["tempo_medio_entrega"],
            metricas["distancia_media_entrega"],
            taxa_mut, forca_mut,
            tempo_real,
        ]
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(linha)

        if escrever_log:
            msg = (f"Ger {geracao:3d} | "
                   f"fit_med {metricas['fit_medio']:8.1f} | "
                   f"fit_melhor {metricas['fit_melhor']:8.1f} | "
                   f"col {metricas['coletas']:2d} | "
                   f"ent {metricas['entregas']:2d} | "
                   f"colis {metricas['colisoes']:3d} | "
                   f"melhor_t {metricas['melhor_tempo']:5.1f}s | "
                   f"dt {tempo_real:4.1f}s")
            print(msg)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")

    def caminho_checkpoint(self) -> str:
        return self.checkpoint_path

    def copiar_para(self, destino: str):
        if os.path.exists(self.checkpoint_path):
            shutil.copyfile(self.checkpoint_path, destino)
            print(f"[logger] checkpoint copiado para {destino}")
