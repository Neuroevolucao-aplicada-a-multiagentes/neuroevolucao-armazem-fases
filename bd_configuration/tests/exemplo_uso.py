"""
Exemplo: Usar ServicoSupabase com upload automático de redes para Storage

Execute com: python -m bd_configuration.tests.exemplo_uso
Ou: cd bd_configuration/tests && python exemplo_uso.py

Demonstra:
1. Criar experimento no BD
2. Criar fase no BD
3. Registrar redes com UPLOAD automático para Storage
4. Fallback graceful se upload falhar
"""

import os
import sys
from pathlib import Path

# Setup: Adicionar raiz do projeto ao path (2 níveis acima)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bd_configuration import ServicoSupabase
from config_fase1 import CONFIG


def exemplo_registro_com_upload():
    """Exemplo de uso do upload automático"""
    
    print("\n" + "="*70)
    print("📚 EXEMPLO: Upload Automático de Redes para Storage")
    print("="*70 + "\n")
    
    # ======================== 1. Criar Serviço ========================
    print("1️⃣ Inicializando serviço Supabase...")
    servico = ServicoSupabase()
    
    # ======================== 2. Criar Experimento ========================
    print("\n2️⃣ Criando experimento...")
    exp_id = servico.criar_experimento(
        nome="Demo - Upload de Redes",
        descricao="Demonstração de upload automático para bucket redes-npz",
        ambiente="Simulação Pygame"
    )
    print(f"   ✓ Experimento criado: ID {exp_id}")
    
    # ======================== 3. Criar Fase ========================
    print("\n3️⃣ Criando fase...")
    config_dict = {
        "nome": CONFIG.nome,
        "num_agentes": CONFIG.num_agentes,
        "num_geracoes": CONFIG.num_geracoes,
        "duracao_geracao": CONFIG.duracao_geracao,
        "taxa_mutacao": CONFIG.taxa_mutacao,
    }
    
    fase_id = servico.criar_fase(
        experimento_id=exp_id,
        numero_fase=1,
        config=config_dict
    )
    print(f"   ✓ Fase criada: ID {fase_id}")
    
    # ======================== 4. Registrar Rede com Upload ========================
    print("\n4️⃣ Registrando rede treinada (com upload automático)...")
    
    # Simular arquivo .npz existente
    arquivo_teste = "melhor_rede.npz"
    
    # Se arquivo não existe, criar um dummy para exemplo
    if not os.path.exists(arquivo_teste):
        print(f"   ⚠ Arquivo '{arquivo_teste}' não encontrado")
        print(f"   → Seria feito upload para: redes-npz/fase_1/geracao_1/{arquivo_teste}")
        print(f"   → Se upload falhar: fallback para caminho local")
        
        # Criar arquivo dummy
        import numpy as np
        np.savez(arquivo_teste, weights=np.array([1.0, 2.0, 3.0]))
        print(f"   ✓ Arquivo dummy criado: {arquivo_teste}")
    
    # Registrar rede (isso faz upload automático!)
    rede_id = servico.registrar_rede_salva(
        fase_id=fase_id,
        geracao_id=1,
        fitness=850.5,
        arquivo_path=arquivo_teste
    )
    print(f"   ✓ Rede registrada no BD: ID {rede_id}")
    
    if rede_id > 0:
        print("\n   📊 Estrutura no Supabase Storage:")
        print("      redes-npz/")
        print("      ├── fase_1/")
        print("      │   └── geracao_1/")
        print("      │       └── melhor_rede.npz ← Upload automático!")
        print("\n   📋 Metadados salvos em: redes_salvas table")
        print(f"      ├── id: {rede_id}")
        print(f"      ├── fase_id: {fase_id}")
        print(f"      ├── geracao_id: 1")
        print(f"      ├── fitness: 850.5")
        print(f"      └── arquivo_storage_path: fase_1/geracao_1/melhor_rede.npz")
    
    # ======================== 5. Finalizar Fase ========================
    print("\n5️⃣ Finalizando fase...")
    servico.finalizar_fase(fase_id, melhor_fitness=850.5)
    print(f"   ✓ Fase finalizada")
    
    # ======================== 6. Validar Schema ========================
    print("\n6️⃣ Validando schema do banco...")
    if servico.validar_schema():
        print("   ✓ Schema completo e válido")
    else:
        print("   ⚠ Schema incompleto (verifique se criou tabelas no Supabase)")
    
    print("\n" + "="*70)
    print("✅ EXEMPLO CONCLUÍDO!")
    print("="*70)
    print("\n📝 Próximos passos:")
    print("   1. Abrir Supabase Dashboard → Storage → redes-npz")
    print("   2. Verificar se arquivo foi enviado para fase_1/geracao_1/")
    print("   3. Abrir Supabase → SQL → SELECT * FROM redes_salvas")
    print("   4. Verificar se arquivo_storage_path contém caminho remoto\n")


def exemplo_fallback():
    """Exemplo de fallback quando Storage não está disponível"""
    
    print("\n" + "="*70)
    print("🛡️ EXEMPLO: Fallback Graceful")
    print("="*70 + "\n")
    
    print("""
Se Supabase Storage não estiver disponível:

1. Upload falha na tentativa 1 → aguarda 0.5s, tenta novamente
2. Upload falha na tentativa 2 → aguarda 1s, tenta novamente
3. Upload falha na tentativa 3 → usa caminho local como fallback

Resultado:
├── arquivo_storage_path: "/absolute/path/runs/.../melhor_rede.npz" (local)
├── BD: Continua registrando normalmente
├── CSV: Continua salvando localmente
└── Treinamento: NÃO É BLOQUEADO

✅ Graceful degradation: Sempre salva, com ou sem Storage disponível
    """)


if __name__ == "__main__":
    try:
        exemplo_registro_com_upload()
        exemplo_fallback()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        print("\n💡 Dica:")
        print("   • Certifique-se de que .env está configurado")
        print("   • Verifique credenciais SUPABASE_URL e SUPABASE_KEY")
        print("   • Confirm que bucket 'redes-npz' foi criado no Supabase")
        import traceback
        traceback.print_exc()
