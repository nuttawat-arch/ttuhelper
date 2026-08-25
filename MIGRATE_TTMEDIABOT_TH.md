# ย้ายจาก TTMediaBot Docker Helper เก่ามา SNTalkBot

> รองรับเฉพาะ TTMediaBot Docker Helper ที่แต่ละบอตมี `config.json` แบบ `config_version: 1` เท่านั้น การย้ายเป็น **schema translation** ไม่ใช่การคัดลอก config เก่าทั้งไฟล์

## หลักของ TTUHelper 1.5.3

1. ดึง `config_default.ini` จาก SNTalkBot image ปัจจุบันมาเป็น schema หลัก
2. เติมทุก section/key ของ SNTalkBot จาก default ก่อน
3. นำเข้าเฉพาะค่า TTMediaBot ที่มีความหมายตรงและผ่านการตรวจชนิด/ช่วง
4. ค่า legacy ที่ SNTalkBot ไม่มีจะถูกทิ้ง
5. field ปัจจุบันที่ TTMediaBot ไม่มีจะคง default ของ SNTalkBot
6. `config.json` เก่าไม่ถูกคัดลอกเข้า runtime instance; โฟลเดอร์ TTMediaBot ต้นทางยังอยู่เป็น backup

## Field จาก TTMediaBot config v1 ที่นำเข้า

- `general.language` → ภาษาบอต เมื่อเป็นภาษาที่ SNTalkBot รองรับ
- `general.send_channel_messages` → การส่งข้อความ Player ในห้อง
- `general.blocked_commands` → blocked commands โดยกรองเฉพาะ command token ที่ปลอดภัย
- `player.default_volume`, `max_volume`, `seek_step` → ค่า Player หลังตรวจช่วง
- `player.volume_fading` (boolean) → `fade_enabled`; `volume_fading_interval` ไม่มี semantic equivalent จึงไม่ย้าย
- `teamtalk.hostname`, `tcp_port`, `udp_port`, `encrypted` → การเชื่อมต่อ TeamTalk
- `teamtalk.username`, `password`, `nickname`, `channel`, `channel_password`, `status`, `gender`
- `teamtalk.reconnection_attempts`, `reconnection_timeout`
- `teamtalk.users.admins` → authorized users
- `teamtalk.license_name`, `license_key` → TeamTalk SDK license
- `cookies.txt` → คัดลอกเป็นไฟล์ cookies ของ instance ถ้ามี

## ค่า legacy ที่ตั้งใจไม่ย้าย

- `general.cache_file_name`, `delete_uploaded_files_after`, `time_format`, `start_commands`
- `sound_devices.input_device/output_device` — Docker รุ่นใหม่ใช้ `auto`
- `player.volume_fading_interval`, `player.player_options`
- `teamtalk.users.banned_users` และ `teamtalk.event_handling.*`
- `services.*` รวม token/path ของ VK/Yandex/YouTube เก่า; SNTalkBot ใช้ service/config ของตนเอง และ cookies ใช้ `/app/data/cookies.txt`
- `logger.*`, `shortening.*`
- `TTMediaBot.log`, `TTMediaBotCache.dat`

รายการที่ไม่ย้ายยังอยู่ในโฟลเดอร์ TTMediaBot ต้นทางซึ่งระบบไม่ลบ

## ทดลองดูก่อน

```bash
sudo ttuhelper migrate-ttmediabot /opt/ttmediabot-docker-helper --dry-run
```

ตรวจรายชื่อบอตและประเภทให้ถูกต้องก่อนย้ายจริง

## ย้ายจริง

```bash
sudo ttuhelper migrate-ttmediabot /opt/ttmediabot-docker-helper
```

หรือพิมพ์ `sudo ttuhelper migrate-ttmediabot` แล้วกรอก path เมื่อระบบถาม

Helper ให้เลือก:

```text
1) Player Bot ทุกตัว
2) Server Manager ทุกตัว
3) Full Bot ทุกตัว
4) เลือกประเภททีละตัว
```

ถ้าบอตเก่าเป็น media player ให้เลือก Player ได้ตามหน้าที่จริงของบอต

## ตำแหน่งหลังย้าย

```text
/opt/sntalkbot-bots/<ชื่อเดิม>/
  config.ini
  cookies.txt
  instance.conf
  MIGRATED_FROM_TTMEDIABOT.txt
```

ไม่มี `legacy-config.json` ใน runtime instance เพราะ raw source อยู่ที่โฟลเดอร์ TTMediaBot เดิมอยู่แล้ว

## ซ่อม instance ที่เคยย้ายมาแล้ว

TTUHelper 1.5.3 ตรวจเฉพาะ instance ที่มี migration marker โดยอัตโนมัติเมื่อ:

- ติดตั้ง/อัปเดต TTUHelper
- run/restart instance ที่เคย migrate
- update running bots

ก่อนแก้จะ backup `config.ini` ใต้ `.migration-repair-backups/` แล้วเทียบกับ template ปัจจุบัน:

- key/section ที่ขาด → เติม default
- boolean/int/float ที่เขียนผิดชนิดแต่แปลงได้อย่างปลอดภัย → แปลงให้ถูก
- ค่าที่ผิดช่วง/แปลงไม่ได้ → ใช้ default ปัจจุบัน
- `blocked_commands`/`authorized_users` ที่ผิดรูป → sanitize หรือกลับ default
- key/section legacy ที่ไม่มีใน schema → ตัดออก
- role ใน `instance.conf` คงเดิม เช่น Player ยังคง Player

Repair report บันทึกเฉพาะชื่อ field/action ไม่บันทึก password/token/secret

ถ้า `config.ini` เสียจน parse ไม่ได้ ระบบจะพยายาม rebuild จาก `config.json` ในโฟลเดอร์ต้นทางที่ marker ชี้ไว้ หากต้นทางหายด้วย ระบบจะ **ไม่เดา credential** และจะคง config เดิมไว้พร้อมรายงาน failure

## ตรวจหลังย้าย/ซ่อม

```bash
sudo ttuhelper ls
sudo ttuhelper ps
sudo ttuhelper logs <ชื่อบอต>
```

เก็บโฟลเดอร์ TTMediaBot ต้นทางไว้จนตรวจว่า login, join channel, queue/playback และค่าที่ต้องใช้ทำงานครบแล้ว
