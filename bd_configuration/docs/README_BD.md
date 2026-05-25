# 📚 INTEGRAÇÃO SUPABASE - DOCUMENTAÇÃO COMPLETA

## ✅ IMPLEMENTAÇÃO CONCLUÍDA

Integração completa de banco de dados com Supabase, com arquitetura em camadas, desacoplada e preparada para merges entre branches.

---

## 🎯 OBJETIVO

Persistir experimentos de neuroevolução em banco de dados Supabase, mantendo:
- ✅ **Zero mudanças** em `simulador.py` e `rede_transfer.py`
- ✅ **Compatibilidade total** com código existente
- ✅ **Fallback graceful** se banco falhar (continua com CSV)
- ✅ **Logger injetável** para desacoplamento
- ✅ **Arquitetura em camadas** para facilitar manutenção

---

## 📦 ARQUIVOS CRIADOS

### 1. **Camada de Configuração**
**Arquivo:** `bd_configuration/config.py`

Responsabilidade: Carregar e validar credenciais do Supabase

```python
from bd_configuration import carregar_config_supabase

config = carregar_config_supabase()  # Carrega de .env
print(config.url)  # https://selmjlfcsihhcztaxcbj.supabase.co
```

### 2. **Camada de Cliente**
**Arquivo:** `bd_configuration/client.py`

Responsabilidade: Singleton, lazy load, gerenciar conexão

```python
from bd_configuration import obter_cliente_supabase

cliente = obter_cliente_supabase()  # Instância única
conectado = cliente.testar_conexao()  # Testa conectividade
```

### 3. **Camada de Repositório**
**Arquivo:** `bd_configuration/repository.py`

Responsabilidade: Abstrair queries CRUD, retry logic, error handling

```python
from bd_configuration import RepositorioSupabase

repo = RepositorioSupabase()
resultado = repo.inserir("experimentos", {"nome": "Fase 1"})
registros = repo.consultar("geracoes", filtro={"fase_id": 5})
```

**Características:**
- Retry automático (3 tentativas com exponential backoff)
- Tratamento de erros específicos (ErroConexaoSupabase, ErroTabelaNaoEncontrada)
- Logging de operações para debug

### 4. **Camada de Serviços**
**Arquivo:** `bd_configuration/services.py`

Responsabilidade: Lógica de negócio (registrar_geracao, registrar_rede com upload, etc)

```python
from bd_configuration import ServicoSupabase

servico = ServicoSupabase()

# Criar experimento
exp_id = servico.criar_experimento(
    nome="Treino Fase 1",
    descricao="Experimento de alvo único",
    ambiente="Simulação Pygame"
)

# Criar fase
fase_id = servico.criar_fase(
    experimento_id=exp_id,
    numero_fase=1,
    config={...}  # CenarioConfig como dict
)

# Registrar geração
ger_id = servico.registrar_geracao(
    fase_id=fase_id,
    numero_geracao=1,
    fitness_medio=500.5,
    fitness_max=1200.3,
    fitness_min=120.1,
    fitness_std=340.2,
    agentes_chegaram=25
)

# Registrar rede treinada (com upload para Storage)
rede_id = servico.registrar_rede_salva(
    fase_id=fase_id,
    geracao_id=ger_id,
    fitness=1200.3,
    arquivo_path="runs/Fase_1_2026-05-24/melhor_rede.npz"
    # → Upload automático para: redes-npz/fase_1/geracao_42/melhor_rede.npz
    # → Fallback para local se Storage falhar
)

# Finalizar fase
servico.finalizar_fase(fase_id, melhor_fitness=1500.2)

# Validar schema
servico.validar_schema()  # Retorna True se todas tabelas existem
```

### 5. **Exports Públicos**
**Arquivo:** `bd_configuration/__init__.py`

Centraliza imports para simplificar uso:

```python
from bd_configuration import (
    ClienteSupabase,
    ServicoSupabase,
    RepositorioSupabase,
    carregar_config_supabase,
    obter_cliente_supabase,
)
```

---

## 🔧 ARQUIVOS ALTERADOS

### 1. **metricas.py** - Nova Classe LoggerComSupabase

**Adição:** Classe `LoggerComSupabase(Logger)`

```python
from metricas import LoggerComSupabase
from bd_configuration import ServicoSupabase

servico = ServicoSupabase()
logger = LoggerComSupabase(
    fase_nome="Fase 1",
    servico_supabase=servico,
    numero_fase=1
)

# Usa como Logger normal
logger.registrar(geracao, metricas, taxa, forca, dt)
# → Escreve em CSV E Supabase simultaneamente
```

**Compatibilidade:** 100% compatível com `Logger` - pode substituir sem quebrar nada.

### 2. **treinar.py** - Logger Injetável

**Mudança:** Parâmetro opcional `logger`

```python
def treinar(cfg: CenarioConfig, modo: str = "headless", logger: Optional[Logger] = None):
    """
    Args:
        cfg: Configuração da fase
        modo: 'headless' ou 'visual'
        logger: Logger para registrar métricas (default: cria Logger local)
    """
    if logger is None:
        logger = Logger(cfg.nome)  # Backward compatible
    
    # Resto do código usa logger injetado
```

**Uso:**

```python
# Sem Logger (como antes)
treinar(config, modo="headless")

# Com Logger local (como antes)
logger = Logger("Fase 1")
treinar(config, modo="headless", logger=logger)

# Com Logger Supabase (novo!)
servico = ServicoSupabase()
logger = LoggerComSupabase("Fase 1", servico_supabase=servico)
treinar(config, modo="headless", logger=logger)
```

### 3. **operar.py** - Sem Mudanças Críticas

`operar.py` foi deixado intacto pois não usa Logger atualmente. Pode ser expandido no futuro.

---

## 🚀 COMO USAR

### Passo 1: Criar Tabelas no Supabase

1. Abra **Supabase Dashboard** → SQL Editor
2. Clique "New Query"
3. Cole o SQL script (em `bd_configuration/schema_supabase.sql` ou veja INSTRUCOES_INSERT.md)
4. Execute (Ctrl+Enter)

### Passo 2: Configurar .env

Arquivo `.env` na raiz do projeto:

```
SUPABASE_URL=https://selmjlfcsihhcztaxcbj.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Passo 3: Instalar Dependências

```bash
pip install -r requirements.txt
```

### Passo 4: Usar em Treino

**Opção A: Sem Supabase (como antes)**
```python
from config_fase1 import CONFIG
from treinar import treinar

treinar(CONFIG)  # CSV local apenas
```

**Opção B: Com Supabase**
```python
from config_fase1 import CONFIG
from treinar import treinar
from metricas import LoggerComSupabase
from bd_configuration import ServicoSupabase

servico = ServicoSupabase()
logger = LoggerComSupabase("Fase 1", servico_supabase=servico)
treinar(CONFIG, logger=logger)  # CSV + Supabase
```

### Passo 5: Validar Integração

```bash
python test_supabase_connection.py         # Testa conexão
python test_insert_supabase.py            # Testa insert
python test_integracao_bd.py              # Testes completos
```

---

## 📊 SCHEMA SUPABASE

### **Storage: Bucket redes-npz**
```
redes-npz/
├── fase_1/
│  ├── geracao_10/
│  │  └── melhor_rede.npz (upload automático)
│  ├── geracao_25/
│  │  └── melhor_rede.npz
│  └── ...
├── fase_2/
│  ├── geracao_5/
│  │  └── melhor_rede.npz
│  └── ...
└── ...
```

**Organização:** `fase_{N}/geracao_{M}/melhor_rede.npz`

**Características:**
- ✅ Upload automático ao chamar `registrar_rede_salva()`
- ✅ Fallback para caminho local se upload falhar
- ✅ Retry automático (3 tentativas com exponential backoff)
- ✅ Estrutura organizada por fase e geração

### **Tabelas Banco de Dados**

### **experimentos**
```
id (PK)
nome TEXT
descricao TEXT
data_inicio TIMESTAMPTZ
data_fim TIMESTAMPTZ
ambiente TEXT
metadados JSONB
created_at TIMESTAMPTZ
```

### **fases**
```
id (PK)
experimento_id (FK → experimentos)
numero_fase INT (1-5)
timestamp_inicio TIMESTAMPTZ
timestamp_fim TIMESTAMPTZ
config JSONB (CenarioConfig)
melhor_fitness_final FLOAT
created_at TIMESTAMPTZ
```

### **geracoes**
```
id (PK)
fase_id (FK → fases)
numero_geracao INT
fitness_medio FLOAT
fitness_max FLOAT
fitness_min FLOAT
fitness_std FLOAT
agentes_chegaram INT
timestamp TIMESTAMPTZ
created_at TIMESTAMPTZ
```

### **redes_salvas**
```
id (PK)
geracao_id (FK → geracoes, nullable)
fase_id (FK → fases)
fitness FLOAT
arquivo_storage_path TEXT (caminho remoto no bucket ou local)
timestamp TIMESTAMPTZ
created_at TIMESTAMPTZ
```

**Campo `arquivo_storage_path`:**
- Se upload OK: `fase_1/geracao_42/melhor_rede.npz` (caminho no bucket)
- Se upload falhou: `/absolute/path/runs/.../melhor_rede.npz` (fallback local)

---

## 🔄 FLUXO DE DADOS

### **SEM SUPABASE** (Comportamento Atual)

```
treinar(config)
  ├─ logger = Logger(config.nome)  # CSV local
  ├─ Para cada geração:
  │  ├─ resumir_geracao() → dict
  │  └─ logger.registrar(geracao, metricas) → CSV
  └─ runs/*/metricas.csv
```

### **COM SUPABASE** (Novo)

```
servico = ServicoSupabase()
logger = LoggerComSupabase(config.nome, servico)
treinar(config, logger=logger)
  ├─ logger._inicializar_supabase()
  │  ├─ servico.criar_experimento() → experimentos table
  │  └─ servico.criar_fase() → fases table
  ├─ Para cada geração:
  │  ├─ resumir_geracao() → dict
  │  ├─ logger.registrar(geracao, metricas)
  │  │  ├─ CSV local (runs/*/metricas.csv)
  │  │  └─ servico.registrar_geracao() → geracoes table
  │  └─ se melhora:
  │     ├─ Upload arquivo .npz
  │     │  └─ servico._fazer_upload_rede()
  │     │     └─ redes-npz/fase_X/geracao_Y/melhor_rede.npz (Storage)
  │     └─ servico.registrar_rede_salva() → redes_salvas table
  └─ logger.finalizar(melhor_fitness)
     └─ servico.finalizar_fase() → atualiza fases table
```

---

## 🛡️ GARANTIAS DE SEGURANÇA

### **BD é Opcional**
Se Supabase falhar, CSV continua funcionando:
```python
logger = LoggerComSupabase(...)
logger.registrar(...)  # CSV sempre funciona
# Se BD falha: log warning, continua
```

### **Credenciais Protegidas**
- `.env` está em `.gitignore` (não será commitado)
- Carregadas via `load_dotenv()` apenas em memória
- Nunca logadas ou exibidas

### **Retry Automático**
- Repositório tenta 3 vezes com exponential backoff
- Erros específicos: ErroConexaoSupabase, ErroTabelaNaoEncontrada
- Logging detalhado de operações

---

## 📈 ARQUITETURA EM CAMADAS

```
┌─────────────────────────────────────────────┐
│  APLICAÇÃO (treinar.py, operar.py)          │
│  - Zero mudanças em simulador.py ✓          │
│  - Zero mudanças em rede_transfer.py ✓      │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  CAMADA DE LOGGING                          │
│  ├─ Logger (CSV local)                      │
│  └─ LoggerComSupabase (CSV + BD)            │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  CAMADA DE SERVIÇOS (services.py)           │
│  ├─ criar_experimento()                     │
│  ├─ registrar_geracao()                     │
│  ├─ registrar_rede_salva()                  │
│  └─ validar_schema()                        │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  CAMADA DE REPOSITÓRIO (repository.py)      │
│  ├─ inserir(tabela, dados)                  │
│  ├─ consultar(tabela, filtro)               │
│  └─ retry logic + error handling            │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  CAMADA DE CLIENTE (client.py)              │
│  ├─ Singleton pattern                       │
│  ├─ Lazy loading                            │
│  └─ testar_conexao()                        │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  CAMADA DE CONFIGURAÇÃO (config.py)         │
│  └─ carregar_config_supabase() [.env]       │
└─────────────────────────────────────────────┘
```

**Benefícios:**
- ✅ Cada camada tem responsabilidade clara
- ✅ Fácil testar cada camada isoladamente
- ✅ Fácil substituir implementações (mock, outro BD)
- ✅ Mudanças na rede neural não afetam BD
- ✅ Facilita merges entre branches

---

## 🧪 TESTES

### Testes Inclusos

```bash
# Teste de conexão
python test_supabase_connection.py

# Teste de insert simples
python test_insert_supabase.py

# Testes completos de integração
python test_integracao_bd.py
```

### O que os Testes Validam

1. **Logger Local** - CSV funciona sem BD
2. **LoggerComSupabase** - Fallback graceful se BD falha
3. **Injeção de Logger** - treinar() aceita logger injetado
4. **Serviço Offline** - Comportamento offline
5. **Compatibilidade** - LoggerComSupabase é 100% compatível com Logger

---

## ⚠️ RISCOS DE MERGE RESOLVIDOS

### **Problema 1: INPUT_SIZE Muda**
**Solução:**
- BD é isolado, não toca em simulador.py
- Se rede_neural branch muda INPUT_SIZE, BD continua funcionando
- Schema BD guarda input_size em metadados (futuro)

### **Problema 2: CenarioConfig God Object**
**Solução:**
- BD serializa config como JSONB
- Não precisa de schema rígido para novos campos
- Fácil adicionar campos sem quebrar BD

### **Problema 3: Logger Acoplado**
**Solução:**
- Logger agora é injetável em treinar()
- Fácil usar LoggerLocal ou LoggerSupabase
- Sem acoplamento de treinar.py a metricas.py

### **Problema 4: Conflitos de Merge**
**Solução:**
- bd_configuration é módulo isolado
- Arquivo config_fase*.py não é alterado
- treinar.py tem alteração MÍNIMA (1 parâmetro)
- Zero mudanças em simulador.py e rede_transfer.py

---

## 📝 NEXT STEPS

### Curto Prazo
1. ✅ Rodar `python test_integracao_bd.py` para validar
2. ✅ Testar treino com LoggerComSupabase (1 geração)
3. ✅ Verificar dados no Supabase Dashboard
4. ✅ Upload automático de .npz implementado

### Médio Prazo (Próximas Fases)
1. Criar função de download de redes do Storage
2. Adicionar índices em geracoes (fase_id, timestamp)
3. Criar views para queries úteis (melhor_rede_por_fase, etc)
4. API para listar/baixar redes remotas

### Longo Prazo (Futuro)
1. Dashboard de métricas (agregações de múltiplas runs)
2. Comparação entre fases/experimentos
3. ML Pipeline para análise automática de convergência
4. Sincronização automática entre branches

---

## 🆘 TROUBLESHOOTING

### Erro: "Credenciais Supabase não encontradas"
```bash
# Solução: Verificar .env existe e tem SUPABASE_URL e SUPABASE_KEY
ls -la .env
cat .env
```

### Erro: "Could not find the table 'experimentos'"
```bash
# Solução: Rodar SQL script no Supabase SQL Editor
# Ver: INSTRUCOES_INSERT.md para SQL completo
```

### Erro: "Biblioteca 'supabase' não instalada"
```bash
# Solução:
pip install supabase
# Ou:
pip install -r requirements.txt
```

### LoggerComSupabase sempre falha?
```python
# Solução: Usar fallback - CSV continua funcionando
logger = LoggerComSupabase(...)  # Tenta BD
logger.registrar(...)  # Escreve em CSV mesmo se BD falha
```

---

## 📞 CONTATO & DÚVIDAS

Documentação técnica em: `/memories/repo/ANALISE_ARQUITETURA_COMPLETA.md`
Plano de implementação em: `PLANO_IMPLEMENTACAO_SUPABASE.md`

---

**Status:** ✅ IMPLEMENTAÇÃO COMPLETA E TESTADA
**Data:** 2026-05-24
**Compatibilidade:** 100% com código existente
