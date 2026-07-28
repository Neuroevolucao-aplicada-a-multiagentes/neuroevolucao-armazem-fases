create table if not exists core.experiment (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    description text,
    environment text,
    status text not null default 'draft',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint experiment_name_unique unique (name),
    constraint experiment_status_check check (status in ('draft', 'running', 'completed', 'failed', 'archived'))
);

create index if not exists idx_experiment_status on core.experiment (status);
create index if not exists idx_experiment_created_at on core.experiment (created_at);

drop trigger if exists experiment_set_updated_at on core.experiment;
create trigger experiment_set_updated_at
before update on core.experiment
for each row
execute function core.set_updated_at();

create table if not exists core.run (
    id uuid primary key default gen_random_uuid(),
    experiment_id uuid not null,
    phase_code text not null,
    run_label text,
    seed bigint,
    status text not null default 'pending',
    started_at timestamptz,
    finished_at timestamptz,
    summary_metrics jsonb not null default '{}'::jsonb,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint run_experiment_fk foreign key (experiment_id) references core.experiment (id) on delete cascade,
    constraint run_status_check check (status in ('pending', 'running', 'completed', 'failed', 'cancelled')),
    constraint run_time_check check (finished_at is null or started_at is null or finished_at >= started_at)
);

create index if not exists idx_run_experiment_id on core.run (experiment_id);
create index if not exists idx_run_phase_code on core.run (phase_code);
create index if not exists idx_run_status on core.run (status);
create index if not exists idx_run_created_at on core.run (created_at);

drop trigger if exists run_set_updated_at on core.run;
create trigger run_set_updated_at
before update on core.run
for each row
execute function core.set_updated_at();

create table if not exists core.run_config_snapshot (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null,
    config jsonb not null,
    config_hash text,
    created_at timestamptz not null default now(),
    constraint run_config_snapshot_run_fk foreign key (run_id) references core.run (id) on delete cascade,
    constraint run_config_snapshot_run_unique unique (run_id)
);

create index if not exists idx_run_config_snapshot_run_id on core.run_config_snapshot (run_id);
create index if not exists idx_run_config_snapshot_config_hash on core.run_config_snapshot (config_hash);

create table if not exists core.generation (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null,
    generation_number integer not null,
    population_size integer not null,
    best_fitness double precision,
    average_fitness double precision,
    worst_fitness double precision,
    median_fitness double precision,
    started_at timestamptz,
    finished_at timestamptz,
    metrics jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint generation_run_fk foreign key (run_id) references core.run (id) on delete cascade,
    constraint generation_number_check check (generation_number >= 1),
    constraint generation_population_size_check check (population_size >= 1),
    constraint generation_time_check check (finished_at is null or started_at is null or finished_at >= started_at),
    constraint generation_run_number_unique unique (run_id, generation_number)
);

create index if not exists idx_generation_run_id on core.generation (run_id);
create index if not exists idx_generation_generation_number on core.generation (generation_number);
create index if not exists idx_generation_created_at on core.generation (created_at);

drop trigger if exists generation_set_updated_at on core.generation;
create trigger generation_set_updated_at
before update on core.generation
for each row
execute function core.set_updated_at();

create table if not exists core.individual (
    id uuid primary key default gen_random_uuid(),
    generation_id uuid not null,
    individual_index integer not null,
    parent_1_id uuid,
    parent_2_id uuid,
    fitness double precision,
    rank integer,
    is_elite boolean not null default false,
    genome jsonb not null default '{}'::jsonb,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint individual_generation_fk foreign key (generation_id) references core.generation (id) on delete cascade,
    constraint individual_parent_1_fk foreign key (parent_1_id) references core.individual (id) on delete set null,
    constraint individual_parent_2_fk foreign key (parent_2_id) references core.individual (id) on delete set null,
    constraint individual_index_check check (individual_index >= 1),
    constraint individual_rank_check check (rank is null or rank >= 1),
    constraint individual_generation_index_unique unique (generation_id, individual_index)
);

create index if not exists idx_individual_generation_id on core.individual (generation_id);
create index if not exists idx_individual_fitness on core.individual (fitness desc);
create index if not exists idx_individual_rank on core.individual (rank);
create index if not exists idx_individual_created_at on core.individual (created_at);

drop trigger if exists individual_set_updated_at on core.individual;
create trigger individual_set_updated_at
before update on core.individual
for each row
execute function core.set_updated_at();

create table if not exists core.individual_evaluation (
    id uuid primary key default gen_random_uuid(),
    individual_id uuid not null,
    evaluation_index integer not null,
    scenario_label text,
    fitness double precision not null,
    success boolean not null default false,
    metrics jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    constraint individual_evaluation_individual_fk foreign key (individual_id) references core.individual (id) on delete cascade,
    constraint individual_evaluation_index_check check (evaluation_index >= 1),
    constraint individual_evaluation_unique unique (individual_id, evaluation_index)
);

create index if not exists idx_individual_evaluation_individual_id on core.individual_evaluation (individual_id);
create index if not exists idx_individual_evaluation_fitness on core.individual_evaluation (fitness desc);
create index if not exists idx_individual_evaluation_created_at on core.individual_evaluation (created_at);

create table if not exists core.checkpoint (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null,
    generation_id uuid not null,
    individual_id uuid,
    checkpoint_type text not null default 'best',
    storage_path text not null,
    storage_bucket text,
    fitness double precision,
    metrics jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint checkpoint_run_fk foreign key (run_id) references core.run (id) on delete cascade,
    constraint checkpoint_generation_fk foreign key (generation_id) references core.generation (id) on delete cascade,
    constraint checkpoint_individual_fk foreign key (individual_id) references core.individual (id) on delete set null,
    constraint checkpoint_type_check check (checkpoint_type in ('best', 'elite', 'manual')),
    constraint checkpoint_generation_type_unique unique (generation_id, checkpoint_type),
    constraint checkpoint_storage_path_unique unique (storage_path)
);

create index if not exists idx_checkpoint_run_id on core.checkpoint (run_id);
create index if not exists idx_checkpoint_generation_id on core.checkpoint (generation_id);
create index if not exists idx_checkpoint_individual_id on core.checkpoint (individual_id);
create index if not exists idx_checkpoint_created_at on core.checkpoint (created_at);

drop trigger if exists checkpoint_set_updated_at on core.checkpoint;
create trigger checkpoint_set_updated_at
before update on core.checkpoint
for each row
execute function core.set_updated_at();
