"""
Banco de Dados - Módulo de Integração Supabase
Camada de abstração para persistência de experimentos, métricas e redes

Estrutura em camadas:
1. config.py - Carregamento e validação de credenciais
2. client.py - Singleton cliente Supabase (lazy load)
3. repository.py - Queries CRUD com retry logic
4. services.py - Lógica de negócio
"""

from .config import ConfigSupabase, CarregadorConfigBD, carregar_config_supabase
from .client import ClienteSupabase, obter_cliente_supabase, resetar_cliente_supabase
from .repository import (
    RepositorioSupabase,
    ErroSupabase,
    ErroConexaoSupabase,
    ErroTabelaNaoEncontrada,
    TratadorErroSupabase,
)
from .services import ServicoSupabase

__all__ = [
    # Config
    "ConfigSupabase",
    "CarregadorConfigBD",
    "carregar_config_supabase",
    # Client
    "ClienteSupabase",
    "obter_cliente_supabase",
    "resetar_cliente_supabase",
    # Repository
    "RepositorioSupabase",
    "ErroSupabase",
    "ErroConexaoSupabase",
    "ErroTabelaNaoEncontrada",
    "TratadorErroSupabase",
    # Services
    "ServicoSupabase",
]
