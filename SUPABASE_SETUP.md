# Guia de Integração Supabase

## ✅ O que foi criado

Foram criados **3 arquivos** para testar a conexão com Supabase:

### 1. `.env` 
- Armazena as credenciais Supabase de forma segura
- Nunca faça commit deste arquivo!

### 2. `supabase_connector.py`
- Módulo de conexão com Supabase
- Responsabilidades:
  - Carregar credenciais do `.env`
  - Inicializar cliente Supabase (lazy loading)
  - Testar conexão com o banco
  - Retornar status de conectividade

### 3. `test_supabase_connection.py`
- Script de teste da conexão
- Execute com: `python test_supabase_connection.py`

## 🚀 Como usar

### Passo 1: Instalar dependências
```bash
pip install -r requirements.txt
```

### Passo 2: Testar a conexão
```bash
python test_supabase_connection.py
```

Você deve ver algo como:
```
============================================================
TESTE DE CONEXÃO COM SUPABASE
============================================================

Verificando status da conexão...

📋 Status:
  • Chave de autenticação carregada: Sim
  • URL Supabase: https://selmjlfcsihhcztaxcbj.supabase.co
  • Conectado ao banco: ✓ SIM

✓ Conexão estabelecida com sucesso!

✨ Supabase está pronto para integração.
```

## 📋 Próximas etapas (para quando a rede estiver pronta)

1. **Criar tabelas no Supabase**
   - Tabela de métricas por geração
   - Tabela de histórico de redes treinadas
   - Tabela de operações do robô

2. **Expandir `supabase_connector.py` com:**
   - Métodos para inserir métricas
   - Métodos para guardar histórico de redes
   - Métodos para queries e agregações

3. **Integrar com `metricas.py`**
   - Guardar registros de gerações no Supabase
   - Manter compatibilidade com CSV local

## 🔒 Boas práticas

- `.env` está incluído no `.gitignore` por padrão
- Credenciais nunca devem ser commitadas
- O arquivo `.env` é carregado automaticamente quando o módulo é importado

## 🐛 Troubleshooting

Se o teste falhar, verifique:
- Conexão com internet ativa
- Credenciais corretas no `.env`
- Projeto Supabase ativo
- Dependências instaladas: `pip install supabase python-dotenv`

## 📝 Notas de implementação

O módulo foi criado com simplicidade em mente. Apenas testa a conexão por enquanto.
Quando a rede neural estiver completa (outra branch), integrar persistência completa será simples:

```python
# Exemplo futuro (não implementado ainda)
conector = criar_conector_supabase()
conector.salvar_metrica_geracao(geracao=1, fitness=95.5, ...)
```
