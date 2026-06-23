import os

DB = {
    "host":     os.getenv("PG_HOST", "127.0.0.1"),
    "port":     int(os.getenv("PG_PORT", "5434")),
    "dbname":   os.getenv("PG_DB",   "waystone2"),
    "user":     os.getenv("PG_USER", "bird"),
    "password": os.getenv("PG_PASS", "bird-pg-pass"),
}

TG_TOKEN = os.getenv("TG_TOKEN", "")
TG_CHAT  = os.getenv("TG_CHAT",  "")

BLACKLISTS_DIR  = os.getenv("BLACKLISTS_DIR", "/home/mcp/blacklists/AS_Network_List")
BIRD_PROTOCOLS  = os.getenv("BIRD_PROTOCOLS", "/etc/bird/protocols")
BIRD_BACKUP_DIR = os.getenv("BIRD_BACKUP_DIR", "/etc/bird/backups")
MMDB_PATH       = os.getenv("MMDB_PATH",       "/home/mcp/dbip-country.mmdb")
BIRDC_SOCKET    = os.getenv("BIRDC_SOCKET",    "/run/bird/bird.ctl")

COMMUNITY_COUNTRY = 65445
COMMUNITY_VENDOR  = 65444

RKN_URL    = "https://antifilter.download/list/allyouneed.lst"
RU_GOV_URL = "https://raw.githubusercontent.com/C24Be/AS_Network_List/main/lists/ru-gov-netnames.txt"

SOURCES = {
    "telegram":   {"type": "asn_file", "file": "telegram.txt"},
    "whatsapp":   {"type": "asn_file", "file": "whatsapp.txt"},
    "vmware":     {"type": "asn_file", "file": "vmware.txt"},
    "intel":      {"type": "asn_file", "file": "intel.txt"},
    "chatgpt":    {"type": "asn_file", "file": "chatgpt.txt"},
    "cdn77":      {"type": "asn_file", "file": "cdn77.txt"},
    "qrator":     {"type": "asn_file", "file": "qrator.txt"},
    "t1cloud":    {"type": "asn_file", "file": "t1cloud.txt"},
    "akamai":     {"type": "asn_file", "file": "akamai.txt"},
    "microsoft":  {"type": "asn_file", "file": "microsoft.txt"},
    "nvidia":     {"type": "asn_file", "file": "nvidia.txt"},
    "aws":        {"type": "asn_file", "file": "aws.txt"},
    "cloudflare": {"type": "asn_file", "file": "cloudflare.txt"},
    "yandex":     {"type": "asn_file", "file": "yandex.txt"},
    "meta":       {"type": "asn_file", "file": "meta.txt"},
    "google":     {"type": "asn_file", "file": "google.txt"},
    "rkn":        {"type": "url",     "url": RKN_URL},
    "ru_gov":     {"type": "netname", "url": RU_GOV_URL},
}
