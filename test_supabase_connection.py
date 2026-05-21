"""
Script de teste para validar conexão com Supabase
Execute este arquivo para verificar se a configuração está correta
"""

import sys
from supabase_connector import criar_conector_supabase


def main():
    print("=" * 60)
    print("TESTE DE CONEXÃO COM SUPABASE")
    print("=" * 60)
    print()
    
    # Criar conector
    conector = criar_conector_supabase()
    
    if conector is None:
        print("✗ Falha: Não foi possível criar o conector Supabase")
        print("  Verifique se o arquivo .env existe e contém as credenciais")
        return 1
    
    # Verificar status
    print("Verificando status da conexão...")
    status = conector.verificar_status()
    
    print("\n📋 Status:")
    for chave, valor in status.items():
        if chave == "chave_carregada":
            print(f"  • Chave de autenticação carregada: {'Sim' if valor else 'Não'}")
        elif chave == "url":
            print(f"  • URL Supabase: {valor}")
        elif chave == "conectado":
            resultado = "✓ SIM" if valor else "✗ NÃO"
            print(f"  • Conectado ao banco: {resultado}")
        elif chave == "erro":
            print(f"  • Erro: {valor}")
    
    print()
    
    # Testar conexão
    if status.get("conectado"):
        print("✓ Conexão estabelecida com sucesso!")
        print("\n✨ Supabase está pronto para integração.")
        print("   Próximos passos:")
        print("   1. Criar tabelas no Supabase (schemas SQL)")
        print("   2. Implementar funções de insert/update")
        print("   3. Integrar com Logger e sistema de treinamento")
        return 0
    else:
        print("✗ Não foi possível conectar ao Supabase")
        print("\n🔍 Checklist de troubleshooting:")
        print("   1. Verifique se as credenciais em .env estão corretas")
        print("   2. Verifique sua conexão de internet")
        print("   3. Certifique-se de que o projeto Supabase está ativo")
        print("   4. Instale a biblioteca: pip install supabase")
        return 1


if __name__ == "__main__":
    sys.exit(main())
