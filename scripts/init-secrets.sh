#!/usr/bin/env sh
# Генерирует локальные секреты для docker compose. Файлы в secrets/ не коммитятся.
set -eu

cd "$(dirname "$0")/.."
umask 077

password_file=secrets/grafana_admin_password.txt
if [ -s "$password_file" ]; then
    echo "$password_file already exists, keeping it"
else
    openssl rand -base64 24 | tr -d '\n' > "$password_file"
    echo "generated $password_file"
fi
