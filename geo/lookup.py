import ipaddress, sys

try:
    import geoip2.database
    _reader = None
except ImportError:
    geoip2 = None
    _reader = None

from config.settings import MMDB_PATH

_A2N = {
    'AF':4,'AL':8,'DZ':12,'AD':20,'AO':24,'AR':32,'AM':51,'AU':36,'AT':40,'AZ':31,
    'BS':44,'BH':48,'BD':50,'BE':56,'BY':112,'BR':76,'BG':100,'CA':124,'CN':156,
    'CO':170,'HR':191,'CU':192,'CY':196,'CZ':203,'DK':208,'EG':818,'EE':233,
    'FI':246,'FR':250,'GE':268,'DE':276,'GH':288,'GR':300,'HK':344,'HU':348,
    'IN':356,'ID':360,'IR':364,'IQ':368,'IE':372,'IL':376,'IT':380,'JP':392,
    'JO':400,'KZ':398,'KE':404,'KP':408,'KR':410,'KW':414,'LV':428,'LB':422,
    'LY':434,'LT':440,'LU':442,'MY':458,'MT':470,'MX':484,'MD':498,'MN':496,
    'ME':499,'MA':504,'MM':104,'NL':528,'NZ':554,'NG':566,'NO':578,'OM':512,
    'PK':586,'PA':591,'PE':604,'PH':608,'PL':616,'PT':620,'QA':634,'RO':642,
    'RU':643,'SA':682,'RS':688,'SG':702,'SK':703,'SI':705,'ZA':710,'ES':724,
    'LK':144,'SE':752,'CH':756,'SY':760,'TW':158,'TH':764,'TN':788,'TR':792,
    'UA':804,'AE':784,'GB':826,'US':840,'UZ':860,'VN':704,'YE':887,
}


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
        return _A2N.get((rec.country.iso_code or '').upper())
    except Exception:
        return None
