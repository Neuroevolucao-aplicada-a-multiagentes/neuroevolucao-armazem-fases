"""
Camada de Cliente - Singleton e lazy loading do cliente Supabase
"""

from typing import Optional
import logging

from .config import carregar_config_supabase, ConfigSupabase


logger = logging.getLogger(__name__)


class ClienteSupabase:
    """Cliente Supabase com lazy loading e singleton pattern"""
    
    _instancia: Optional['ClienteSupabase'] = None
    _cliente_interno = None
    
    def __new__(cls):
        """Implementa singleton pattern"""
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
        return cls._instancia
    
    def __init__(self):
        """Inicializa cliente Supabase (lazy loading no primeiro acesso)"""
        # Evitar reinicialização
        if hasattr(self, '_inicializado'):
            return
        
        self._config: Optional[ConfigSupabase] = None
        self._cliente_interno = None
        self._inicializado = True
    
    @property
    def config(self) -> ConfigSupabase:
        """Carrega config na primeira vez"""
        if self._config is None:
            self._config = carregar_config_supabase()
        return self._config
    
    @property
    def cliente(self):
        """Lazy load do cliente Supabase (na primeira vez)"""
        if self._cliente_interno is None:
            try:
                from supabase import create_client
                logger.info("Inicializando cliente Supabase...")
                self._cliente_interno = create_client(
                    self.config.url,
                    self.config.key
                )
                logger.info("✓ Cliente Supabase inicializado com sucesso")
            except ImportError:
                raise ImportError(
                    "Biblioteca 'supabase' não instalada. "
                    "Execute: pip install supabase"
                )
            except Exception as e:
                logger.error(f"Erro ao inicializar cliente Supabase: {e}")
                raise
        
        return self._cliente_interno
    
    def testar_conexao(self) -> bool:
        """
        Testa conectividade com o servidor Supabase
        
        Returns:
            bool: True se consegue comunicar com o servidor
        """
        try:
            # Tenta uma query simples
            response = self.cliente.table("experimentos").select("id").limit(1).execute()
            logger.info("✓ Conexão com Supabase validada")
            return True
        except Exception as e:
            erro_str = str(e)
            # Se recebemos erro de tabela (PGRST205), a conexão HTTP funcionou
            if "PGRST205" in erro_str or "Could not find the table" in erro_str:
                logger.info("✓ Conexão com Supabase validada (tabela não existe, mas servidor respondeu)")
                return True
            
            logger.error(f"✗ Erro ao testar conexão: {e}")
            return False
    
    def status(self) -> dict:
        """Retorna status da conexão"""
        try:
            conectado = self.testar_conexao()
            return {
                "conectado": conectado,
                "url": self.config.url,
                "servidor": "Supabase (PostgreSQL)",
            }
        except Exception as e:
            return {
                "conectado": False,
                "erro": str(e),
                "url": getattr(self.config, 'url', 'inválida'),
            }


# Singleton global
_cliente_global: Optional[ClienteSupabase] = None


def obter_cliente_supabase() -> ClienteSupabase:
    """
    Obtém instância única do cliente Supabase
    
    Returns:
        ClienteSupabase: Cliente singleton
    """
    global _cliente_global
    if _cliente_global is None:
        _cliente_global = ClienteSupabase()
    return _cliente_global


def resetar_cliente_supabase():
    """Reseta cliente (útil para testes)"""
    global _cliente_global
    _cliente_global = None
    ClienteSupabase._instancia = None
    ClienteSupabase._cliente_interno = None
