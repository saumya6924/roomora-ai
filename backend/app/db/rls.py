"""Row-level security helpers for Supabase.

Why: Supabase exposes every table in the `public` schema through its auto-generated REST API, using
the public `anon` key. Our data is only ever read and written by the FastAPI backend (which connects
with the database owner credentials and bypasses RLS), so each table gets RLS switched ON with NO
policies for `anon` / `authenticated`: deny-all. The API keys then cannot read or change anything.

Rule for future migrations: any migration that creates a table must also call `enable_rls(...)`.
"""

from alembic import op

ENABLE_ALL_SQL = """
DO $$
DECLARE t record;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.tablename);
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
    REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON ALL TABLES IN SCHEMA public FROM authenticated;
    REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM authenticated;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM authenticated;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM authenticated;
  END IF;
END $$;
"""

DISABLE_ALL_SQL = """
DO $$
DECLARE t record;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', t.tablename);
  END LOOP;
END $$;
"""


def is_postgres() -> bool:
    return op.get_context().dialect.name == "postgresql"


def enable_rls_everywhere() -> None:
    if is_postgres():
        op.execute(ENABLE_ALL_SQL)


def disable_rls_everywhere() -> None:
    if is_postgres():
        op.execute(DISABLE_ALL_SQL)


def enable_rls(*tables: str) -> None:
    """For migrations that add tables later: lock the new tables down the same way."""
    if is_postgres():
        for table in tables:
            op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
