# DEVELOPMENT REPORT — TTUHelper 1.5.3

- ตรวจเทียบกับ TTMediaBot `config.json` v1 ตัวจริงที่ผู้ใช้ส่งมา: general/sound_devices/player/teamtalk/services/logger/shortening ครบ
- field ที่รองรับจริงถูก map 23 path; field ที่ไม่มี semantic equivalent เช่น cache/time/start_commands, device IDs, fade interval, banned users/event handlers, services tokens/path, logger และ shortening ถูกทิ้งโดยตั้งใจ
- ทดสอบแปลงไฟล์ต้นฉบับจริงเป็น Player: schema หลังแปลงตรง `config_default.ini` ปัจจุบันทุก section/key; host/ports/account/channel/volume/admin/fade ถูกแปลงถูกต้อง และ device/cookie path ใช้นโยบาย Docker ปัจจุบัน
- เพิ่ม internal migrated-config repair mode โดยไม่เพิ่ม public command
- ซ่อม wrong-type/missing/stale fields จาก current SNTalkBot template; preserve valid current values, safe-coerce, default invalid, drop unknown
- ถ้า config.ini parse ไม่ได้ จะ rebuild จาก preserved TTMediaBot config.json เมื่อ source ยังอยู่; ถ้าไม่มี source จะไม่เดา credential และจะรายงานว่า repair ไม่สำเร็จโดยคงไฟล์เดิม
- auto repair ทำทั้งตอน install/update helper และก่อน run/restart migrated instance
- regression ครอบคลุม backup, secret-free report, Player role enforcement, range/type coercion และ unknown section removal

---

# DEVELOPMENT REPORT — TTUHelper 1.5.2

วันที่: 2026-08-25

## ปัญหาจากรอบก่อน
- 1.5.1 ใช้ชื่อ Docker container เป็นตัวตัดสินใน run/stop/restart/delete/logs บางเส้นทาง โดยยังไม่ยืนยัน label ว่า container ชื่อนั้นเป็นของ TTUHelper จริง
- หากชื่อ instance ชนกับ Docker container ของบริการอื่น การ stop/restart/delete มีความเสี่ยงไปแตะ container ที่ไม่ใช่ SNTalkBot และ logs อาจอ่าน log ของ container อื่น

## การแก้ไข/ฟีเจอร์
- เพิ่ม `container_is_managed` ตรวจ label `com.ttutilities.helper=true`, `com.ttutilities.bot=<name>` และ data path ให้ตรง instance ก่อนแตะ container
- run/stop/restart/delete ปฏิเสธทันทีเมื่อพบ same-name container ที่ไม่ใช่ TTUHelper
- logs ตรวจทั้ง instance path และ ownership label ก่อนอ่าน Docker logs
- `ls` แสดง `name-conflict-unmanaged` เมื่อพบชื่อชน แทนการรายงานว่าเป็นบอตของเรา
- คงคำสั่ง public 22 คำสั่งเดิมทั้งหมด

## การทดสอบรอบนี้
- validator ตรวจ ownership-label guards, 22-command catalog, cookie safety, API allocator, permissions, Bash syntax และ LF-only
- เพิ่ม regression test แบบ fake Docker เพื่อยืนยันว่า same-name unmanaged container ไม่ถูก `docker rm -f` และไม่ถูกอ่าน logs

## ลบอะไรออก
- ไม่มีคำสั่งหรือฟีเจอร์เดิมถูกลบ

## สถานะ
- ต้อง publish 1.5.2 และอัปเดต `/opt/ttuhelper` ก่อนถือว่า Web Manager destructive actions ปลอดภัยครบ

---

# DEVELOPMENT REPORT — TTUHelper 1.5.1

วันที่: 2026-08-24

## ปัญหาจากรอบก่อน
- Production `/opt/ttuhelper` มี local changes ใน `install.sh` และ `ttuhelper.sh` จึงทำให้ `git pull --ff-only` abort แม้ installer ที่มีอยู่ยังรันได้

## การแก้ไข/ฟีเจอร์
- คง public command catalog 22 คำสั่งเดิมครบถ้วน
- เพิ่มคู่มือ backup/diff แล้ว `git fetch` + `git reset --hard origin/main` อย่างปลอดภัย โดยไม่แตะ `/etc/default/ttuhelper` และ `/opt/sntalkbot-bots`
- เพิ่ม Linux LF-only validation และยืนยัน `bash -n` ทั้ง `ttuhelper.sh`/`install.sh`

## การทดสอบรอบนี้
- validator 22 commands, cookie safety, API allocator, permission/setgid, delete safety และ Bash syntax ผ่าน
- LF-only validation ผ่าน

## ลบอะไรออก
- ไม่มีคำสั่งหรือฟีเจอร์เดิมถูกลบ

## สถานะ
- Source พร้อม publish; production ต้อง sync source ใหม่แล้ว `ttuhelper update` เพื่อ recreate instance ที่กำลังรันด้วย image ใหม่
