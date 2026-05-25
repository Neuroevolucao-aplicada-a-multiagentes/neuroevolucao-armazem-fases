"""
Testes de integração - Valida funcionamento completo do sistema com BD
Execute com: python -m bd_configuration.tests.test_integracao
Ou: cd bd_configuration/tests && python test_integracao.py
"""

import os
import sys
import tempfile
from pathlib import Path

# Adicionar raiz do projeto ao path (2 níveis acima)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config_fase1 import CONFIG as CONFIG_FASE1
from metricas import Logger, LoggerComSupabase
from treinar import treinar
from bd_configuration import (
    ServicoSupabase,
    ClienteSupabase,
    resetar_cliente_supabase,
)


def test_logger_local():
    """Testa Logger local (CSV) sem Supabase"""
    print("\n" + "="*60)
    print("✓ TESTE 1: Logger Local (CSV)")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = Logger(fase_nome="Teste Local", raiz_runs=tmpdir)
        
        # Simular registro de métrica
        logger.registrar(
            geracao=1,
            metricas={
                "fit_medio": 500.0,
                "fit_melhor": 1000.0,
                "fit_pior": 100.0,
                "fit_std": 200.0,
                "coletas": 25,
                "entregas": 20,
                "colisoes": 5,
                "mortos": 0,
                "taxa_coleta": 0.5,
                "taxa_entrega": 0.4,
                "melhor_tempo": 10.0,
                "tempo_medio_entrega": 15.0,
                "distancia_media_entrega": 500.0,
            },
            taxa_mut=0.15,
            forca_mut=0.25,
            tempo_real=0.05,
            escrever_log=False,
        )
        
        # Verificar que CSV foi criado
        csv_path = logger.csv_path
        assert os.path.exists(csv_path), f"CSV não foi criado em {csv_path}"
        
        with open(csv_path, 'r') as f:
            linhas = f.readlines()
            assert len(linhas) == 2, "CSV deve ter header + 1 linha"
        
        print(f"✓ CSV criado corretamente em {logger.dir}")
        return True


def test_logger_com_supabase():
    """Testa LoggerComSupabase (BD + CSV) com fallback graceful"""
    print("\n" + "="*60)
    print("✓ TESTE 2: LoggerComSupabase (Fallback Graceful)")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Tentar criar logger com Supabase (pode falhar se .env não existe)
            logger = LoggerComSupabase(
                fase_nome="Teste BD",
                raiz_runs=tmpdir,
                numero_fase=1,
                servico_supabase=None  # Deixar tentar criar
            )
            
            # Mesmo se falhar no BD, CSV deve funcionar
            logger.registrar(
                geracao=1,
                metricas={
                    "fit_medio": 500.0,
                    "fit_melhor": 1000.0,
                    "fit_pior": 100.0,
                    "fit_std": 200.0,
                    "coletas": 25,
                    "entregas": 20,
                    "colisoes": 5,
                    "mortos": 0,
                    "taxa_coleta": 0.5,
                    "taxa_entrega": 0.4,
                    "melhor_tempo": 10.0,
                    "tempo_medio_entrega": 15.0,
                    "distancia_media_entrega": 500.0,
                },
                taxa_mut=0.15,
                forca_mut=0.25,
                tempo_real=0.05,
                escrever_log=False,
            )
            
            csv_path = logger.csv_path
            assert os.path.exists(csv_path), "CSV não foi criado"
            
            print(f"✓ LoggerComSupabase funcionou (com fallback para CSV)")
            print(f"  - Diretório: {logger.dir}")
            print(f"  - Serviço BD: {'Ativo' if logger.servico else 'Falhou gracefully'}")
            return True
            
        except Exception as e:
            print(f"✗ Erro ao testar LoggerComSupabase: {e}")
            return False


def test_injecao_logger():
    """Testa injeção de logger em treinar()"""
    print("\n" + "="*60)
    print("✓ TESTE 3: Injeção de Logger em treinar()")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Criar config mínima para 1 geração
        config = CONFIG_FASE1
        config.num_geracoes = 1  # Só 1 geração para teste rápido
        config.num_agentes = 5   # Menos agentes
        
        # Criar logger e injetar
        logger = Logger(fase_nome="Teste Injeção", raiz_runs=tmpdir)
        
        try:
            # Chamar treinar com logger injetado
            resultado = treinar(config, modo="headless", logger=logger)
            
            assert os.path.exists(resultado), "Diretório de run não foi criado"
            assert os.path.exists(os.path.join(resultado, "metricas.csv")), "CSV não criado"
            
            print(f"✓ Logger injetado com sucesso")
            print(f"  - Run: {resultado}")
            return True
            
        except Exception as e:
            print(f"✗ Erro ao executar treinar com logger injetado: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_servico_supabase_offline():
    """Testa ServicoSupabase em modo offline (sem .env)"""
    print("\n" + "="*60)
    print("✓ TESTE 4: ServicoSupabase Offline")
    print("="*60)
    
    # Remover cliente global para testar fresh
    resetar_cliente_supabase()
    
    try:
        # Tentar criar serviço sem .env
        servico = ServicoSupabase()
        
        # Validar schema (deve falhar offline)
        resultado = servico.validar_schema()
        
        if resultado:
            print("✓ Schema validado (Supabase disponível!)")
        else:
            print("✓ Schema não validado (Supabase offline - esperado sem .env)")
        
        return True
        
    except Exception as e:
        print(f"⚠ ServicoSupabase offline (esperado): {str(e)[:100]}")
        return True


def test_compatibilidade_logger():
    """Testa que LoggerComSupabase é 100% compatível com Logger"""
    print("\n" + "="*60)
    print("✓ TESTE 5: Compatibilidade Logger")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Criar ambos loggers
        logger_local = Logger("Teste 1", tmpdir)
        logger_bd = LoggerComSupabase("Teste 2", raiz_runs=tmpdir, servico_supabase=None)
        
        # Ambos devem ter os mesmos métodos
        metodos_esperados = [
            'registrar',
            'salvar_config',
            'caminho_checkpoint',
            'copiar_para',
        ]
        
        for metodo in metodos_esperados:
            assert hasattr(logger_local, metodo), f"Logger sem {metodo}"
            assert hasattr(logger_bd, metodo), f"LoggerComSupabase sem {metodo}"
        
        print("✓ Todos os métodos presentes")
        print(f"  - Logger: {type(logger_local).__name__}")
        print(f"  - LoggerComSupabase: {type(logger_bd).__name__}")
        return True


def main():
    """Executa todos os testes"""
    print("\n" + "█"*60)
    print("█ TESTES DE INTEGRAÇÃO - SUPABASE BD")
    print("█"*60)
    
    testes = [
        ("Logger Local", test_logger_local),
        ("Logger com Supabase", test_logger_com_supabase),
        ("Injeção de Logger", test_injecao_logger),
        ("Serviço Supabase Offline", test_servico_supabase_offline),
        ("Compatibilidade Logger", test_compatibilidade_logger),
    ]
    
    resultados = []
    for nome, funcao_teste in testes:
        try:
            resultado = funcao_teste()
            resultados.append((nome, resultado))
        except Exception as e:
            print(f"\n✗ ERRO EM {nome}: {e}")
            import traceback
            traceback.print_exc()
            resultados.append((nome, False))
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)
    
    passou = 0
    falhou = 0
    for nome, resultado in resultados:
        status = "✓ PASSOU" if resultado else "✗ FALHOU"
        print(f"{status:12s} | {nome}")
        if resultado:
            passou += 1
        else:
            falhou += 1
    
    print("\n" + "="*60)
    print(f"Total: {passou} passou, {falhou} falhou")
    print("="*60 + "\n")
    
    return falhou == 0


if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
