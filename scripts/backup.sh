#!/bin/bash
set -e

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/pomoshnik_backup_$DATE.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "Создаем бэкап данных OpenClaw..."
tar -czf "$BACKUP_FILE" ./openclaw_data ./openclaw/MEMORY.md ./openclaw/SOUL.md

echo "Бэкап успешно создан: $BACKUP_FILE"
