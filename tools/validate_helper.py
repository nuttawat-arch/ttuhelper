#!/usr/bin/env python3
from pathlib import Path
import os, platform, re, shutil, sys, subprocess
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def need(cond,msg):
    if cond: print(f'[OK] {msg}')
    else: errors.append(msg); print(f'[FAIL] {msg}')
version=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
sh=(ROOT/'ttuhelper.sh').read_text(encoding='utf-8')
installer=(ROOT/'install.sh').read_text(encoding='utf-8')
need(f'HELPER_VERSION="{version}"' in sh, f'helper version matches VERSION ({version})')
expected=['new','run','stop','restart','delete','logs','ls','ps','start-all','stop-all','pull','update','migrate-ttmediabot','cks','cks-all','cks-check','limit','edit','path','doctor','version','help']
for cmd in expected:
    need(re.search(rf'^\s*ttuhelper\s+{re.escape(cmd)}(?:\s|$)', sh, re.M) is not None, f'help advertises {cmd}')
need(len(expected)==22, 'TTUHelper public command catalog contains 22 commands')
# Cookie safety
for token in ('validate_cookie_file()', '#HttpOnly_', 'install -o 10001 -g 10001 -m 0640', 'Restart the instance to force yt-dlp to reload'):
    need(token in sh, f'cookie safety behavior present: {token}')
need((ROOT/'YOUTUBE_COOKIES_TH.md').is_file(), 'cookie guide is packaged')
need('cookies.txt' in (ROOT/'.gitignore').read_text(encoding='utf-8'), 'cookies are ignored by Git')
need(re.search(r'cks\)\s+update_cookies\s+"\$\{1:-\}"\s+"\$\{2:-\}"', sh) is not None, 'cks accepts an optional file path')
need(re.search(r'cks-all\)\s+update_all_cookies\s+"\$\{1:-\}"', sh) is not None, 'cks-all accepts an optional file path')
need(re.search(r'cks-check\)\s+check_cookies\s+"\$\{1:-\}"', sh) is not None, 'cks-check dispatch is registered')
need('instance_has_player()' in sh and 'Server Manager-only; YouTube cookies belong only to Player/Full Bot.' in sh, 'cks/cks-check reject Manager-only instances')
need('skipped $skipped Server Manager instance(s)' in sh, 'cks-all skips Server Manager-only instances')
need('elif [[ "$cmd" == "cks" || "$cmd" == "cks-all" || "$cmd" == "cks-check" ]]' in sh, 'cookie maintenance does not require a running Docker daemon')
# Realtime API metadata and collision safety
need('API_PORT_MIN="${TTU_API_PORT_MIN:-20000}"' in sh and 'API_PORT_MAX="${TTU_API_PORT_MAX:-27999}"' in sh, 'per-instance API defaults to high loopback range 20000-27999')
need('reserved=set()' in sh and "root.glob('*/instance.conf')" in sh, 'API allocator excludes ports already assigned to other instances')
need("s.bind(('127.0.0.1', port))" in sh, 'API allocator verifies the port is actually free on loopback')
need('api_lock_acquire()' in sh and 'flock -x 9' in sh and sh.count('api_lock_acquire') >= 3, 'API allocation is serialized to prevent concurrent duplicate assignments')
for token in ('SNTALKBOT_API_BIND=127.0.0.1','SNTALKBOT_API_PORT=$API_PORT','SNTALKBOT_API_TOKEN=$API_TOKEN'):
    need(token in sh, f'container receives local API metadata: {token}')
need('generate_api_token()' in sh and 'api_token_new="$(generate_api_token)"' in sh and 'chmod 0640 "$dir/instance.conf"' in sh, 'API token is generated per instance and kept in protected instance metadata')
# Linux/web-manager file sharing
need('chmod 2770 "$BOTS_ROOT"' in sh and sh.count('chmod 2770 "$dir"') >= 2, 'bot data root/instance directories preserve group-write setgid semantics')
need('chmod 0660 "$dir/config.ini"' in sh and 'chmod 0660 "$dir/limits.conf"' in sh, 'config and limits remain editable through the shared data group')
# Delete safety
need(re.search(r'delete\)\s+delete_bot\s+"\$\{1:-\}"\s+"\$\{2:-\}"', sh) is not None, 'delete dispatch is registered')
for token in ('Type the exact instance name', 'sntalkbot-deleted-backups', 'tar -C "$BOTS_ROOT" -czf "$backup"', 'chmod 0600 "$backup"', 'rm -rf --one-file-system -- "$real_dir"'):
    need(token in sh, f'delete safety invariant present: {token}')
need('--yes' in sh, 'delete supports non-interactive --yes for the Web Manager after web confirmation')
# Installer preflight
for token in ('has curl || missing+=(curl)','has python3 || missing+=(python3)','has flock || missing+=(util-linux)','if ! has docker','Docker command already exists; skipping Docker installation'):
    need(token in installer, f'installer preflight present: {token}')
need('grep -q \'^TTU_API_PORT_MIN=\'' in installer and 'grep -q \'^TTU_API_PORT_MAX=\'' in installer, 'upgrade installer adds only missing API range settings without replacing existing config')
# Shell syntax.  On Windows, ``bash`` on PATH can be WSL bash.  Passing a
# Windows path such as D:\\repo\\install.sh to it produces a false failure even
# when the script is valid.  Prefer the Git-for-Windows bash that ships with git
# and feed the script through stdin so path syntax is irrelevant on every OS.
def find_bash():
    candidates=[]
    explicit=os.environ.get('BASH')
    if explicit:
        candidates.append(Path(explicit))
    git=shutil.which('git')
    if git:
        g=Path(git).resolve()
        # Typical Git for Windows layouts:
        #   C:/Program Files/Git/cmd/git.exe
        #   C:/Program Files/Git/bin/git.exe
        root=g.parent.parent
        candidates.extend((root/'bin'/'bash.exe', root/'usr'/'bin'/'bash.exe'))
    path_bash=shutil.which('bash')
    if path_bash:
        candidates.append(Path(path_bash))
    seen=set()
    for candidate in candidates:
        key=str(candidate).lower() if os.name=='nt' else str(candidate)
        if key in seen:
            continue
        seen.add(key)
        try:
            if candidate.is_file():
                return str(candidate)
        except OSError:
            pass
    return None

bash=find_bash()
need(bool(bash), 'bash executable available for real shell-syntax validation')
if bash:
    print(f'[INFO] shell syntax validator: {bash}')
    for file in (ROOT/'ttuhelper.sh', ROOT/'install.sh'):
        script=file.read_text(encoding='utf-8')
        try:
            proc=subprocess.run([bash, '-n'], input=script, capture_output=True, text=True)
        except OSError as exc:
            need(False, f'bash syntax valid: {file.name}')
            print(f'[DETAIL] unable to start {bash}: {exc}')
            continue
        ok=proc.returncode==0
        need(ok, f'bash syntax valid: {file.name}')
        if not ok:
            detail=(proc.stderr or proc.stdout or '').strip()
            if detail:
                print(f'[DETAIL] {file.name}: {detail}')
raise SystemExit(1 if errors else 0)
