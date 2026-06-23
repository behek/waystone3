import os, shutil, subprocess, sys
from datetime import datetime
from config.settings import BIRD_PROTOCOLS, BIRD_BACKUP_DIR, BIRDC_SOCKET, COMMUNITY_VENDOR, COMMUNITY_COUNTRY
from db.database import get_prefixes_by_list


def _backup(filepath):
    if not os.path.exists(filepath): return
    os.makedirs(BIRD_BACKUP_DIR, exist_ok=True)
    ts   = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = os.path.join(BIRD_BACKUP_DIR, os.path.basename(filepath) + '.' + ts)
    shutil.copy2(filepath, dest)
    pref = os.path.basename(filepath) + '.'
    for old in sorted(f for f in os.listdir(BIRD_BACKUP_DIR) if f.startswith(pref))[:-10]:
        os.unlink(os.path.join(BIRD_BACKUP_DIR, old))


def _comms(row):
    r = [(COMMUNITY_VENDOR, vc) for vc in row['vendor_communities']]
    if row['country_iso']: r.append((COMMUNITY_COUNTRY, row['country_iso']))
    return r


def _route(prefix, comms):
    adds = '; '.join(f'bgp_community.add(({a}, {v}))' for a, v in comms)
    return f'    route {prefix} reject {{ {adds}; }};'


def generate_list_conf(list_name, label, community):
    rows = get_prefixes_by_list(list_name)
    ts   = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = [
        f'# Auto-generated: {ts} | {label} | {COMMUNITY_VENDOR}:{community}',
        'protocol static {', '    ipv4;', '',
    ]
    for row in rows:
        c = _comms(row)
        if c: lines.append(_route(row['prefix'], c))
    lines.append('}')
    return '\n'.join(lines) + '\n'


def write_list_conf(list_name, label, community):
    fp = os.path.join(BIRD_PROTOCOLS, f'static_{list_name}.conf')
    _backup(fp)
    with open(fp, 'w') as f:
        f.write(generate_list_conf(list_name, label, community))
    print(f'[bird] written {fp}')
    return fp


def birdc_configure():
    try:
        r = subprocess.run(['birdc', '-s', BIRDC_SOCKET, 'configure'],
                           capture_output=True, text=True, timeout=30)
        out = r.stdout + r.stderr
        print(f'[bird] {out.strip()}')
        return 'econfigured' in out
    except Exception as e:
        print(f'[bird] error: {e}', file=sys.stderr)
        return False
