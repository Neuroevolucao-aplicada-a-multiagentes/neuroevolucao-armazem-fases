"""
Camada de Repositório - Abstrair queries, retry logic, error handling
"""

import logging
import time
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from .client import obter_cliente_supabase


logger = logging.getLogger(__name__)


class ErroSupabase(Exception):
    """Erro geral do Supabase"""
    pass


class ErroConexaoSupabase(ErroSupabase):
    """Erro de conexão com Supabase"""
    pass


class ErroTabelaNaoEncontrada(ErroSupabase):
    """Tabela não existe no Supabase"""
    pass


class TratadorErroSupabase:
    """Mapeia erros do Supabase para exceções claras"""
    
    @staticmethod
    def mapear_erro(erro: Exception) -> ErroSupabase:
        """
        Mapeia erro da API Supabase para tipo específico
        
        Args:
            erro: Exceção capturada
            
        Returns:
            ErroSupabase: Tipo específico de erro
        """
        erro_str = str(erro)
        
        if "PGRST205" in erro_str or "Could not find the table" in erro_str:
            return ErroTabelaNaoEncontrada(f"Tabela não encontrada: {erro}")
        
        if "connection" in erro_str.lower() or "timeout" in erro_str.lower():
            return ErroConexaoSupabase(f"Erro de conexão: {erro}")
        
        return ErroSupabase(f"Erro Supabase: {erro}")


class RepositorioSupabase:
    """Repositório genérico para operações CRUD com retry logic"""
    
    # Configuração de retry
    MAX_TENTATIVAS = 3
    ESPERA_INICIAL = 0.5  # segundos
    
    def __init__(self):
        """Inicializa repositório"""
        self.cliente = obter_cliente_supabase()
    
    def inserir(self, tabela: str, dados: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insere registro em tabela com retry
        
        Args:
            tabela: Nome da tabela
            dados: Dicionário com dados a inserir
            
        Returns:
            dict: Dados inseridos (com ID gerado)
            
        Raises:
            ErroSupabase: Se falha após tentativas
        """
        return self._executar_com_retry(
            lambda: self.cliente.cliente.table(tabela).insert(dados).execute(),
            tabela=tabela,
            operacao="insert"
        )
    
    def consultar(
        self, 
        tabela: str, 
        filtro: Optional[Dict[str, Any]] = None,
        limite: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Consulta registros em tabela
        
        Args:
            tabela: Nome da tabela
            filtro: Dicionário com filtros (ex: {"fase_id": 5})
            limite: Número máximo de registros
            
        Returns:
            list: Lista de registros
            
        Raises:
            ErroSupabase: Se falha
        """
        def fazer_query():
            query = self.cliente.cliente.table(tabela).select("*")
            
            if filtro:
                for chave, valor in filtro.items():
                    query = query.eq(chave, valor)
            
            return query.limit(limite).execute()
        
        return self._executar_com_retry(
            fazer_query,
            tabela=tabela,
            operacao="select"
        )
    
    def atualizar(self, tabela: str, id: int, dados: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza registro
        
        Args:
            tabela: Nome da tabela
            id: ID do registro
            dados: Dados a atualizar
            
        Returns:
            dict: Dados atualizados
            
        Raises:
            ErroSupabase: Se falha
        """
        return self._executar_com_retry(
            lambda: self.cliente.cliente.table(tabela).update(dados).eq("id", id).execute(),
            tabela=tabela,
            operacao="update",
            id=id
        )
    
    def deletar(self, tabela: str, id: int) -> bool:
        """
        Deleta registro
        
        Args:
            tabela: Nome da tabela
            id: ID do registro
            
        Returns:
            bool: True se sucesso
            
        Raises:
            ErroSupabase: Se falha
        """
        self._executar_com_retry(
            lambda: self.cliente.cliente.table(tabela).delete().eq("id", id).execute(),
            tabela=tabela,
            operacao="delete",
            id=id
        )
        return True
    
    def _executar_com_retry(
        self,
        funcao,
        tabela: str = "",
        operacao: str = "",
        **kwargs
    ) -> Any:
        """
        Executa função com retry automático
        
        Args:
            funcao: Função a executar
            tabela: Tabela para log
            operacao: Operação para log
            **kwargs: Argumentos para log
            
        Returns:
            Any: Resultado da função
            
        Raises:
            ErroSupabase: Se falha em todas as tentativas
        """
        ultima_excecao = None
        espera = self.ESPERA_INICIAL
        
        for tentativa in range(1, self.MAX_TENTATIVAS + 1):
            try:
                resultado = funcao()
                
                # Extrair dados da resposta
                if hasattr(resultado, 'data'):
                    dados = resultado.data
                    if isinstance(dados, list) and len(dados) > 0:
                        logger.debug(
                            f"✓ {operacao} em {tabela} bem-sucedido "
                            f"(tentativa {tentativa})"
                        )
                        return dados[0] if len(dados) == 1 else dados
                    elif isinstance(dados, list) and len(dados) == 0:
                        logger.debug(f"✓ {operacao} retornou vazio")
                        return []
                    else:
                        return dados
                
                return resultado
                
            except Exception as e:
                ultima_excecao = e
                erro_str = str(e)
                
                logger.warning(
                    f"⚠ Tentativa {tentativa}/{self.MAX_TENTATIVAS} "
                    f"falhou em {operacao} {tabela}: {erro_str}"
                )
                
                # Erros não recuperáveis
                if "PGRST205" in erro_str or "unauthorized" in erro_str.lower():
                    break
                
                # Esperar antes de retry (exponencial backoff)
                if tentativa < self.MAX_TENTATIVAS:
                    time.sleep(espera)
                    espera *= 2
        
        # Falha final
        if ultima_excecao:
            erro_mapped = TratadorErroSupabase.mapear_erro(ultima_excecao)
            logger.error(
                f"✗ Falha final em {operacao} {tabela} "
                f"após {self.MAX_TENTATIVAS} tentativas: {erro_mapped}"
            )
            raise erro_mapped
        
        raise ErroSupabase(f"Falha desconhecida em {operacao} {tabela}")
