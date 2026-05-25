"""
Camada de Configuração - Carregamento e validação de credenciais Supabase
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv
from typing import Optional


@dataclass
class ConfigSupabase:
    """Configuração do Supabase validada"""
    url: str
    key: str
    
    def validar(self) -> bool:
        """Valida credenciais básicas"""
        if not self.url or not isinstance(self.url, str):
            raise ValueError("SUPABASE_URL inválido ou vazio")
        if not self.url.startswith("https://"):
            raise ValueError("SUPABASE_URL deve começar com https://")
        
        if not self.key or not isinstance(self.key, str):
            raise ValueError("SUPABASE_KEY inválido ou vazio")
        if len(self.key) < 20:
            raise ValueError("SUPABASE_KEY parece inválido (muito curto)")
        
        return True


class CarregadorConfigBD:
    """Carrega configuração do Supabase de .env"""
    
    def __init__(self, caminho_env: Optional[str] = None):
        """
        Inicializa carregador
        
        Args:
            caminho_env: Caminho para arquivo .env (default: procura na raiz)
        """
        self.caminho_env = caminho_env or ".env"
    
    def carregar(self) -> ConfigSupabase:
        """
        Carrega credenciais do .env
        
        Returns:
            ConfigSupabase: Configuração validada
            
        Raises:
            FileNotFoundError: Se .env não existe
            ValueError: Se credenciais inválidas
        """
        # Carregar .env
        load_dotenv(self.caminho_env)
        
        # Extrair credenciais
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        # Validar
        if not url or not key:
            raise ValueError(
                "Credenciais Supabase não encontradas em .env. "
                "Certifique-se que contém SUPABASE_URL e SUPABASE_KEY"
            )
        
        config = ConfigSupabase(url=url, key=key)
        config.validar()  # Validação adicional
        
        return config


def carregar_config_supabase(caminho_env: Optional[str] = None) -> ConfigSupabase:
    """
    Factory function para carregar config com tratamento de erros
    
    Args:
        caminho_env: Caminho para .env
        
    Returns:
        ConfigSupabase: Configuração do Supabase
        
    Raises:
        ValueError: Se credenciais inválidas
    """
    carregador = CarregadorConfigBD(caminho_env)
    return carregador.carregar()
