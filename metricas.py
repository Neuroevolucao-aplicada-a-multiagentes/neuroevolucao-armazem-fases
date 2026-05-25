import csv
import datetime
import os
import shutil
import logging
from dataclasses import asdict
from typing import Optional

try:
    from bd_configuration import ServicoSupabase
    SUPABASE_DISPONIVEL = True
except ImportError:
    SUPABASE_DISPONIVEL = False

logger_local = logging.getLogger(__name__)


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


class LoggerComSupabase(Logger):
    """Logger que salva métricas em CSV local E Supabase simultaneamente"""
    
    def __init__(
        self,
        fase_nome: str,
        servico_supabase: Optional['ServicoSupabase'] = None,
        raiz_runs: str = "runs",
        numero_fase: int = 1,
        experimento_id: Optional[int] = None,
    ):
        """
        Inicializa logger com suporte a Supabase
        
        Args:
            fase_nome: Nome da fase (ex: "Fase 1 - alvo unico")
            servico_supabase: Instância de ServicoSupabase (se None, cria nova)
            raiz_runs: Diretório raiz para runs
            numero_fase: Número da fase (1-5)
            experimento_id: ID do experimento (se None, cria novo)
        """
        super().__init__(fase_nome, raiz_runs)
        
        self.numero_fase = numero_fase
        self.experimento_id = experimento_id
        self.fase_id: Optional[int] = None
        self.servico = servico_supabase
        
        # Inicializar Supabase se disponível e serviço não fornecido
        if SUPABASE_DISPONIVEL and self.servico is None:
            try:
                self.servico = ServicoSupabase()
                logger_local.info("✓ Serviço Supabase inicializado")
            except Exception as e:
                logger_local.warning(f"⚠ Não foi possível inicializar Supabase: {e}")
                self.servico = None
        
        # Criar experimento e fase se não existem
        if self.servico:
            self._inicializar_supabase(fase_nome)
    
    def _inicializar_supabase(self, fase_nome: str):
        """Cria experimento e fase no Supabase"""
        try:
            # Criar ou usar experimento existente
            if self.experimento_id is None:
                self.experimento_id = self.servico.criar_experimento(
                    nome=f"Treino - {fase_nome}",
                    descricao=f"Experimento de neuroevolução",
                    ambiente="Simulação Pygame"
                )
            
            # Criar fase
            self.fase_id = self.servico.criar_fase(
                experimento_id=self.experimento_id,
                numero_fase=self.numero_fase,
                config={}  # Config será atualizada em salvar_config()
            )
            
            logger_local.info(
                f"✓ Experimento ({self.experimento_id}) e "
                f"Fase ({self.fase_id}) criados no Supabase"
            )
        except Exception as e:
            logger_local.warning(
                f"⚠ Erro ao criar experimento/fase no Supabase: {e}. "
                f"Continuando com CSV local apenas."
            )
            self.servico = None
    
    def salvar_config(self, cfg):
        """Salva config em arquivo local (como Logger base) e em Supabase"""
        super().salvar_config(cfg)
        
        # Atualizar config no Supabase
        if self.servico and self.fase_id:
            self.servico.atualizar_config_fase(self.fase_id, cfg)
    
    def registrar(
        self,
        geracao: int,
        metricas: dict,
        taxa_mut: float,
        forca_mut: float,
        tempo_real: float,
        escrever_log: bool = True
    ):
        """Registra métrica em CSV local E Supabase"""
        # Registrar localmente (CSV)
        super().registrar(geracao, metricas, taxa_mut, forca_mut, tempo_real, escrever_log)
        
        # Registrar em Supabase
        if self.servico and self.fase_id:
            try:
                self.servico.registrar_geracao(
                    fase_id=self.fase_id,
                    numero_geracao=geracao,
                    fitness_medio=float(metricas.get("fit_medio", 0)),
                    fitness_max=float(metricas.get("fit_melhor", 0)),
                    fitness_min=float(metricas.get("fit_pior", 0)),
                    fitness_std=float(metricas.get("fit_std", 0)),
                    agentes_chegaram=int(metricas.get("entregas", 0)),
                    metadados={
                        "taxa_mutacao": taxa_mut,
                        "forca_mutacao": forca_mut,
                        "tempo_real_seg": tempo_real,
                    }
                )
            except Exception as e:
                logger_local.debug(
                    f"⚠ Erro ao registrar geração {geracao} em Supabase: {e}. "
                    f"CSV local continua funcionando."
                )
    
    def finalizar(self, melhor_fitness: float):
        """Marca fase como finalizada no Supabase"""
        if self.servico and self.fase_id:
            try:
                self.servico.finalizar_fase(self.fase_id, melhor_fitness)
                logger_local.info(f"✓ Fase finalizada no Supabase")
            except Exception as e:
                logger_local.warning(f"⚠ Erro ao finalizar fase em Supabase: {e}")
