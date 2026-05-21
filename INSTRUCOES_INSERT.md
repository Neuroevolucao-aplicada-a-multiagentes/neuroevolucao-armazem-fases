# 📝 Instruções para executar INSERT no Supabase

## ✅ Passo 1: Criar as tabelas no Supabase

1. Acesse **Supabase Dashboard** → SQL Editor
2. Clique em "New Query"
3. Cole este SQL script:

```sql
-- Tabela de experimentos
CREATE TABLE experimentos (
  id BIGSERIAL PRIMARY KEY,
  nome TEXT NOT NULL,
  descricao TEXT,
  data_inicio TIMESTAMPTZ DEFAULT now(),
  data_fim TIMESTAMPTZ,
  ambiente TEXT,
  metadados JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Tabela de fases
CREATE TABLE fases (
  id BIGSERIAL PRIMARY KEY,
  experimento_id BIGINT REFERENCES experimentos(id) ON DELETE CASCADE,
  numero_fase INT NOT NULL,
  timestamp_inicio TIMESTAMPTZ DEFAULT now(),
  timestamp_fim TIMESTAMPTZ,
  config JSONB NOT NULL,
  melhor_fitness_final FLOAT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Tabela de gerações (crítica para gráficos!)
CREATE TABLE geracoes (
  id BIGSERIAL PRIMARY KEY,
  fase_id BIGINT NOT NULL REFERENCES fases(id) ON DELETE CASCADE,
  numero_geracao INT NOT NULL,
  fitness_medio FLOAT NOT NULL,
  fitness_max FLOAT NOT NULL,
  fitness_min FLOAT NOT NULL,
  fitness_std FLOAT,
  agentes_chegaram INT,
  timestamp TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Índices para queries rápidas
CREATE INDEX idx_geracoes_fase_geracao ON geracoes(fase_id, numero_geracao);
CREATE INDEX idx_geracoes_timestamp ON geracoes(timestamp);
CREATE INDEX idx_fases_experimento ON fases(experimento_id);

-- Tabela de redes salvas (checkpoints)
CREATE TABLE redes_salvas (
  id BIGSERIAL PRIMARY KEY,
  geracao_id BIGINT REFERENCES geracoes(id) ON DELETE CASCADE,
  fase_id BIGINT NOT NULL REFERENCES fases(id),
  fitness FLOAT NOT NULL,
  arquivo_storage_path TEXT,
  timestamp TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);
```

4. Clique em "Run" (ou Ctrl+Enter)
5. Pronto! ✅ As tabelas foram criadas

## ✅ Passo 2: Testar o INSERT

Execute no terminal:

```bash
python test_insert_supabase.py
```

Você deve ver algo como:

```
============================================================
TESTE DE INSERT NO SUPABASE
============================================================

1️⃣ Verificando conexão...
✓ Conectado com sucesso!

2️⃣ Inserindo experimento de teste...

✅ Experimento 'Teste Inicial - Fase 1' registrado com sucesso!

📋 Dados Inseridos:
   • ID gerado: 1
   • Nome: Teste Inicial - Fase 1
   • Descrição: Experimento de teste para validar integração com Supabase
   • Ambiente: Simulação Pygame
   • Criado em: 2026-05-21T15:30:45.123456+00:00

🎉 Banco de dados está 100% funcional!
   Você pode ver o registro no Supabase Dashboard
```

## ✅ Passo 3: Validar no Dashboard

1. Acesse Supabase Dashboard
2. Vá para **Table Editor**
3. Selecione a tabela **"experimentos"**
4. Você verá o registro que foi inserido!

## 📊 Próximas etapas

Agora que tem conexão funcionando:

1. **Para a Fase 1 de Treinamento**: Expandir métodos para inserir métricas de gerações
2. **Para a Fase 2**: Guardar redes treinadas na tabela `redes_salvas`
3. **Para a Fase 3**: Integrar com o arquivo `metricas.py` para sincronizar automaticamente

A integração completa será feita quando a rede neural estiver pronta em outra branch.
