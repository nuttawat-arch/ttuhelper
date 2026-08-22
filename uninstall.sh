#!/usr/bin/env bash
set -euo pipefail

[[ "$EUID" -eq 0 ]] || { echo "Run with sudo: sudo ./uninstall.sh" >&2; exit 1; }

rm -f /usr/local/bin/ttuhelper

echo "Removed /usr/local/bin/ttuhelper."
echo "Kept /etc/default/ttuhelper and bot data directories unchanged for safety."
echo "The old /usr/local/bin/tthelper command, if present, was not touched."
echo "If you intentionally want to remove the new helper configuration/data too, delete them manually:"
echo "  sudo rm -f /etc/default/ttuhelper"
echo "  sudo rm -rf /opt/sntalkbot-bots"
echo "  # Legacy data, only if you no longer need it:"
echo "  sudo rm -rf /opt/ttutilities-bots"
