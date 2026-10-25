import configparser
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import os
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from migrate_ttmediabot import repair_one_migrated, repair_existing_migrated, _read_ini
from recover_instance_config import recover

TEMPLATE = '''[server]
address=CHANGE_ME
tcp_port=10333
udp_port=10333
username=CHANGE_ME
password=
encrypted=False
[features]
player_enabled=True
server_management_enabled=False
[bot]
default_channel=/
channel_password=
nickname=SN TalkBot
[playback]
default_volume=80
'''
CURRENT = '''[server]
address=real.example.test
tcp_port=29730
udp_port=29731
username=real-bot
password=  pass%Word  
encrypted=True
[features]
player_enabled=True
server_management_enabled=True
[bot]
default_channel=/private-room
channel_password=room%Password
nickname=My Bot
[playback]
default_volume=67
custom_option=keep
'''

class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.template=self.root/'template.ini';self.template.write_text(TEMPLATE)
        self.instance=self.root/'alpha';self.instance.mkdir()
        (self.instance/'instance.conf').write_text('mode=player\nmigrated_from=/nonexistent\n')
        self.path=self.instance/'config.ini';self.path.write_text(CURRENT)

    def test_restart_repair_keeps_identity_role_and_unknown_settings(self):
        before=_read_ini(self.path);result=repair_one_migrated(self.template,self.instance)
        after=configparser.ConfigParser(interpolation=None);after.read_string(result['_new_text'])
        for section in ('server','bot'):
            for key,value in before.items(section):self.assertEqual(after.get(section,key,raw=True),value)
        self.assertTrue(after.getboolean('features','server_management_enabled'))
        self.assertEqual(after.get('playback','custom_option'),'keep')

    def test_legacy_hostname_does_not_become_change_me(self):
        self.path.write_text(CURRENT.replace('address=','hostname='))
        result=repair_one_migrated(self.template,self.instance)
        self.assertFalse(result['failed']);self.assertIn('address = real.example.test',result['_new_text'])

    def test_case_variant_sections_preserve_values(self):
        self.path.write_text(CURRENT.replace('[server]','[Server]'))
        result=repair_one_migrated(self.template,self.instance)
        self.assertFalse(result['failed']);self.assertIn('address = real.example.test',result['_new_text'])

    def test_invalid_port_blocks_without_writing_defaults(self):
        self.path.write_text(CURRENT.replace('29730','70000'));before=self.path.read_bytes()
        result=repair_one_migrated(self.template,self.instance)
        self.assertTrue(result['failed']);self.assertEqual(self.path.read_bytes(),before)

    def test_missing_host_blocks_no_change_me_written(self):
        self.path.write_text(CURRENT.replace('address=real.example.test',''))
        result=repair_one_migrated(self.template,self.instance)
        self.assertTrue(result['failed']);self.assertNotIn('CHANGE_ME',self.path.read_text())

    def test_corrupt_ini_does_not_rebuild_from_old_identity(self):
        self.path.write_text('[server\naddress=real.example.test');before=self.path.read_bytes()
        result=repair_one_migrated(self.template,self.instance)
        self.assertTrue(result['failed']);self.assertEqual(before,self.path.read_bytes())

    def test_repair_is_idempotent_and_reports_no_secrets(self):
        first=repair_existing_migrated(self.template,self.root,'alpha')
        second=repair_existing_migrated(self.template,self.root,'alpha')
        self.assertFalse(second[0]['changed'])
        for p in (self.root/'Document/MigrationReports').glob('*.json'):
            self.assertNotIn('pass%Word',p.read_text())

    @unittest.skipUnless(os.name != 'nt' and hasattr(os,'geteuid') and os.geteuid() == 0 and shutil.which('bash'), 'shell lifecycle test needs Linux root harness')
    def test_restart_blocks_before_stop_for_native_invalid_config(self):
        (self.instance/'instance.conf').unlink()
        self.path.write_text(CURRENT.replace('real.example.test','CHANGE_ME'));before=self.path.read_bytes()
        bindir=self.root/'bin';bindir.mkdir();calls=self.root/'docker-calls'
        scripts={'docker': '#!/bin/sh\necho "$*" >> "$TEST_DOCKER_CALLS"\nexit 0\n',
                 'chown':'#!/bin/sh\nexit 0\n','systemctl':'#!/bin/sh\nexit 0\n'}
        for name,text in scripts.items():
            target=bindir/name;target.write_text(text);target.chmod(0o755)
        env=dict(os.environ,PATH=str(bindir)+os.pathsep+os.environ['PATH'],TTU_BOTS_ROOT=str(self.root),TTU_HELPER_CONFIG=str(self.root/'no-config'),TEST_DOCKER_CALLS=str(calls))
        result=subprocess.run(['bash',str(ROOT/'ttuhelper.sh'),'restart','alpha'],env=env,capture_output=True,text=True,timeout=5)
        self.assertNotEqual(result.returncode,0);self.assertIn('[BLOCKED]',result.stderr)
        self.assertNotIn('rm -f',calls.read_text());self.assertEqual(self.path.read_bytes(),before)

    def test_explicit_recovery_preserves_current_playback(self):
        backup=self.root/'.migration-repair-backups/20260101/alpha';backup.mkdir(parents=True)
        (backup/'config.ini').write_text(CURRENT)
        self.path.write_text(CURRENT.replace('real.example.test','CHANGE_ME').replace('default_volume=67','default_volume=44'))
        before=self.path.read_bytes();self.assertTrue(recover(self.root,'alpha'))
        self.assertEqual(before,self.path.read_bytes())
        self.assertTrue(recover(self.root,'alpha',True))
        cfg=_read_ini(self.path);self.assertEqual(cfg.get('server','address'),'real.example.test')
        self.assertEqual(cfg.getint('playback','default_volume'),44)

if __name__=='__main__':unittest.main()
