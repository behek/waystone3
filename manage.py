#!/usr/bin/env python3
"""
Управление вендорами.

Добавить:
  python3 manage.py --add NAME --community 286 --file NAME.txt [--label "Pretty Name"]

Удалить:
  python3 manage.py --remove NAME
"""
import argparse, sys, os, re, subprocess
sys.path.insert(0, os.path.dirname(__file__))

# Загружаем env если запущен не через systemd
env_file = os.path.join(os.path.dirname(__file__), 'systemd/bird-updater.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k, v)

from db.database import get_conn, cursor
from config.settings import BIRD_PROTOCOLS, SOURCES


def add_vendor(name, community, file, label):
    label = label or name.capitalize()

    # 1. Добавляем в БД
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO bl_lists (name, label, community)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (name) DO UPDATE
                    SET label=EXCLUDED.label, community=EXCLUDED.community
                """, (name, label, community))
        print(f"[db] added '{name}' (community={community})")
    finally:
        conn.close()

    # 2. Добавляем в settings.py
    settings_path = os.path.join(os.path.dirname(__file__), 'config/settings.py')
    with open(settings_path) as f:
        content = f.read()

    entry = f'    "{name}":    {{"type": "asn_file", "file": "{file}"}},\n'
    if f'"{name}"' not in content:
        # Вставляем перед строкой с rkn
        content = content.replace(
            '    "rkn":',
            entry + '    "rkn":'
        )
        with open(settings_path, 'w') as f:
            f.write(content)
        print(f"[settings] added '{name}'")
    else:
        print(f"[settings] '{name}' already exists, skipped")

    print(f"\nГотово! Теперь:")
    print(f"  1. Создай файл: ~/blacklists/AS_Network_List/lists/{file}")
    print(f"  2. Запусти:     python3 updater.py --list {name}")


def remove_vendor(name):
    # 1. Получаем list_id
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, label FROM bl_lists WHERE name=%s", (name,))
                row = cur.fetchone()
                if not row:
                    print(f"[db] vendor '{name}' not found")
                    return
                list_id, label = row[0], row[1]

                # 2. Удаляем связи prefix_lists
                cur.execute("DELETE FROM bl_prefix_lists WHERE list_id=%s", (list_id,))
                deleted_links = cur.rowcount
                print(f"[db] removed {deleted_links} prefix links for '{name}'")

                # 3. Удаляем логи
                cur.execute("DELETE FROM bl_update_log WHERE list_id=%s", (list_id,))
                print(f"[db] removed update logs for '{name}'")

                # 4. Удаляем сам список
                cur.execute("DELETE FROM bl_lists WHERE id=%s", (list_id,))
                print(f"[db] removed list '{name}'")

        print(f"[db] done")
    finally:
        conn.close()

    # 5. Удаляем из settings.py
    settings_path = os.path.join(os.path.dirname(__file__), 'config/settings.py')
    with open(settings_path) as f:
        content = f.read()
    new_content = re.sub(rf'\s+"{name}".*\n', '\n', content)
    if new_content != content:
        with open(settings_path, 'w') as f:
            f.write(new_content)
        print(f"[settings] removed '{name}'")
    else:
        print(f"[settings] '{name}' not found in settings.py")

    # 6. Удаляем конфиг BIRD и делаем backup
    conf_path = os.path.join(BIRD_PROTOCOLS, f'static_{name}.conf')
    if os.path.exists(conf_path):
        os.unlink(conf_path)
        print(f"[bird] removed {conf_path}")
    else:
        print(f"[bird] {conf_path} not found, skip")

    # 7. Убираем include из bird.conf
    bird_conf = '/etc/bird/bird.conf'
    result = subprocess.run(
        ['sudo', 'sed', '-i', f'/static_{name}\\.conf/d', bird_conf],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"[bird.conf] removed include for static_{name}.conf")
    else:
        print(f"[bird.conf] warning: {result.stderr}")

    # 8. Перезагружаем BIRD
    result = subprocess.run(
        ['sudo', 'birdc', 'configure'],
        capture_output=True, text=True
    )
    if 'econfigured' in result.stdout + result.stderr:
        print("[bird] reconfigured OK")
    else:
        print(f"[bird] warning: {result.stdout + result.stderr}")

    print(f"\nГотово! Вендор '{name}' ({label}) удалён.")
    print(f"Файл списка ~/blacklists/AS_Network_List/lists/ НЕ удалён — удали вручную если нужно.")


def list_vendors():
    with cursor() as cur:
        cur.execute("""
            SELECT l.name, l.label, l.community, l.enabled,
                   COUNT(pl.prefix_id) as prefix_count,
                   l.last_ok_at
            FROM bl_lists l
            LEFT JOIN bl_prefix_lists pl ON pl.list_id = l.id
            GROUP BY l.id
            ORDER BY l.name
        """)
        rows = cur.fetchall()

    print(f"{'NAME':<15} {'LABEL':<20} {'COMM':>6} {'PREFIXES':>9} {'LAST OK'}")
    print("-" * 70)
    for r in rows:
        last_ok = r['last_ok_at'].strftime('%Y-%m-%d %H:%M') if r['last_ok_at'] else 'never'
        enabled = '' if r['enabled'] else ' [disabled]'
        print(f"{r['name']:<15} {r['label']:<20} {r['community']:>6} {r['prefix_count']:>9}  {last_ok}{enabled}")


def main():
    p = argparse.ArgumentParser(description='Vendor management')
    p.add_argument('--add',       metavar='NAME', help='Add vendor')
    p.add_argument('--remove',    metavar='NAME', help='Remove vendor')
    p.add_argument('--list',      action='store_true', help='List all vendors')
    p.add_argument('--community', type=int, help='Community ID (for --add)')
    p.add_argument('--file',      help='Source filename in lists/ dir (for --add)')
    p.add_argument('--label',     help='Display label (for --add)')
    a = p.parse_args()

    if a.list:
        list_vendors()
    elif a.add:
        if not a.community or not a.file:
            print("Error: --add requires --community and --file")
            sys.exit(1)
        add_vendor(a.add, a.community, a.file, a.label)
    elif a.remove:
        confirm = input(f"Remove vendor '{a.remove}' and all its data? [y/N] ")
        if confirm.lower() == 'y':
            remove_vendor(a.remove)
        else:
            print("Cancelled")
    else:
        p.print_help()


if __name__ == '__main__':
    main()
