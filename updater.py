#!/usr/bin/env python3
import argparse, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from config.settings import SOURCES
from db.database import (
    init_schema, get_list_id, upsert_prefixes, log_start, log_finish, log_error,
    mark_list_ok, mark_list_run, get_prefixes_without_geo, get_prefixes_for_geo_refresh,
    update_prefix_geo, cursor,
)
from sources.fetcher import fetch_list
from geo.lookup import get_country_numeric
from bird.generator import write_list_conf, write_combined_conf, birdc_configure
from notify.telegram import (
    send_update_stats, send_error, send_geo_refresh_done,
    send_bird_reload_ok, send_bird_reload_fail,
)


def update_list(name, dry_run=False):
    cfg = SOURCES.get(name)
    if not cfg:
        print(f'[updater] unknown: {name}', file=sys.stderr); return False
    try:
        lid = get_list_id(name)
    except ValueError as e:
        print(e, file=sys.stderr); return False

    mark_list_run(lid)
    log_id = log_start(lid)
    print(f'[updater] fetching {name} ...')
    try:
        prefixes = fetch_list(name, cfg)
        print(f'[updater] {name}: {len(prefixes)} prefixes')
    except Exception as e:
        log_error(log_id, e); send_error(name, e); return False

    if dry_run:
        print(f'[dry-run] {len(prefixes)} prefixes, skip write')
        log_error(log_id, 'dry-run'); return True

    try:
        stats = upsert_prefixes(lid, prefixes)
        log_finish(log_id, stats); mark_list_ok(lid)
        print(f'[updater] {name}: +{stats["added"]} -{stats["removed"]} total={stats["total"]}')
    except Exception as e:
        log_error(log_id, e); send_error(name, e); return False

    with cursor() as cur:
        cur.execute('SELECT label, community FROM bl_lists WHERE name=%s', (name,))
        row = cur.fetchone() or {}
    label = row.get('label', name)
    comm  = row.get('community', 0)

    send_update_stats(label, stats['total'], stats['added'], stats['removed'])
    _enrich_new()
    try:
        write_combined_conf()
    except Exception as e:
        print(f'[bird] {e}', file=sys.stderr)
    return True


def _enrich_new(batch=0):
    rows = get_prefixes_without_geo(limit=batch if batch > 0 else 999999)
    if not rows: return
    print(f'[geo] enriching {len(rows)} new prefixes')
    ok = 0
    for r in rows:
        iso = get_country_numeric(r['prefix'])
        if iso:
            update_prefix_geo(r['id'], iso)
            ok += 1
    print(f'[geo] enriched {ok}/{len(rows)}')


def geo_refresh_all():
    rows = get_prefixes_for_geo_refresh(50000)
    print(f'[geo] refresh: {len(rows)}')
    ok = fail = 0
    for r in rows:
        iso = get_country_numeric(r['prefix'])
        if iso:
            update_prefix_geo(r['id'], iso); ok += 1
        else:
            fail += 1
    send_geo_refresh_done(ok, fail)


def update_all(dry_run=False):
    res = {n: update_list(n, dry_run) for n in SOURCES}
    ok  = sum(res.values())
    print(f'[updater] {ok} ok, {len(res)-ok} failed')
    if not dry_run:
        if birdc_configure(): send_bird_reload_ok()
        else:                 send_bird_reload_fail()


def main():
    p = argparse.ArgumentParser(description='Bird prefix updater')
    p.add_argument('--list')
    p.add_argument('--geo-refresh', action='store_true')
    p.add_argument('--dry-run',     action='store_true')
    p.add_argument('--init-schema', action='store_true')
    p.add_argument('--regen-bird',  action='store_true')
    a = p.parse_args()

    if a.init_schema:
        init_schema(); return
    if a.geo_refresh:
        geo_refresh_all(); return
    if a.regen_bird:
        write_combined_conf()
        if birdc_configure(): send_bird_reload_ok()
        else:                 send_bird_reload_fail()
        return
    if a.list:
        sys.exit(0 if update_list(a.list, a.dry_run) else 1)
    else:
        update_all(a.dry_run)


if __name__ == '__main__':
    main()
