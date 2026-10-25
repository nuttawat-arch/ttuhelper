#!/usr/bin/env python3
"""Explicit local recovery from same-instance repair backups. Preview by default."""
import argparse
import os
from pathlib import Path
import re
import shutil
import tempfile
from datetime import datetime, timezone
from migrate_ttmediabot import _read_ini, _ini_string, normalize_connection, connection_errors, config_lock, IDENTITY_KEYS


def recover(root, name, apply=False):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,62}', name):
        raise ValueError('Invalid instance name')
    root = Path(root).resolve(); instance = root / name
    if not instance.is_dir() or instance.is_symlink():
        raise ValueError('Instance not found')
    candidates = sorted((root / '.migration-repair-backups').glob('*/' + name + '/config.ini'), key=lambda p:p.stat().st_mtime_ns, reverse=True)
    for backup in candidates:
        try:
            saved = _read_ini(backup); normalize_connection(saved)
            if connection_errors(saved):
                continue
        except Exception:
            continue
        # Only connection identity is restored; current playback settings survive.
        try:
            current = _read_ini(instance/'config.ini')
            if not connection_errors(current):
                raise ValueError('Current connection config is valid; recovery refused')
        except (OSError, __import__('configparser').Error):
            current = saved
        for section, key in IDENTITY_KEYS:
            if saved.has_option(section, key):
                if not current.has_section(section): current.add_section(section)
                current.set(section, key, saved.get(section, key, raw=True))
        print('Valid same-instance backup found: ' + str(backup.relative_to(root)))
        print('Connection fields can be recovered; no credentials are printed.')
        if not apply:
            print('Preview only. Add --apply to restore connection fields.'); return True
        with config_lock(instance):
            # Rebase under the same lock used by bot/web/repair writers.
            try:
                current = _read_ini(instance/'config.ini')
                if not connection_errors(current):
                    raise ValueError('Current connection config is valid; recovery refused')
            except (OSError, __import__('configparser').Error):
                current = saved
            for section, key in IDENTITY_KEYS:
                if saved.has_option(section, key):
                    if not current.has_section(section): current.add_section(section)
                    current.set(section, key, saved.get(section, key, raw=True))
            before = instance/'config.ini'
            previous = root/'Document/Recovery'/name/'before-recovery.ini'
            previous.parent.mkdir(parents=True,exist_ok=True);previous.parent.chmod(0o700)
            if before.exists(): shutil.copy2(before, previous);previous.chmod(0o600)
            fd, temporary = tempfile.mkstemp(prefix='.recover-',dir=instance)
            try:
                with os.fdopen(fd,'w',encoding='utf-8') as handle:
                    handle.write(_ini_string(current));handle.flush();os.fsync(handle.fileno())
                os.chmod(temporary,0o660)
                if os.name != 'nt' and os.geteuid()==0:
                    info=instance.stat();os.chown(temporary,info.st_uid,info.st_gid)
                os.replace(temporary,before)
            finally:
                Path(temporary).unlink(missing_ok=True)
        print('Connection fields restored. Restart this instance after reviewing config.');return True
    raise ValueError('No valid same-instance backup found. Enter the actual connection settings in Manager; no defaults were written.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bots-root',default='/opt/sntalkbot-bots');parser.add_argument('--instance',required=True)
    parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    try: recover(args.bots_root,args.instance,args.apply)
    except ValueError as exc: parser.exit(1,str(exc)+'\n')
