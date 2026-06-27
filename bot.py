#!/usr/bin/env python3
import os, sys, time, threading, io
import requests

sys.path.insert(0, os.path.dirname(__file__))

env_file = os.path.join(os.path.dirname(__file__), 'systemd/bird-updater.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k, v)

from config.settings import TG_TOKEN, TG_CHAT

BASE  = f'https://api.telegram.org/bot{TG_TOKEN}'
OWNER = str(TG_CHAT)

_pending = {}


def send(chat_id, text):
    requests.post(f'{BASE}/sendMessage',
                  json={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'},
                  timeout=15)


def get_updates(offset):
    try:
        r = requests.get(f'{BASE}/getUpdates',
                         params={'offset': offset, 'timeout': 30},
                         timeout=35)
        return r.json().get('result', [])
    except Exception:
        return []


def _capture(fn, *args, **kwargs):
    buf = io.StringIO()
    old, sys.stdout = sys.stdout, buf
    try:
        fn(*args, **kwargs)
    finally:
        sys.stdout = old
    return buf.getvalue()


def _in_thread(chat_id, fn, *args):
    def _wrap():
        try:
            fn(*args)
        except Exception as e:
            send(chat_id, f'🚨 <code>{e}</code>')
    threading.Thread(target=_wrap, daemon=True).start()


# --- команды ---

def cmd_help(chat_id, _):
    send(chat_id, (
        '<b>Bird Updater Bot</b>\n\n'
        '<b>Обновление:</b>\n'
        '/update — все списки\n'
        '/update &lt;name&gt; — один список\n'
        '/regen — перегенерировать конфиг BIRD\n'
        '/geo — обновить GeoIP\n\n'
        '<b>Вендоры:</b>\n'
        '/list — таблица вендоров\n'
        '/add &lt;name&gt; &lt;community&gt; &lt;file&gt; [label]\n'
        '/remove &lt;name&gt;\n\n'
        '<b>Файлы списков:</b>\n'
        '/files — список файлов\n'
        '/show &lt;name&gt; — содержимое файла\n'
        '/addentry &lt;name&gt; &lt;AS/prefix&gt;\n'
        '/delentry &lt;name&gt; &lt;AS/prefix&gt;\n\n'
        '/confirm · /cancel'
    ))


def cmd_update(chat_id, args):
    from updater import update_list, update_all
    if args:
        name = args[0]
        send(chat_id, f'⏳ Обновляю <b>{name}</b>…')
        def _do():
            ok = update_list(name)
            if not ok:
                send(chat_id, f'❌ {name}: ошибка (см. логи)')
        _in_thread(chat_id, _do)
    else:
        send(chat_id, '⏳ Обновляю все списки…')
        _in_thread(chat_id, update_all)


def cmd_list(chat_id, _):
    from manage import list_vendors
    out = _capture(list_vendors)
    send(chat_id, f'<pre>{out}</pre>')


def cmd_regen(chat_id, _):
    from bird.generator import write_combined_conf, birdc_configure
    send(chat_id, '⏳ Перегенерирую конфиг BIRD…')
    def _do():
        write_combined_conf()
        if birdc_configure():
            send(chat_id, '✅ BIRD reconfigured OK')
        else:
            send(chat_id, '❌ BIRD configure failed')
    _in_thread(chat_id, _do)


def cmd_geo(chat_id, _):
    from updater import geo_refresh_all
    send(chat_id, '⏳ Запускаю geo refresh…')
    _in_thread(chat_id, geo_refresh_all)


def cmd_add(chat_id, args):
    if len(args) < 3:
        send(chat_id, 'Использование: /add &lt;name&gt; &lt;community&gt; &lt;file&gt; [label]')
        return
    name, community_str, file_ = args[0], args[1], args[2]
    label = ' '.join(args[3:]) or None
    try:
        community = int(community_str)
    except ValueError:
        send(chat_id, '❌ community должен быть числом'); return
    from manage import add_vendor
    out = _capture(add_vendor, name, community, file_, label)
    send(chat_id, f'<pre>{out}</pre>')


def cmd_remove(chat_id, args):
    if not args:
        send(chat_id, 'Использование: /remove &lt;name&gt;'); return
    name = args[0]
    _pending[chat_id] = {'action': 'remove', 'data': name}
    send(chat_id, f'Удалить <b>{name}</b> и все его данные?\n\n/confirm — да\n/cancel — нет')


def cmd_confirm(chat_id, _):
    p = _pending.pop(chat_id, None)
    if not p:
        send(chat_id, 'Нет ожидающих действий'); return
    if p['action'] == 'remove':
        name = p['data']
        send(chat_id, f'⏳ Удаляю {name}…')
        from manage import remove_vendor
        out = _capture(remove_vendor, name)
        send(chat_id, f'<pre>{out}</pre>')


def cmd_cancel(chat_id, _):
    _pending.pop(chat_id, None)
    send(chat_id, '❌ Отменено')


# --- управление файлами lists/ ---

def _lists_dir():
    from config.settings import LISTS_DIR
    return LISTS_DIR


def cmd_files(chat_id, _):
    d = _lists_dir()
    files = sorted(f for f in os.listdir(d) if f.endswith('.txt'))
    lines = []
    for fn in files:
        path = os.path.join(d, fn)
        with open(path) as f:
            n = sum(1 for l in f if l.strip() and not l.startswith('#'))
        lines.append(f'{fn[:-4]:<15} {n} строк')
    send(chat_id, '<pre>' + '\n'.join(lines) + '</pre>')


def cmd_show(chat_id, args):
    if not args:
        send(chat_id, 'Использование: /show &lt;name&gt;'); return
    path = os.path.join(_lists_dir(), args[0] + '.txt')
    if not os.path.exists(path):
        send(chat_id, f'❌ Файл не найден: {args[0]}.txt'); return
    with open(path) as f:
        content = f.read()
    if len(content) > 3000:
        content = content[:3000] + '\n…(обрезано)'
    send(chat_id, f'<pre>{content}</pre>')


def cmd_addentry(chat_id, args):
    if len(args) < 2:
        send(chat_id, 'Использование: /addentry &lt;name&gt; &lt;ASN или префикс&gt;'); return
    name, entry = args[0], args[1]
    path = os.path.join(_lists_dir(), name + '.txt')
    if not os.path.exists(path):
        send(chat_id, f'❌ Файл не найден: {name}.txt'); return
    with open(path) as f:
        lines = f.read().splitlines()
    if entry in lines:
        send(chat_id, f'⚠️ Уже есть: <code>{entry}</code>'); return
    with open(path, 'a') as f:
        f.write(f'\n{entry}\n')
    send(chat_id, f'✅ Добавлено в <b>{name}</b>: <code>{entry}</code>\nЗапусти /update {name} чтобы применить.')


def cmd_delentry(chat_id, args):
    if len(args) < 2:
        send(chat_id, 'Использование: /delentry &lt;name&gt; &lt;ASN или префикс&gt;'); return
    name, entry = args[0], args[1]
    path = os.path.join(_lists_dir(), name + '.txt')
    if not os.path.exists(path):
        send(chat_id, f'❌ Файл не найден: {name}.txt'); return
    with open(path) as f:
        lines = f.read().splitlines()
    new_lines = [l for l in lines if l.strip() != entry]
    if len(new_lines) == len(lines):
        send(chat_id, f'⚠️ Не найдено: <code>{entry}</code>'); return
    with open(path, 'w') as f:
        f.write('\n'.join(new_lines) + '\n')
    send(chat_id, f'✅ Удалено из <b>{name}</b>: <code>{entry}</code>\nЗапусти /update {name} чтобы применить.')


COMMANDS = {
    'start':    cmd_help,
    'help':     cmd_help,
    'update':   cmd_update,
    'list':     cmd_list,
    'regen':    cmd_regen,
    'geo':      cmd_geo,
    'add':      cmd_add,
    'remove':   cmd_remove,
    'confirm':  cmd_confirm,
    'cancel':   cmd_cancel,
    'files':    cmd_files,
    'show':     cmd_show,
    'addentry': cmd_addentry,
    'delentry': cmd_delentry,
}


def handle(msg):
    chat_id = str(msg.get('chat', {}).get('id', ''))
    if chat_id != OWNER:
        return
    text = (msg.get('text') or '').strip()
    if not text.startswith('/'):
        return
    parts = text.split()
    cmd   = parts[0].lstrip('/').lower().split('@')[0]
    args  = parts[1:]
    fn = COMMANDS.get(cmd)
    if fn:
        fn(chat_id, args)
    else:
        send(chat_id, f'Неизвестная команда: /{cmd}\n/help')


def main():
    print('[bot] starting', flush=True)
    send(OWNER, '🤖 Bird bot online')
    offset = 0
    while True:
        updates = get_updates(offset)
        for upd in updates:
            offset = upd['update_id'] + 1
            msg = upd.get('message') or upd.get('edited_message')
            if msg:
                try:
                    handle(msg)
                except Exception as e:
                    print(f'[bot] error: {e}', file=sys.stderr)
        if not updates:
            time.sleep(1)


if __name__ == '__main__':
    main()
