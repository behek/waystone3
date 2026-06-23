import os, re, subprocess, sys
import requests
from config.settings import BLACKLISTS_DIR, RKN_URL, RU_GOV_URL

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
    path = os.path.join(BLACKLISTS_DIR, 'lists', filename)
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
                out = _run([sys.executable, 'network_list_from_as.py', '-q', asn], BLACKLISTS_DIR)
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
    out = _run([sys.executable, 'network_list_from_netname.py', url], BLACKLISTS_DIR, timeout=300)
    return {l.strip() for l in out.splitlines()
            if l.strip() and not l.startswith('#') and _is_ipv4(l.strip())}


def fetch_list(name, cfg):
    t = cfg['type']
    if t == 'asn_file': return fetch_from_asn_file(name, cfg['file'])
    if t == 'url':      return fetch_rkn(cfg['url'])
    if t == 'netname':  return fetch_ru_gov(cfg['url'])
    raise ValueError(f'Unknown type: {t}')
