#!/bin/bash
set -e

echo "Начинаем установку на Oracle Cloud..."

# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker и Docker Compose
if ! command -v docker &> /dev/null; then
    echo "Устанавливаем Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
else
    echo "Docker уже установлен."
fi

# Настройка файрвола (опционально, если нужно)
# sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 3001 -j ACCEPT
# sudo netfilter-persistent save

echo "Копируем .env.example в .env (не забудьте отредактировать его!)..."
if [ ! -f .env ]; then
    cp .env.example .env
fi

echo "Сборка и запуск контейнеров..."
docker compose build
docker compose up -d

echo "Установка завершена! Отредактируйте .env файл и перезапустите контейнеры: docker compose restart"
