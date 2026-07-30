-- Permite que o backend acesse objetos do schema customizado.
grant usage on schema core to service_role;

-- Permissões sobre as tabelas já existentes.
grant all privileges on all tables in schema core to service_role;

-- Permissões sobre funções existentes no schema.
grant all privileges on all routines in schema core to service_role;

-- Mantido para compatibilidade caso sequences sejam adicionadas futuramente.
grant all privileges on all sequences in schema core to service_role;

-- Permissões automáticas para futuras tabelas criadas pelo papel
-- que executar esta migration, normalmente postgres no Supabase.
alter default privileges in schema core
grant all privileges on tables to service_role;

-- Permissões automáticas para futuras funções.
alter default privileges in schema core
grant all privileges on routines to service_role;

-- Permissões automáticas para futuras sequences.
alter default privileges in schema core
grant all privileges on sequences to service_role;