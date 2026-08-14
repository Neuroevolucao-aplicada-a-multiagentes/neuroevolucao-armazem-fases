# Persistência de dados

## Visão geral

A persistência em Supabase é uma camada adicional ao treinamento. O fluxo local de arquivos continua ativo em paralelo: métricas em CSV, configuração em TXT, log textual, gráficos em PNG e checkpoints da rede em NPZ não foram substituídos pelo banco.

O caminho de escrita no banco é:

```text
Treinamento (treinar.py)
    → TrainingPersistenceService
        → Repositories
            → Supabase Data API
                → PostgreSQL
```

`treinar.py` controla o ciclo de vida do treinamento. `TrainingPersistenceService` traduz esse ciclo em operações de persistência e coordena repositories especializados. Cada repository acessa uma tabela do schema `core` por meio do cliente Python do Supabase e da Data API.

## Schemas

- `core`: persistência operacional do treinamento. Contém as tabelas `experiment`, `run`, `run_config_snapshot`, `generation`, `individual`, `individual_evaluation` e `checkpoint`.
- `mart`: reservado para a futura camada analítica, incluindo views e estruturas de consumo pelo Power BI. O schema já existe, mas ainda não possui views ou marts implementados.

## Migrations

As migrations existentes em `supabase/migrations/` devem ser aplicadas na ordem do prefixo numérico:

1. `20260727_0001_create_schemas.sql`
   - habilita a extensão `pgcrypto`, usada para geração de UUIDs no PostgreSQL;
   - cria os schemas `core` e `mart`;
   - cria a função `core.set_updated_at()`, utilizada pelos triggers de atualização.

2. `20260727_0002_create_core_tables.sql`
   - cria as sete tabelas operacionais do schema `core`;
   - define chaves primárias, relacionamentos, checks, unicidades e índices;
   - instala triggers de `updated_at` nas tabelas que possuem essa coluna;
   - estabelece deleção em cascata para entidades dependentes e `on delete set null` para referências opcionais de pais e de Individual em Checkpoint.

3. `20260727_0003_fix_checkpoint_integrity_and_indexes.sql`
   - adiciona a unicidade `generation (id, run_id)`;
   - substitui a FK simples de Checkpoint para Generation por uma FK composta de `(generation_id, run_id)` para `(generation.id, generation.run_id)`, garantindo que o Checkpoint e a Generation pertençam à mesma Run;
   - remove índices redundantes que já são cobertos por constraints de unicidade.

4. `20260727_0004_grant_permissions.sql`
   - concede ao papel `service_role` uso do schema `core` e privilégios sobre tabelas, rotinas e sequences existentes;
   - configura privilégios padrão equivalentes para objetos futuros criados no schema `core` pelo papel que executar a migration.

As migrations atuais não criam objetos analíticos em `mart`, não concedem acesso a `mart` e não definem policies de RLS para `anon` ou `authenticated`.

## Configuração e conexão com Supabase

A conexão exige duas variáveis de ambiente:

```dotenv
SUPABASE_URL=<url-do-projeto>
SUPABASE_KEY=<chave-do-backend>
```

Os valores podem estar no ambiente do processo ou em um arquivo `.env`, carregado por `python-dotenv`. Secrets e chaves reais não devem ser versionados nem incluídos nesta documentação. Como as permissões das migrations são concedidas a `service_role`, a credencial usada pelo backend precisa assumir esse papel; ela não deve ser exposta em cliente público.

`database.connection.get_supabase_client()` cria o `Client` apenas no primeiro acesso e reutiliza a instância em chamadas posteriores. A inicialização lazy é protegida por lock, e `reset_supabase_client()` existe para testes ou reinicialização controlada. Ausência de URL ou chave, ou falha na criação do cliente, resulta em `SupabaseConfigurationError`.

O schema `core` precisa estar — e está no ambiente utilizado pelo projeto — na lista de schemas expostos pela Supabase Data API. Os repositories selecionam esse schema explicitamente com `client.schema("core")`. O schema `mart` ainda não participa do fluxo de persistência.

## Repositories

Todos os repositories usam a Data API no schema `core`, aceitam injeção opcional de um `Client` e fornecem operações de criação, consulta, listagem, atualização e exclusão compatíveis com sua entidade.

| Repository | Tabela | Responsabilidade |
| --- | --- | --- |
| `ExperimentRepository` | `core.experiment` | Mantém a identificação e os metadados de um experimento; também consulta por nome. |
| `RunRepository` | `core.run` | Mantém execuções de um experimento, fase, seed, status, timestamps e métricas de resumo. |
| `RunConfigSnapshotRepository` | `core.run_config_snapshot` | Mantém um snapshot JSON de configuração por Run, com hash opcional. |
| `GenerationRepository` | `core.generation` | Mantém gerações, tamanho da população, timestamps, fitness agregados e métricas. |
| `IndividualRepository` | `core.individual` | Mantém indivíduos avaliados, fitness, genome, metadados e referências genealógicas opcionais. |
| `IndividualEvaluationRepository` | `core.individual_evaluation` | Mantém avaliações individuais indexadas, com cenário, fitness, sucesso e métricas; ainda não é chamado pelo treinamento. |
| `CheckpointRepository` | `core.checkpoint` | Mantém metadados e referências dos checkpoints, com consultas por Run e Generation. |

## TrainingPersistenceService

`TrainingPersistenceService` é a fronteira arquitetural entre o treinamento e a camada de acesso a dados. Ele recebe ou instancia os sete repositories e concentra as operações de ciclo de vida usadas pela aplicação:

- `start_experiment()`;
- `start_run()`;
- `save_run_config_snapshot()`;
- `start_generation()` e `finish_generation()`;
- `save_individual()`;
- `save_checkpoint()`;
- `complete_run()` e `fail_run()`.

O serviço normaliza a configuração para JSON no snapshot e, ao finalizar uma Generation, mapeia `fit_melhor`, `fit_medio`, `fit_pior` e, quando disponível, `fit_mediana` ou `median_fitness` para as colunas agregadas correspondentes. As demais validações e operações CRUD ficam nos repositories.

Embora o serviço receba e mantenha um `IndividualEvaluationRepository`, ainda não expõe uma operação de treinamento que grave avaliações individuais por cenário.

## Integração com o treinamento

O fluxo está integrado aos modos `headless` e `visual` de `treinar.py`. O lifecycle de uma execução concluída é:

```text
Experiment
    → Run (running)
        → RunConfigSnapshot
            → Generation criada
                → população avaliada
                → Individuals persistidos
                → melhor Individual identificado
                → Checkpoint persistido quando há melhora do melhor fitness global
                → Generation finalizada
        → Run (completed)
```

Para cada chamada de `treinar()`, um Experiment é criado com `status=running` e uma Run também é iniciada com `status=running`. Atualmente, o fluxo não atualiza automaticamente o Experiment para `completed` ou `failed`: o lifecycle operacional implementado e validado está concentrado na Run. Esse comportamento pode ser revisto futuramente caso um Experiment passe a agrupar múltiplas Runs.

A configuração usada é salva logo depois como `RunConfigSnapshot`. Cada Generation é criada antes da avaliação e finalizada depois da persistência da população, da verificação do melhor Individual e do registro local das métricas.

Ao concluir todas as gerações, a Run passa para `completed`, com `finished_at` e as métricas finais. Uma interrupção manual que impeça a conclusão no modo visual marca a Run como `failed`. Em uma exceção abortiva após a criação da Run, o bloco de tratamento também tenta marcá-la como `failed` e preserva a exceção original.

### Generation

Uma Generation é criada com:

- `generation_number` 1-based e único dentro da Run;
- `population_size` correspondente a `len(agentes)`;
- `started_at` no início e `finished_at` na finalização;
- `metrics` reais retornadas por `rodar_geracao()`/`resumir_geracao()` ou consolidadas por `_avaliar_em_cenarios()`.

Na finalização, `best_fitness`, `average_fitness` e `worst_fitness` recebem, respectivamente, `fit_melhor`, `fit_medio` e `fit_pior`. `median_fitness` somente recebe valor se as métricas trouxerem `fit_mediana` ou `median_fitness`; caso não exista cálculo real, permanece `NULL`.

### Individual

Depois da avaliação, todos os agentes da população são persistidos. `individual_index` é 1-based porque esse é o contrato do repository e do schema, e o loop usa `enumerate(..., start=1)`.

Cada registro recebe o fitness real do Agente, o genome serializado e metadados reais de estado: `coletou`, `entregou`, `morto`, `colisoes`, `tempo_vivo`, `tempo_entrega`, `distancia_percorrida` e `carregando`.

O fluxo atual não possui informação segura para materializar `parent_1_id`, `parent_2_id` ou `rank`, portanto esses campos permanecem `NULL`. `is_elite` não é calculado pelo treinamento; como a chamada não fornece esse argumento, o valor persistido segue o default `false` do serviço/repository, sem representar uma classificação de elite calculada.

### Genome

O campo JSON `genome` contém os pesos e biases reais da rede do Agente:

- matrizes `w1`, `w2` e `w3`;
- vetores `b1`, `b2` e `b3`;
- metadados estruturais em `meta`: `input_size`, `hidden_1`, `hidden_2` e `output_size`.

Os arrays NumPy são convertidos com `tolist()` para serialização JSON. Esse JSON permite representar o genome no registro do Individual, mas não substitui o checkpoint `.npz` salvo localmente.

### Checkpoint

Quando o melhor fitness da Generation supera o melhor fitness global da execução, a rede do melhor Agente é salva localmente em arquivo `.npz`. Em seguida, o banco recebe os metadados e a referência desse artefato:

- `checkpoint_type`: `best`;
- `run_id` e `generation_id`;
- `individual_id` do melhor Agente, associado depois que os Individuals foram persistidos;
- `storage_path` do arquivo local;
- `fitness` real do melhor Individual;
- `metrics` reais da Generation;
- `storage_bucket`: permanece `NULL`, pois ainda não existe upload para o Supabase Storage.

A FK composta `checkpoint (generation_id, run_id) → generation (id, run_id)` garante que a Generation informada pertence à mesma Run do Checkpoint. O schema também limita `checkpoint_type` a `best`, `elite` ou `manual` e impede duplicidade do mesmo tipo em uma Generation; a integração atual usa apenas `best`.

## Persistência local

O Supabase não substitui os artefatos existentes. O fluxo continua produzindo e mantendo localmente:

- CSV para histórico tabular de métricas;
- TXT para a configuração local da execução, além do log textual;
- PNG para gráficos;
- NPZ para checkpoints da rede neural.

O banco acrescenta rastreabilidade relacional, metadados consultáveis e genomes em JSON. O arquivo NPZ continua sendo a representação local usada pelo fluxo de checkpoint.

## Validação end-to-end

O fluxo foi validado com um treinamento real reduzido da Fase 1, em modo headless, com uma Generation, oito agentes, um cenário e duração reduzida. O resultado observado foi:

- Run finalizada com `status=completed`;
- uma Generation persistida;
- oito Individuals, com índices de 1 a 8, fitness real, genome JSON e metadados;
- um Checkpoint `best` associado à Run, à Generation e ao melhor Individual;
- consistência entre `generation.best_fitness`, o fitness do melhor Individual e `checkpoint.fitness`.

Nenhum identificador específico da execução de teste é necessário para reproduzir ou documentar essa validação.

## IndividualEvaluation

A tabela `core.individual_evaluation` e o `IndividualEvaluationRepository` existem, e o CRUD do repository está implementado. Entretanto, a integração automática com o treinamento ainda não foi feita.

O motivo é que o fluxo atual não materializa de forma confiável a granularidade indivíduo × cenário. `_avaliar_em_cenarios()` agrega fitness entre cenários e mantém resumos por Generation, mas não produz eventos individuais por cenário que possam ser ligados com segurança a cada Individual. Portanto, dados não devem ser inferidos ou inventados para preencher essa tabela.

## Próximos passos

- desenvolver a camada `mart`;
- criar views analíticas a partir de `core`;
- conectar a camada analítica ao Power BI;
- definir medidas e dashboards;
- evoluir a integração de `IndividualEvaluation` caso o simulador passe a expor explicitamente a granularidade indivíduo × cenário.
