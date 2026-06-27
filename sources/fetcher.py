import os, re, subprocess, sys
import requests
from config.settings import LISTS_DIR, RKN_URL, RU_GOV_URL
from pylib.ip import convert_to_cidr

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AS_RE   = re.compile(r'\bAS\d+\b', re.IGNORECASE)
CIDR_RE = re.compile(r'^\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}$')


def _is_ipv4(p):
    return ':' not in p and bool(CIDR_RE.match(p))


def _run(args, cwd, timeout=120):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:500])
    return r.stdout


def fetch_from_asn_file(name, filename):
    path = os.path.join(LISTS_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f'Not found: {path}')
    prefixes = set()
    with open(path) as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    for line in lines:
        m = AS_RE.search(line)
        if m:
            asn = m.group(0).upper()
            try:
                out = _run([sys.executable, 'network_list_from_as.py', '-q', asn], _PROJECT_ROOT)
                prefixes.update(p.strip() for p in out.splitlines() if _is_ipv4(p.strip()))
            except Exception as e:
                print(f'  [warn] {asn}: {e}', file=sys.stderr)
        elif _is_ipv4(line):
            prefixes.add(line)
    return prefixes


def fetch_rkn(url=RKN_URL):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return {l.strip() for l in r.text.splitlines()
            if l.strip() and not l.startswith('#') and _is_ipv4(l.strip())}


def fetch_ru_gov(url=RU_GOV_URL):
    out = _run([sys.executable, 'network_list_from_netname.py', url], _PROJECT_ROOT, timeout=300)
    return {l.strip() for l in out.splitlines()
            if l.strip() and not l.startswith('#') and _is_ipv4(l.strip())}


def fetch_list(name, cfg):
    t = cfg['type']
    if t == 'asn_file': return fetch_from_asn_file(name, cfg['file'])
    if t == 'url':      return fetch_rkn(cfg['url'])
    if t == 'netname':  return fetch_ru_gov(cfg['url'])
    if t == 'netname_file': return fetch_ru_gov_local(cfg['file'])
    raise ValueError(f'Unknown type: {t}')


def fetch_ru_gov_local(filename):
    filepath = os.path.join(LISTS_DIR, filename)
    netnames = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line.startswith('netname:'):
                netnames.append(line.split(':', 1)[1].strip())

    print(f'  [ru_gov] {len(netnames)} netnames found', file=sys.stderr)
    prefixes = set()
    for netname in netnames:
        try:
            url = f'https://rest.db.ripe.net/search.json?query-string={netname}&flags=no-referenced'
            r = requests.get(url, timeout=15, headers={'Accept': 'application/json'})
            if r.status_code not in (200, 400):
                continue
            data = r.json()
            for obj in data.get('objects', {}).get('object', []):
                if obj.get('type') != 'inetnum':
                    continue
                pk = obj.get('primary-key', {}).get('attribute', [{}])[0].get('value', '')
                if ' - ' not in pk:
                    continue
                try:
                    for cidr in convert_to_cidr(pk):
                        if _is_ipv4(cidr):
                            prefixes.add(cidr)
                except Exception:
                    pass
        except Exception as e:
            print(f'  [ru_gov] {netname}: {e}', file=sys.stderr)

    return prefixes
