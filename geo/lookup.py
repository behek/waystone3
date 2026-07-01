import ipaddress, sys

try:
    import geoip2.database
    _reader = None
except ImportError:
    geoip2 = None
    _reader = None

try:
    import pycountry
    _A2N = {c.alpha_2: int(c.numeric) for c in pycountry.countries if c.numeric}
except ImportError:
    pycountry = None
    _A2N = {}

from config.settings import MMDB_PATH


def _reader_get():
    global _reader
    if geoip2 is None:
        return None
    if _reader is None:
        try:
            _reader = geoip2.database.Reader(MMDB_PATH)
        except Exception as e:
            print(f'[geo] mmdb error: {e}', file=sys.stderr)
    return _reader


def _host(prefix):
    return str(ipaddress.ip_network(prefix, strict=False).network_address)


def get_country_numeric(prefix):
    rd = _reader_get()
    if not rd:
        return None
    try:
        rec = rd.country(_host(prefix))
        iso2 = (rec.country.iso_code or '').upper()
        if not iso2:
            return None
        # Пробуем через pycountry
        if pycountry:
            c = pycountry.countries.get(alpha_2=iso2)
            if c and c.numeric:
                return int(c.numeric)
        # Fallback на встроенный словарь
        return _A2N.get(iso2)
    except Exception:
        return None
