-- Script SQL para criar o schema no Supabase
-- Cole isso no Supabase: SQL Editor → New Query

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

-- Criar bucket para armazenar arquivos .npz
-- (Isso faz via UI do Supabase: Storage → New bucket → "redes-npz" → Public)

-- ✅ Schema criado com sucesso!
