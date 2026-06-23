CREATE TABLE IF NOT EXISTS bl_lists (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    community   INTEGER NOT NULL,
    enabled     BOOLEAN DEFAULT TRUE,
    last_ok_at  TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS bl_prefixes (
    id             BIGSERIAL PRIMARY KEY,
    prefix         CIDR NOT NULL UNIQUE,
    country_iso    INTEGER,
    geo_checked_at TIMESTAMPTZ,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS bl_prefixes_prefix_idx ON bl_prefixes (prefix);
CREATE TABLE IF NOT EXISTS bl_prefix_lists (
    prefix_id   BIGINT NOT NULL REFERENCES bl_prefixes(id) ON DELETE CASCADE,
    list_id     INTEGER NOT NULL REFERENCES bl_lists(id) ON DELETE CASCADE,
    added_at    TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (prefix_id, list_id)
);
CREATE INDEX IF NOT EXISTS bl_prefix_lists_list_idx ON bl_prefix_lists (list_id);
CREATE TABLE IF NOT EXISTS bl_update_log (
    id          BIGSERIAL PRIMARY KEY,
    list_id     INTEGER NOT NULL REFERENCES bl_lists(id),
    started_at  TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status      TEXT NOT NULL DEFAULT 'running',
    total       INTEGER DEFAULT 0,
    added       INTEGER DEFAULT 0,
    removed     INTEGER DEFAULT 0,
    error_msg   TEXT
);
INSERT INTO bl_lists (name, label, community) VALUES
    ('telegram','Telegram',250),('whatsapp','WhatsApp',251),
    ('vmware','VMware',252),('intel','Intel',253),
    ('chatgpt','ChatGPT',260),('claude','Claude',261),
    ('cdn77','CDN77',262),('plex','Plex',263),
    ('gcore','GCore',264),('qrator','Qrator',270),
    ('t1cloud','T1 Cloud',271),('akamai','Akamai',277),
    ('microsoft','Microsoft',280),('nvidia','NVIDIA',281),
    ('docker','Docker',282),('aws','AWS',283),
    ('cloudflare','Cloudflare',284),('yandex','Yandex',285),
    ('meta','Meta',245),('google','Google',246),
    ('rkn','RKN AntiFilter',777),('ru_gov','RU-GOV',900)
ON CONFLICT (name) DO UPDATE SET label=EXCLUDED.label, community=EXCLUDED.community;
