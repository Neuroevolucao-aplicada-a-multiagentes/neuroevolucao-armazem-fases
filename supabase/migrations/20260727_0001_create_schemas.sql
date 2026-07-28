create extension if not exists pgcrypto;

create schema if not exists core;
create schema if not exists mart;

create or replace function core.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;
