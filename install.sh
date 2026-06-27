#!/bin/bash
set -e
TG_TOKEN="${1:-}"
TG_CHAT="${2:-}"
[ -z "$TG_TOKEN" ] || [ -z "$TG_CHAT" ] && { echo "Usage: bash install.sh <TG_TOKEN> <TG_CHAT_ID>"; exit 1; }

DIR="/home/mcp/bird-updater"
echo "=== 1. pip install ==="
pip3 install -q -r "$DIR/requirements.txt" --break-system-packages

echo "=== 2. init schema ==="
cd "$DIR"
PG_HOST=127.0.0.1 PG_PORT=5434 PG_DB=waystone2 PG_USER=bird PG_PASS=bird-pg-pass \
    python3 updater.py --init-schema

echo "=== 3. backup dir ==="
sudo mkdir -p /etc/bird/backups && sudo chown mcp:mcp /etc/bird/backups

echo "=== 4. env file ==="
cat > "$DIR/systemd/bird-updater.env" << ENVEOF
PG_HOST=127.0.0.1
PG_PORT=5434
PG_DB=waystone2
PG_USER=bird
PG_PASS=bird-pg-pass
TG_TOKEN=$TG_TOKEN
TG_CHAT=$TG_CHAT
BLACKLISTS_DIR=/home/mcp/blacklists/AS_Network_List
BIRD_PROTOCOLS=/etc/bird/protocols
BIRD_BACKUP_DIR=/etc/bird/backups
MMDB_PATH=/home/mcp/dbip-country.mmdb
BIRDC_SOCKET=/run/bird/bird.ctl
ENVEOF
chmod 600 "$DIR/systemd/bird-updater.env"

echo "=== 5. systemd ==="
sudo cp "$DIR/systemd/bird-updater.service"     /etc/systemd/system/
sudo cp "$DIR/systemd/bird-updater.timer"       /etc/systemd/system/
sudo cp "$DIR/systemd/bird-geo-refresh.service" /etc/systemd/system/
sudo cp "$DIR/systemd/bird-geo-refresh.timer"   /etc/systemd/system/

echo "=== 6. birdc sudo ==="
echo 'mcp ALL=(ALL) NOPASSWD: /usr/sbin/birdc' | sudo tee /etc/sudoers.d/bird-updater > /dev/null
sudo chmod 440 /etc/sudoers.d/bird-updater

echo "=== 7. enable timers ==="
sudo systemctl daemon-reload
sudo systemctl enable --now bird-updater.timer
sudo systemctl enable --now bird-geo-refresh.timer

echo ""
echo "Done! Test: cd $DIR && python3 updater.py --list telegram --dry-run"
echo "Logs: journalctl -u bird-updater -f"
