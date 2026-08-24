#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
bash -n ttuhelper.sh
bash -n install.sh
bash -n uninstall.sh
version="$(tr -d '\r\n' < VERSION)"
grep -Fq "HELPER_VERSION=\"$version\"" ttuhelper.sh
for token in 'cks-check' 'validate_cookie_file' '#HttpOnly_' 'install -o 10001 -g 10001 -m 0640'; do
  grep -Fq "$token" ttuhelper.sh
 done
printf '[OK] TTUHelper %s shell syntax and cookie safety checks passed\n' "$version"
