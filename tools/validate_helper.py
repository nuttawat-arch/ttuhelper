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
need('container_is_managed()' in sh and 'refuse_unmanaged_collision()' in sh, 'container operations verify TTUHelper ownership labels before destructive actions')
need(sh.count('refuse_unmanaged_collision "$name"') >= 3, 'run/stop/delete guard against unmanaged Docker name collisions')
need('Refusing logs for unmanaged Docker container' in sh, 'logs cannot expose a same-name non-TTUHelper Docker container')
need('name-conflict-unmanaged' in sh, 'instance listing surfaces unmanaged Docker name collisions without touching them')
# Installer preflight
for token in ('has curl || missing+=(curl)','has python3 || missing+=(python3)','has flock || missing+=(util-linux)','if ! has docker','Docker command already exists; skipping Docker installation'):
    need(token in installer, f'installer preflight present: {token}')
need('grep -q \'^TTU_API_PORT_MIN=\'' in installer and 'grep -q \'^TTU_API_PORT_MAX=\'' in installer, 'upgrade installer adds only missing API range settings without replacing existing config')
need('--repair-existing' in installer and 'Checking previously migrated TTMediaBot instances' in installer, 'helper installer automatically repairs previously migrated configs after pulling the current image')
need('repair_migrated_configs "$name"' in sh and 'repair_migrated_configs()' in sh, 'run/restart repairs migrated config before container recreation')

# Migration schema regression: build from the current template, import only
# supported legacy values, reject invalid scalar/range values, and never copy the
# raw legacy config into the active instance. Missing current fields keep their
# template defaults automatically.
import tempfile, json, configparser
try:
    with tempfile.TemporaryDirectory() as td:
        t=Path(td); source=t/'legacy'; bot=source/'LegacyBot'; bot.mkdir(parents=True)
        dest=t/'dest'; template=t/'config_default.ini'
        template_text = "[features]\nplayer_enabled=True\nserver_management_enabled=True\n[server]\naddress=CHANGE_ME\ntcp_port=10333\nudp_port=10333\nencrypted=False\nusername=CHANGE_ME\npassword=\n[bot]\nlanguage=th\nnickname=SN TalkBot\ngender=0\ndefault_channel=/\nchannel_password=\nstatus_message=auto\nblocked_commands=\nreconnection_attempts=-1\nreconnection_timeout=10\nintercept_channel_messages=True\nwelcome_broadcast=True\nwelcome_mode=0\nprofanity_filter_enabled=False\n[accounts]\nauthorized_users=\ndetect_server_admins=True\n[playback]\ninput_device=auto\noutput_device=auto\ncookiefile_path=/app/data/cookies.txt\ndefault_volume=80\nmax_volume=150\nseek_step=5\nsend_channel_messages=True\nvolume_fading=0\nfade_enabled=True\n[teamtalk_license]\nlicense_name=\nlicense_key=\n"
        template.write_text(template_text, encoding='utf-8')
        legacy={
            'config_version':1,
            'general':{'language':'xx-unsupported','send_channel_messages':'yes','cache_file_name':'TTMediaBotCache.dat','blocked_commands':['/p','/s'],'delete_uploaded_files_after':300,'time_format':'%H:%M','start_commands':[],'legacy_only':'drop-me'},
            'sound_devices':{'output_device':1,'input_device':5},
            'player':{'default_volume':'not-a-number','max_volume':9999,'seek_step':'7','volume_fading':True,'volume_fading_interval':0.025,'player_options':{},'old_device':42},
            'teamtalk':{'hostname':'server.example','tcp_port':'10333','udp_port':'invalid','encrypted':'true','username':'botuser','password':'legacy-secret','nickname':['bad-container'],'channel':'/music','channel_password':'','status':'','gender':'unknown','reconnection_attempts':-1,'reconnection_timeout':10,'users':{'admins':['alice',{'bad':'object'},'alice'],'banned_users':['old-ban'],'other':['drop']},'event_handling':{'load_event_handlers':False,'event_handlers_file_name':'event_handlers.py'},'license_name':'name','license_key':'key','unknown_teamtalk':'drop'},
            'services':{'default_service':'yt','vk':{'enabled':True,'token':'vk-secret'},'yam':{'enabled':True,'token':'yam-secret'},'yt':{'enabled':True,'cookiefile_path':'/home/ttbot/data/cookies.txt'},'youtube':{'api_key':'unsupported-secret'}},
            'logger':{'log':True,'level':'INFO','format':'legacy-format','mode':'FILE','file_name':'TTMediaBot.log','max_file_size':0,'backup_count':0},
            'shortening':{'shorten_links':False,'service':'clckru','service_params':{}},
        }
        (bot/'config.json').write_text(json.dumps(legacy), encoding='utf-8')
        (bot/'limit.txt').write_text('--cpus nope --memory ../../etc/passwd\n', encoding='utf-8')
        cp=subprocess.run([sys.executable,str(ROOT/'tools/migrate_ttmediabot.py'),'--source',str(source),'--dest-root',str(dest),'--template',str(template),'--mode','player','--yes'],capture_output=True,text=True,timeout=20)
        good=cp.returncode==0
        cfg=configparser.ConfigParser(interpolation=None); cfg.read(dest/'LegacyBot'/'config.ini',encoding='utf-8')
        good=good and cfg.get('bot','language')=='th' and cfg.get('bot','nickname')=='SN TalkBot'
        good=good and cfg.getint('playback','default_volume')==80 and cfg.getint('playback','max_volume')==150 and cfg.getint('playback','seek_step')==7 and cfg.getboolean('playback','fade_enabled') is True and cfg.getint('playback','volume_fading')==0
        good=good and cfg.getint('server','udp_port')==10333 and cfg.getboolean('server','encrypted') is True
        good=good and cfg.get('accounts','authorized_users')=='alice'
        good=good and not (dest/'LegacyBot'/'limits.conf').exists()
        good=good and not (dest/'LegacyBot'/'legacy-config.json').exists()
        reports=list((dest/'.migration-reports').glob('*.json'))
        report_text=reports[0].read_text(encoding='utf-8') if reports else ''
        good=good and all(x in report_text for x in ('general.legacy_only','general.cache_file_name','sound_devices.output_device','player.volume_fading_interval','teamtalk.users.banned_users','teamtalk.event_handling.load_event_handlers','services.vk.token','logger.file_name','shortening.service'))
        good=good and all(secret not in report_text for secret in ('unsupported-secret','legacy-secret','vk-secret','yam-secret'))
        template_cfg=configparser.ConfigParser(interpolation=None); template_cfg.read(template,encoding='utf-8')
        good=good and {(sec,key) for sec in cfg.sections() for key in cfg[sec]} == {(sec,key) for sec in template_cfg.sections() for key in template_cfg[sec]}
        need(good, 'TTMediaBot migration is template-first, allowlisted, type-safe, drops unsupported/raw legacy values and fills current defaults')
        if not good:
            print('[DETAIL] migration stdout:',cp.stdout); print('[DETAIL] migration stderr:',cp.stderr)

        # Already-migrated config repair regression.
        migrated=dest/'LegacyBot'; current=configparser.ConfigParser(interpolation=None); current.read(migrated/'config.ini',encoding='utf-8')
        current.set('server','tcp_port','10333.0'); current.set('server','udp_port','70000')
        current.set('server','password','do-not-log-this-secret')
        current.set('features','server_management_enabled','nonsense')
        current.set('playback','default_volume','55.0'); current.set('playback','max_volume','wrong')
        current.set('playback','send_channel_messages','1'); current.remove_option('playback','seek_step')
        current.set('bot','blocked_commands','[/bad object]'); current.set('accounts','authorized_users','alice, alice, bob')
        current.set('playback','legacy_stale_key','drop'); current.add_section('legacy_extra'); current.set('legacy_extra','token','secret-legacy-extra')
        with (migrated/'config.ini').open('w',encoding='utf-8') as fh: current.write(fh)
        repair=subprocess.run([sys.executable,str(ROOT/'tools/migrate_ttmediabot.py'),'--repair-existing','--dest-root',str(dest),'--template',str(template)],capture_output=True,text=True,timeout=20)
        fixed=configparser.ConfigParser(interpolation=None); fixed.read(migrated/'config.ini',encoding='utf-8')
        repair_reports=sorted((dest/'.migration-reports').glob('ttmediabot-repair-*.json'))
        repair_text=repair_reports[-1].read_text(encoding='utf-8') if repair_reports else ''
        repair_good=repair.returncode==0 and fixed.getint('server','tcp_port')==10333 and fixed.getint('server','udp_port')==10333
        repair_good=repair_good and fixed.get('server','password')=='do-not-log-this-secret' and fixed.getboolean('features','server_management_enabled') is False
        repair_good=repair_good and fixed.getint('playback','default_volume')==55 and fixed.getint('playback','max_volume')==150 and fixed.getint('playback','seek_step')==5 and fixed.getboolean('playback','send_channel_messages') is True
        repair_good=repair_good and fixed.get('bot','blocked_commands')=='' and fixed.get('accounts','authorized_users')=='alice,bob'
        repair_good=repair_good and not fixed.has_option('playback','legacy_stale_key') and not fixed.has_section('legacy_extra')
        repair_good=repair_good and bool(list((dest/'.migration-repair-backups').rglob('config.ini'))) and 'do-not-log-this-secret' not in repair_text and 'secret-legacy-extra' not in repair_text
        repair_good=repair_good and 'playback.default_volume' in repair_text and 'playback.max_volume' in repair_text and 'playback.legacy_stale_key' in repair_text
        need(repair_good, 'previously migrated configs auto-repair against current schema with backup, safe coercion/defaults and secret-free report')
        if not repair_good:
            print('[DETAIL] repair stdout:',repair.stdout); print('[DETAIL] repair stderr:',repair.stderr); print('[DETAIL] repair report:',repair_text)
except Exception as exc:
    need(False, f'TTMediaBot schema migration regression: {exc!r}')
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

# Linux runtime regression: a same-name Docker container that lacks TTUHelper
# ownership labels must never be removed or have its logs exposed. This test uses
# a fake docker executable and therefore does not touch the host Docker daemon.
if os.name != 'nt' and bash:
    import tempfile
    try:
        with tempfile.TemporaryDirectory() as td:
            t=Path(td); bindir=t/'bin'; bindir.mkdir(); bots=t/'bots'; inst=bots/'collision'; inst.mkdir(parents=True)
            (inst/'config.ini').write_text('[server]\naddress=example\n', encoding='utf-8')
            (inst/'instance.conf').write_text('image=nuttawat0295/sntalkbot:latest\n', encoding='utf-8')
            marker=t/'docker-actions.log'
            fake=bindir/'docker'
            fake_script = """#!/usr/bin/env bash
set -u
printf '%s\\n' \"$*\" >> \"${TTU_TEST_MARKER:?}\"
if [[ \"${1:-}\" == \"container\" && \"${2:-}\" == \"inspect\" ]]; then exit 0; fi
if [[ \"${1:-}\" == \"inspect\" && \"${2:-}\" == \"-f\" ]]; then
  if [[ \"${3:-}\" == *Config.Labels* ]]; then printf 'false|other-service|/srv/other\\n'; else printf 'true\\n'; fi
  exit 0
fi
if [[ \"${1:-}\" == \"rm\" || \"${1:-}\" == \"logs\" ]]; then exit 0; fi
exit 0
"""
            fake.write_text(fake_script, encoding='utf-8'); fake.chmod(0o755)
            fake_systemctl=bindir/'systemctl'
            fake_systemctl.write_text('#!/usr/bin/env bash\nexit 0\n', encoding='utf-8'); fake_systemctl.chmod(0o755)
            env=os.environ.copy(); env.update({'PATH':str(bindir)+os.pathsep+env.get('PATH',''),'TTU_BOTS_ROOT':str(bots),'TTU_TEST_MARKER':str(marker),'TTU_HELPER_CONFIG':str(t/'missing.conf')})
            results=[]
            for args in (('stop','collision'),('restart','collision'),('delete','collision','--yes'),('logs','collision')):
                cp=subprocess.run([bash,str(ROOT/'ttuhelper.sh'),*args],env=env,capture_output=True,text=True,timeout=15)
                results.append(cp)
            calls=marker.read_text(encoding='utf-8') if marker.exists() else ''
            safe=all(cp.returncode != 0 and 'Refusing to touch Docker container' in (cp.stderr+cp.stdout) for cp in results)
            safe=safe and '\nrm ' not in '\n'+calls and '\nlogs ' not in '\n'+calls and inst.is_dir()
            need(safe, 'same-name unmanaged Docker container is refused by stop/restart/delete/logs without destructive Docker calls')
            if not safe:
                print('[DETAIL] fake docker calls:\n'+calls)
                for cp in results: print('[DETAIL]',cp.returncode,cp.stdout,cp.stderr)
    except Exception as exc:
        need(False, f'unmanaged Docker collision runtime regression: {exc!r}')
else:
    print('[INFO] unmanaged Docker collision runtime regression deferred to Linux validator')

# Linux release files must remain LF-only.  This catches Windows checkout/ZIP
# regressions before they become /bin/bash ^M failures on the server.
crlf=[]
for path in ROOT.rglob('*'):
    if not path.is_file() or '.git' in path.parts or '__pycache__' in path.parts:
        continue
    if path.suffix.lower() not in {'.sh','.py','.md','.txt','.conf','.example'} and path.name not in {'VERSION','.gitattributes'}:
        continue
    if b'\r\n' in path.read_bytes():
        crlf.append(str(path.relative_to(ROOT)))
need(not crlf, 'Linux/helper source line endings are LF-only')
if crlf:
    print('[DETAIL] CRLF files: '+', '.join(crlf[:12]))
raise SystemExit(1 if errors else 0)
