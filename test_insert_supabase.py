"""
Script de teste para fazer um INSERT simples no Supabase
Verifica se consegue inserir dados na tabela 'experimentos'
"""

import sys
from supabase_connector import criar_conector_supabase


def main():
    print("=" * 60)
    print("TESTE DE INSERT NO SUPABASE")
    print("=" * 60)
    print()
    
    # Criar conector
    conector = criar_conector_supabase()
    
    if conector is None:
        print("✗ Falha: Não foi possível criar o conector Supabase")
        return 1
    
    # Verificar conexão primeiro
    print("1️⃣ Verificando conexão...")
    status = conector.verificar_status()
    
    if not status.get("conectado"):
        print("✗ Não está conectado ao Supabase")
        print(f"  Erro: {status.get('erro', 'Desconhecido')}")
        return 1
    
    print("✓ Conectado com sucesso!\n")
    
    # Fazer insert
    print("2️⃣ Inserindo experimento de teste...")
    resultado = conector.registrar_experimento(
        nome="Teste Inicial - Fase 1",
        descricao="Experimento de teste para validar integração com Supabase",
        ambiente="Simulação Pygame"
    )
    
    print()
    
    if resultado["sucesso"]:
        print("✅ " + resultado["mensagem"])
        print(f"\n📋 Dados Inseridos:")
        print(f"   • ID gerado: {resultado['id']}")
        print(f"   • Nome: {resultado['dados']['nome']}")
        print(f"   • Descrição: {resultado['dados']['descricao']}")
        print(f"   • Ambiente: {resultado['dados']['ambiente']}")
        print(f"   • Criado em: {resultado['dados']['created_at']}")
        print()
        print("🎉 Banco de dados está 100% funcional!")
        print("   Você pode ver o registro no Supabase Dashboard")
        return 0
    else:
        print("❌ " + resultado["mensagem"])
        print(f"\n🔍 Detalhes do erro:")
        print(f"   {resultado['erro']}")
        print()
        print("💡 Checklist:")
        print("   1. Você criou a tabela 'experimentos' no Supabase? (SQL Script)")
        print("   2. Certifique-se que as credenciais em .env estão corretas")
        print("   3. Verifique as permissões do banco de dados")
        return 1


if __name__ == "__main__":
    sys.exit(main())
