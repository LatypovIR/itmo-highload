#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
umask 077
[ -s secrets/grafana_admin_password.txt ] || openssl rand -base64 24 | tr -d '\n' > secrets/grafana_admin_password.txt
