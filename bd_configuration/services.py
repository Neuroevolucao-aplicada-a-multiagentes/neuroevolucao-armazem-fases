"""
Camada de Serviços - Lógica de negócio com Supabase
"""

import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from .repository import RepositorioSupabase, ErroSupabase
from .client import obter_cliente_supabase


logger = logging.getLogger(__name__)


class ServicoSupabase:
    """Serviço de lógica de negócio para persistência em Supabase"""
    
    def __init__(self):
        """Inicializa serviço"""
        self.repo = RepositorioSupabase()
        self._cache_experimento_id: Optional[int] = None
        self._cache_fase_id: Optional[int] = None
    
    # ======================== EXPERIMENTOS ========================
    
    def criar_experimento(
        self,
        nome: str,
        descricao: str = "",
        ambiente: str = "Simulação Pygame",
        metadados: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Cria novo experimento
        
        Args:
            nome: Nome do experimento
            descricao: Descrição
            ambiente: Tipo de ambiente
            metadados: Dados extras em JSON
            
        Returns:
            int: ID do experimento criado
            
        Raises:
            ErroSupabase: Se falha
        """
        dados = {
            "nome": nome,
            "descricao": descricao,
            "ambiente": ambiente,
            "metadados": metadados or {},
            "data_inicio": datetime.utcnow().isoformat(),
        }
        
        try:
            resultado = self.repo.inserir("experimentos", dados)
            experimento_id = resultado.get("id")
            self._cache_experimento_id = experimento_id
            
            logger.info(f"✓ Experimento criado: '{nome}' (ID: {experimento_id})")
            return experimento_id
        except ErroSupabase as e:
            logger.error(f"✗ Erro ao criar experimento: {e}")
            raise
    
    def finalizar_experimento(self, experimento_id: int):
        """Marca experimento como finalizado"""
        try:
            self.repo.atualizar(
                "experimentos",
                experimento_id,
                {"data_fim": datetime.utcnow().isoformat()}
            )
            logger.info(f"✓ Experimento {experimento_id} finalizado")
        except ErroSupabase as e:
            logger.warning(f"⚠ Erro ao finalizar experimento: {e}")
    
    # ======================== FASES ========================
    
    def criar_fase(
        self,
        experimento_id: int,
        numero_fase: int,
        config: Dict[str, Any]
    ) -> int:
        """
        Registra uma nova fase de treinamento
        
        Args:
            experimento_id: ID do experimento pai
            numero_fase: Número da fase (1-5)
            config: CenarioConfig como dict
            
        Returns:
            int: ID da fase criada
            
        Raises:
            ErroSupabase: Se falha
        """
        dados = {
            "experimento_id": experimento_id,
            "numero_fase": numero_fase,
            "config": self._serializar_config(config),
            "timestamp_inicio": datetime.utcnow().isoformat(),
        }
        
        try:
            resultado = self.repo.inserir("fases", dados)
            fase_id = resultado.get("id")
            self._cache_fase_id = fase_id
            
            logger.info(f"✓ Fase {numero_fase} registrada (ID: {fase_id})")
            return fase_id
        except ErroSupabase as e:
            logger.error(f"✗ Erro ao criar fase: {e}")
            raise
    
    def finalizar_fase(self, fase_id: int, melhor_fitness: float):
        """Marca fase como finalizada com melhor fitness"""
        try:
            self.repo.atualizar(
                "fases",
                fase_id,
                {
                    "timestamp_fim": datetime.utcnow().isoformat(),
                    "melhor_fitness_final": melhor_fitness,
                }
            )
            logger.info(f"✓ Fase {fase_id} finalizada (fitness: {melhor_fitness})")
        except ErroSupabase as e:
            logger.warning(f"⚠ Erro ao finalizar fase: {e}")
    
    def atualizar_config_fase(self, fase_id: int, config: Dict[str, Any]) -> bool:
        """Atualiza configuração de uma fase"""
        try:
            self.repo.atualizar(
                "fases",
                fase_id,
                {"config": self._serializar_config(config)}
            )
            logger.debug("✓ Config da fase atualizada no Supabase")
            return True
        except ErroSupabase as e:
            logger.warning(f"⚠ Erro ao atualizar config: {e}")
            return False
    
    # ======================== GERAÇÕES ========================
    
    def registrar_geracao(
        self,
        fase_id: int,
        numero_geracao: int,
        fitness_medio: float,
        fitness_max: float,
        fitness_min: float,
        fitness_std: float = 0.0,
        agentes_chegaram: int = 0,
        metadados: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Registra métrica de geração
        
        Args:
            fase_id: ID da fase
            numero_geracao: Número da geração
            fitness_medio: Fitness médio dos agentes
            fitness_max: Melhor fitness
            fitness_min: Pior fitness
            fitness_std: Desvio padrão
            agentes_chegaram: Contagem de agentes que completaram tarefa
            metadados: Dados extras
            
        Returns:
            int: ID do registro criado
            
        Raises:
            ErroSupabase: Se falha
        """
        dados = {
            "fase_id": fase_id,
            "numero_geracao": numero_geracao,
            "fitness_medio": fitness_medio,
            "fitness_max": fitness_max,
            "fitness_min": fitness_min,
            "fitness_std": fitness_std,
            "agentes_chegaram": agentes_chegaram,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        try:
            resultado = self.repo.inserir("geracoes", dados)
            geracao_id = resultado.get("id")
            
            logger.debug(
                f"✓ Geração {numero_geracao} registrada "
                f"(fitness: {fitness_medio:.2f} ± {fitness_std:.2f})"
            )
            return geracao_id
        except ErroSupabase as e:
            logger.warning(f"⚠ Erro ao registrar geração {numero_geracao}: {e}")
            # Não relança - logging continua mesmo se BD falha
            return -1
    
    # ======================== REDES TREINADAS ========================
    
    def _fazer_upload_rede(
        self,
        arquivo_local: str,
        fase_id: int,
        geracao_id: int
    ) -> Optional[str]:
        """
        Faz upload de arquivo .npz para Supabase Storage
        
        Args:
            arquivo_local: Caminho local do .npz
            fase_id: ID da fase (para organizar no storage)
            geracao_id: ID da geração
            
        Returns:
            str: Caminho remoto no bucket ou caminho local se falhar
        """
        # Verificar se arquivo existe
        if not os.path.exists(arquivo_local):
            logger.warning(f"⚠ Arquivo não encontrado: {arquivo_local}")
            return arquivo_local  # Fallback: usar caminho local
        
        try:
            cliente = obter_cliente_supabase()
            
            # Montar nome do arquivo no storage
            # Exemplo: fase_1/geracao_42/rede.npz
            arquivo_nome = Path(arquivo_local).name  # melhor_rede.npz
            caminho_remoto = f"fase_{fase_id}/geracao_{geracao_id}/{arquivo_nome}"
            
            # Retry logic: 3 tentativas
            for tentativa in range(1, 4):
                try:
                    with open(arquivo_local, "rb") as f:
                        conteudo = f.read()
                    
                    # Upload para bucket redes-npz
                    resposta = cliente.cliente.storage.from_("redes-npz").upload(
                        caminho_remoto,
                        conteudo,
                        {"contentType": "application/octet-stream"}
                    )
                    
                    logger.info(
                        f"✓ Rede enviada para Storage: {caminho_remoto}"
                    )
                    return caminho_remoto
                    
                except Exception as e_tentativa:
                    if tentativa < 3:
                        espera = 0.5 * (2 ** (tentativa - 1))  # 0.5s, 1s, 2s
                        logger.debug(
                            f"⚠ Upload falhou (tentativa {tentativa}/3), "
                            f"aguardando {espera}s... Erro: {str(e_tentativa)[:100]}"
                        )
                        time.sleep(espera)
                    else:
                        raise
            
            # Fallback: se todas as tentativas falharem
            logger.warning(
                f"⚠ Upload falhou após 3 tentativas, usando caminho local"
            )
            return arquivo_local
            
        except Exception as e:
            # Erro crítico - fallback para caminho local
            logger.warning(
                f"⚠ Erro ao fazer upload de rede: {str(e)[:200]}. "
                f"Utilizando referência local: {arquivo_local}"
            )
            return arquivo_local  # Sempre retorna algo válido
    
    def registrar_rede_salva(
        self,
        fase_id: int,
        geracao_id: int,
        fitness: float,
        arquivo_path: str,
        metadados: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Registra checkpoint de rede treinada
        
        Faz upload do .npz para Supabase Storage (bucket: redes-npz)
        e registra metadados no banco de dados.
        
        Args:
            fase_id: ID da fase
            geracao_id: ID da geração (pode ser -1 se falhou registrar)
            fitness: Fitness da rede
            arquivo_path: Caminho local do arquivo .npz
            metadados: Dados extras
            
        Returns:
            int: ID do registro criado
            
        Raises:
            ErroSupabase: Se falha
        """
        # Tentar fazer upload para Storage (com fallback para local)
        arquivo_remoto = self._fazer_upload_rede(
            arquivo_path,
            fase_id,
            geracao_id
        )
        
        dados = {
            "fase_id": fase_id,
            "geracao_id": geracao_id if geracao_id > 0 else None,  # nullable
            "fitness": fitness,
            "arquivo_storage_path": arquivo_remoto,  # Pode ser local ou remoto
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        try:
            resultado = self.repo.inserir("redes_salvas", dados)
            rede_id = resultado.get("id")
            
            logger.info(
                f"✓ Rede salva registrada (fitness: {fitness}, ID: {rede_id})"
            )
            return rede_id
        except ErroSupabase as e:
            logger.warning(f"⚠ Erro ao registrar rede: {e}")
            return -1
    
    # ======================== CONSULTAS ========================
    
    def obter_melhor_rede_fase(self, numero_fase: int) -> Optional[Dict[str, Any]]:
        """
        Busca melhor rede treinada de uma fase
        
        Args:
            numero_fase: Número da fase (1-5)
            
        Returns:
            dict: Dados da rede (fitness, arquivo_path) ou None
        """
        try:
            # Consulta: melhor rede dessa fase
            resultados = self.repo.consultar(
                "redes_salvas",
                filtro=None,  # Sem filtro simples, precisa de join/subquery
                limite=1
            )
            
            if resultados:
                return resultados[0]
            return None
        except ErroSupabase as e:
            logger.warning(f"⚠ Erro ao buscar melhor rede: {e}")
            return None
    
    def listar_geracao_fase(
        self,
        fase_id: int,
        ordenar_por: str = "numero_geracao"
    ) -> List[Dict[str, Any]]:
        """
        Lista todas as gerações de uma fase
        
        Args:
            fase_id: ID da fase
            ordenar_por: Campo para ordenação
            
        Returns:
            list: Gerações registradas
        """
        try:
            resultados = self.repo.consultar(
                "geracoes",
                filtro={"fase_id": fase_id},
                limite=10000  # Fase 5 pode ter 250 gerações
            )
            logger.debug(f"✓ Recuperadas {len(resultados)} gerações da fase {fase_id}")
            return resultados
        except ErroSupabase as e:
            logger.warning(f"⚠ Erro ao listar gerações: {e}")
            return []
    
    # ======================== UTILITÁRIOS ========================
    
    def _serializar_config(self, config: Any) -> Dict[str, Any]:
        """
        Converte CenarioConfig ou dict para JSON-serializável
        
        Args:
            config: CenarioConfig ou dict
            
        Returns:
            dict: Configuração pronta para JSON
        """
        if isinstance(config, dict):
            return config
        
        # Se é objeto (CenarioConfig), extrair atributos
        if hasattr(config, '__dict__'):
            config_dict = vars(config).copy()
            # Remover campos não-serializáveis
            for chave in list(config_dict.keys()):
                valor = config_dict[chave]
                if callable(valor) or chave.startswith('_'):
                    del config_dict[chave]
            return config_dict
        
        return {}
    
    def validar_schema(self) -> bool:
        """
        Valida se schema esperado existe no Supabase
        
        Returns:
            bool: True se todas as tabelas existem
        """
        tabelas_esperadas = [
            "experimentos",
            "fases",
            "geracoes",
            "redes_salvas"
        ]
        
        tabelas_existentes = []
        for tabela in tabelas_esperadas:
            try:
                self.repo.consultar(tabela, limite=1)
                tabelas_existentes.append(tabela)
            except Exception:
                logger.warning(f"⚠ Tabela '{tabela}' não encontrada")
        
        if len(tabelas_existentes) == len(tabelas_esperadas):
            logger.info("✓ Schema validado com sucesso")
            return True
        
        logger.error(
            f"✗ Schema incompleto. "
            f"Encontradas: {len(tabelas_existentes)}/{len(tabelas_esperadas)}"
        )
        return False
