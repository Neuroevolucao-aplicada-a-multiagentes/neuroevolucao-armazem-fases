alter table core.generation
    add constraint generation_id_run_unique unique (id, run_id);

alter table core.checkpoint
    drop constraint if exists checkpoint_generation_fk;

alter table core.checkpoint
    add constraint checkpoint_generation_run_fk
    foreign key (generation_id, run_id)
    references core.generation (id, run_id)
    on delete cascade;

drop index if exists core.idx_run_config_snapshot_run_id;
drop index if exists core.idx_generation_run_id;
drop index if exists core.idx_checkpoint_generation_id;
drop index if exists core.idx_individual_generation_id;
drop index if exists core.idx_individual_evaluation_individual_id;