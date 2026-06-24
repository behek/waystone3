import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from config.settings import DB


def get_conn():
    return psycopg2.connect(**DB)


@contextmanager
def cursor():
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                yield cur
    finally:
        conn.close()


def init_schema():
    import os
    path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(path) as f:
        sql = f.read()
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
        print("[db] schema applied")
    finally:
        conn.close()


def get_list_id(name):
    with cursor() as cur:
        cur.execute("SELECT id FROM bl_lists WHERE name = %s", (name,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"List '{name}' not found")
        return row["id"]


def upsert_prefixes(list_id, new_prefixes):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT p.id, p.prefix::text
                    FROM bl_prefix_lists pl
                    JOIN bl_prefixes p ON p.id = pl.prefix_id
                    WHERE pl.list_id = %s
                """, (list_id,))
                current = {r["prefix"]: r["id"] for r in cur.fetchall()}
                to_add    = new_prefixes - set(current)
                to_remove = set(current) - new_prefixes
                for prefix in to_add:
                    cur.execute("""
                        INSERT INTO bl_prefixes (prefix) VALUES (%s::cidr)
                        ON CONFLICT (prefix) DO UPDATE SET prefix=EXCLUDED.prefix
                        RETURNING id
                    """, (prefix,))
                    pid = cur.fetchone()["id"]
                    cur.execute(
                        "INSERT INTO bl_prefix_lists (prefix_id,list_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                        (pid, list_id))
                if to_remove:
                    for p in to_remove:
                        cur.execute(
                            "DELETE FROM bl_prefix_lists WHERE prefix_id=%s AND list_id=%s",
                            (current[p], list_id))
                return {"total": len(new_prefixes), "added": len(to_add), "removed": len(to_remove)}
    finally:
        conn.close()


def get_prefixes_without_geo(limit=500):
    with cursor() as cur:
        cur.execute(
            "SELECT id, prefix::text FROM bl_prefixes WHERE country_iso IS NULL ORDER BY created_at LIMIT %s",
            (limit,))
        return list(cur.fetchall())


def get_prefixes_for_geo_refresh(limit=1000):
    with cursor() as cur:
        cur.execute("""
            SELECT id, prefix::text FROM bl_prefixes
            WHERE geo_checked_at IS NULL OR geo_checked_at < NOW() - INTERVAL '30 days'
            ORDER BY geo_checked_at NULLS FIRST LIMIT %s
        """, (limit,))
        return list(cur.fetchall())


def update_prefix_geo(prefix_id, country_iso):
    with cursor() as cur:
        cur.execute(
            "UPDATE bl_prefixes SET country_iso=%s, geo_checked_at=NOW() WHERE id=%s",
            (country_iso, prefix_id))


def get_prefixes_by_list(list_name):
    with cursor() as cur:
        cur.execute("""
            SELECT p.prefix::text, p.country_iso,
                   array_agg(DISTINCT l2.community ORDER BY l2.community) AS vendor_communities
            FROM bl_prefix_lists pl
            JOIN bl_lists l ON l.id=pl.list_id AND l.name=%s
            JOIN bl_prefixes p ON p.id=pl.prefix_id
            JOIN bl_prefix_lists pl2 ON pl2.prefix_id=p.id
            JOIN bl_lists l2 ON l2.id=pl2.list_id AND l2.enabled=TRUE
            GROUP BY p.prefix, p.country_iso ORDER BY p.prefix
        """, (list_name,))
        return list(cur.fetchall())


def log_start(list_id):
    with cursor() as cur:
        cur.execute(
            "INSERT INTO bl_update_log (list_id,status) VALUES (%s,'running') RETURNING id",
            (list_id,))
        return cur.fetchone()["id"]


def log_finish(log_id, stats):
    with cursor() as cur:
        cur.execute(
            "UPDATE bl_update_log SET finished_at=NOW(),status='ok',total=%s,added=%s,removed=%s WHERE id=%s",
            (stats["total"], stats["added"], stats["removed"], log_id))


def log_error(log_id, msg):
    with cursor() as cur:
        cur.execute(
            "UPDATE bl_update_log SET finished_at=NOW(),status='error',error_msg=%s WHERE id=%s",
            (str(msg), log_id))


def mark_list_ok(list_id):
    with cursor() as cur:
        cur.execute(
            "UPDATE bl_lists SET last_ok_at=NOW(),last_run_at=NOW() WHERE id=%s",
            (list_id,))


def mark_list_run(list_id):
    with cursor() as cur:
        cur.execute("UPDATE bl_lists SET last_run_at=NOW() WHERE id=%s", (list_id,))


def get_all_prefixes_with_lists() -> list:
    """Все префиксы с community и именами списков для генерации общего конфига."""
    with cursor() as cur:
        cur.execute("""
            SELECT
                p.prefix::text,
                p.country_iso,
                array_agg(DISTINCT l.community ORDER BY l.community) AS vendor_communities,
                array_agg(DISTINCT l.name ORDER BY l.name) AS list_names
            FROM bl_prefixes p
            JOIN bl_prefix_lists pl ON pl.prefix_id = p.id
            JOIN bl_lists l ON l.id = pl.list_id AND l.enabled = TRUE
            GROUP BY p.prefix, p.country_iso
            ORDER BY p.prefix
        """)
        return list(cur.fetchall())
