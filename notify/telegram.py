import requests, sys
from config.settings import TG_TOKEN, TG_CHAT


def _send(text):
    if not TG_TOKEN or not TG_CHAT:
        print('[tg] not configured', file=sys.stderr)
        return False
    try:
        r = requests.post(
            f'https://api.telegram.org/bot{TG_TOKEN}/sendMessage',
            json={'chat_id': TG_CHAT, 'text': text, 'parse_mode': 'HTML'},
            timeout=15)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f'[tg] {e}', file=sys.stderr)
        return False


def send_update_stats(label, total, added, removed):
    parts = []
    if added:   parts.append(f'<b>+{added}</b> новых')
    if removed: parts.append(f'<b>-{removed}</b> удалено')
    change = ', '.join(parts) if parts else 'без изменений'
    _send(f'✅ <b>{label}</b>\nВсего: {total} | {change}')


def send_error(label, err):
    _send(f'🚨 <b>{label}</b> — ошибка\n<code>{str(err)[:300]}</code>')


def send_geo_refresh_done(updated, failed):
    _send(f'🌍 GeoIP refresh\nОбновлено: <b>{updated}</b>, ошибок: {failed}')


def send_bird_reload_ok():
    _send('🐦 BIRD reconfigured OK')


def send_bird_reload_fail():
    _send('🚨 BIRD configure failed')
