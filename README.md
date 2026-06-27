# waystone3 — Bird Prefix Updater

Автообновление списков префиксов с BGP community для BIRD 2.14.

## Структура

- `config/settings.py` — настройки (БД, Telegram, пути)
- `db/schema.sql` — схема PostgreSQL
- `db/database.py` — функции работы с БД
- `sources/fetcher.py` — получение префиксов из источников
- `geo/lookup.py` — определение страны (whois + GeoIP fallback)
- `bird/generator.py` — генерация конфигов BIRD, резервное копирование
- `notify/telegram.py` — уведомления в Telegram
- `updater.py` — главный скрипт
- `systemd/` — юниты systemd
- `install.sh` — скрипт установки

## Community

- `65444:XXX` — вендор/список (Telegram=250, RKN=777, RU-GOV=900 ...)
- `65445:XXX` — страна (ISO 3166-1 numeric: RU=643, US=840 ...)

## Установка

```bash
# Клонировать в /home/mcp/bird-updater
git clone https://github.com/behek/waystone3.git /home/mcp/bird-updater
bash /home/mcp/bird-updater/install.sh <TG_TOKEN> <TG_CHAT_ID>
```

## Запуск вручную

```bash
cd /home/mcp/bird-updater

# Инициализация БД (первый раз)
python3 updater.py --init-schema

# Тест одного списка без записи в БД
python3 updater.py --list telegram --dry-run

# Обновить один список
python3 updater.py --list rkn

# Обновить все списки
python3 updater.py

# Перегенерировать все конфиги BIRD без обновления списков
python3 updater.py --regen-bird

# Ежемесячный пересчёт GeoIP
python3 updater.py --geo-refresh
```

## Логи

```bash
journalctl -u bird-updater -f
journalctl -u bird-geo-refresh -f
```

## Таймеры

```bash
systemctl list-timers bird-*
```
