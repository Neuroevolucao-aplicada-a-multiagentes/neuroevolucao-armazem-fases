"""
Módulo de conexão com Supabase - Integração inicial
Propósito: Apenas testar a conexão com o banco de dados
Posteriomente será expandido com inserts, updates, deletes quando a rede estiver completa
"""

import os
from typing import Optional
from dotenv import load_dotenv


class SupabaseConnector:
    """Conector simples para Supabase - apenas testa conexão"""
    
    def __init__(self):
        """Inicializa o conector carregando credenciais das variáveis de ambiente"""
        load_dotenv()
        
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self._client = None
        
        if not self.url or not self.key:
            raise ValueError(
                "Credenciais Supabase não encontradas. "
                "Certifique-se que .env contém SUPABASE_URL e SUPABASE_KEY"
            )
    
    @property
    def client(self):
        """Lazy loading do cliente Supabase"""
        if self._client is None:
            try:
                from supabase import create_client
                self._client = create_client(self.url, self.key)
            except ImportError:
                raise ImportError(
                    "Biblioteca 'supabase' não instalada. "
                    "Execute: pip install supabase"
                )
        return self._client
    
    def testar_conexao(self) -> bool:
        try:
            response = self.client.table("information_schema.tables").select("*").limit(1).execute()
            print("✓ Conexão com Supabase estabelecida com sucesso!")
            return True
        except Exception as e:
            error_str = str(e)
            if "PGRST205" in error_str or "Could not find the table" in error_str:
                print("✓ Conexão com Supabase estabelecida com sucesso!")
                return True
            print(f"✗ Erro ao conectar com Supabase: {e}")
            return False
    
    def verificar_status(self) -> dict:
        """
        Retorna informações sobre o status da conexão
        
        Returns:
            dict: Dicionário com informações de status
        """
        try:
            # Tenta conectar
            self.client
            return {
                "conectado": self.testar_conexao(),
                "url": self.url,
                "chave_carregada": bool(self.key),
            }
        except Exception as e:
            return {
                "conectado": False,
                "erro": str(e),
                "url": self.url,
                "chave_carregada": bool(self.key),
            }
    
    def registrar_experimento(self, nome: str, descricao: str = "", ambiente: str = "") -> dict:
        """
        Insere um novo experimento na tabela de experimentos
        
        Args:
            nome: Nome do experimento
            descricao: Descrição do experimento
            ambiente: Ambiente de execução
        
        Returns:
            dict: Dados do experimento inserido (com id gerado)
        """
        try:
            dados = {
                "nome": nome,
                "descricao": descricao,
                "ambiente": ambiente,
            }
            
            response = self.client.table("experimentos").insert(dados).execute()
            
            if response.data:
                return {
                    "sucesso": True,
                    "id": response.data[0]["id"],
                    "dados": response.data[0],
                    "mensagem": f"✓ Experimento '{nome}' registrado com sucesso!"
                }
            else:
                return {
                    "sucesso": False,
                    "erro": "Nenhum dado retornado",
                    "mensagem": "✗ Erro ao registrar experimento"
                }
        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "mensagem": f"✗ Erro ao registrar experimento: {e}"
            }


def criar_conector_supabase() -> Optional[SupabaseConnector]:
    """
    Factory function para criar conector Supabase
    
    Returns:
        Optional[SupabaseConnector]: Conector se credenciais estiverem disponíveis, None caso contrário
    """
    try:
        return SupabaseConnector()
    except ValueError as e:
        print(f"Aviso: {e}")
        return None
