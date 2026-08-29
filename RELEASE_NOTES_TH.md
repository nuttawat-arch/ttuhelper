# TTUHelper 1.5.6 — 5.1.13 Config Schema Cleanup

- ใช้ SNTalkBot 5.1.13 `config_default.ini` เป็น schema authority ระหว่าง create/repair/update จึงไม่คง key ของ legacy `messages.txt` scheduler ที่ถูกถอดแล้ว
- TTMediaBot migration ยังคงรองรับ `config.json` แบบ legacy เป็น input one-shot และเขียน migration report JSON เพื่อ audit เท่านั้น; ไม่ใช้ JSON เป็น realtime runtime state
- ถอด range rule ของ `random_message_interval`; ค่าที่ต้อง preserve จะถูก SNTalkBot 5.1.13 migrate ไป `[global_broadcast]` ตาม contract ใหม่
- command count และ batch update/queue-preservation contract เดิมยังคง 22 commands

# TTUHelper 1.5.5 — Legacy Channel ID Migration Compatibility

- หน้าสร้าง instance รับ Channel ID หรือ full channel path ในช่องเดียว
- migration regression ล็อกเคส TTMediaBot `teamtalk.channel = 8` ให้คงเป็น `default_channel = 8` โดยไม่บังคับแปลงชื่อห้อง
- พฤติกรรม queue-preservation/batch update จาก 1.5.4 คงเดิม

# TTUHelper 1.5.4 — Safe Batch Update / Persistent Queue Preflight

- `update` ตรวจ config และความสามารถในการรักษาคิวของทุก running instance ให้ผ่านก่อนหยุดบอตตัวแรก
- SNTalkBot 5.1.8+ ตรวจ `state.sqlite3` ด้วย SQLite `quick_check` และเทียบ queue count กับ local API; legacy 5.1.7 จะบล็อก update หาก API export รายละเอียดไม่ครบ เช่น count 600 แต่เห็นเพียง 250
- เมื่อ preflight ผ่านจึงหยุด instance ทั้งชุดก่อน แล้ว recreate/start แบบ concurrent ลดอาการบอตทยอยออก/เข้า
- แก้ queue-preflight JSON parsing และ cleanup trap ที่อาจเกิด `unbound variable` หลังงานสำเร็จ
- config migration ใช้ `config_default.ini` ปัจจุบันเป็น authoritative optional schema และย้าย Telegram settings เก่าไป `[telegram]` โดยไม่พิมพ์ secret
- public commands ยังคง 22 คำสั่งเดิม

# TTUHelper 1.5.3 — TTMediaBot Migration Self-Repair

- Migration เป็น template-first + allowlist mapping ตาม config v1 จริง ไม่ copy raw config
- player.volume_fading แบบ boolean map ไป fade_enabled; volume_fading_interval ของ legacy ไม่มี semantic equivalent จึงทิ้ง
- installer หลัง pull image จะตรวจ instance ที่เคย migrate แล้วและซ่อม config.ini ตาม schema ปัจจุบันอัตโนมัติ
- ก่อนเขียน config ที่ซ่อมจะ backup ไว้ใต้ .migration-repair-backups; report เก็บเฉพาะชื่อ field/action ไม่เก็บ secret
- run/restart ของ migrated instance จะตรวจ repair อีกครั้งก่อนสร้าง container
- คำสั่งสาธารณะยังคง 22 คำสั่งเดิม ไม่มี public command ใหม่

---

# TTUHelper 1.5.2

## การเปลี่ยนแปลง

- เพิ่ม Docker ownership guard ก่อน `run`, `stop`, `restart`, `delete` และ `logs` เพื่อไม่แตะ container ของบริการอื่นเมื่อชื่อชนกับ SNTalkBot instance
- การชนชื่อกับ container ที่ไม่มี label ของ TTUHelper จะถูกปฏิเสธอย่างชัดเจน; `ls` แสดง `name-conflict-unmanaged`
- คง public command catalog 22 คำสั่งเดิมครบถ้วน

---

# TTUHelper 1.5.1

## การเปลี่ยนแปลง

- คงคำสั่งหลัก 22 คำสั่งและพฤติกรรม instance เดิมทั้งหมด; รุ่นนี้เน้น Linux/release hardening สำหรับการ deploy ร่วมกับ SNTalkBot 5.1.1 และ Web Manager 1.1.1
- เพิ่ม validator ตรวจ LF-only สำหรับ Bash/Python/config/docs ที่ถูกใช้บน Linux เพื่อกัน `^M`/CRLF regression ก่อน publish
- เพิ่มคู่มือ recovery เมื่อ `git pull --ff-only` พบ local changes ใน `/opt/ttuhelper`: ต้องบันทึก diff/สำรองก่อน แล้วค่อย reset ไป `origin/main` แทนการลบไฟล์หรือทับ config แบบสุ่ม
- ยืนยัน `/etc/default/ttuhelper` และ `/opt/sntalkbot-bots/` เป็น persistent production state และ installer ไม่เขียนทับค่าที่มีอยู่

## ปัญหาที่ตรวจพบจากรุ่นก่อน

- บน production รอบ 1.5.0 `git pull --ff-only` หยุดเพราะ `install.sh` และ `ttuhelper.sh` มี local changes ค้างอยู่ แต่ `install.sh`, Docker pull และ `ttuhelper doctor` ที่รันจากไฟล์ปัจจุบันสำเร็จ

## สถานะการตรวจ

- ต้องผ่าน 22-command catalog, Bash syntax จริง, Docker/API allocator invariants และ LF-only check ก่อน publish

---

# TTUHelper 1.5.0

- เพิ่ม `ttuhelper delete <name>`: CLI ต้องยืนยันชื่อ instance ตรงทุกตัวอักษรก่อนลบ; Web Manager ใช้ `--yes` ได้หลังยืนยันจากหน้าเว็บ และระบบสำรอง config/data แบบ root-only ก่อนลบ
- เพิ่มพอร์ต Realtime API ต่อ instance สำหรับ SNTalkBot 5.1.0 โดยเลือกอัตโนมัติจาก `20000-27999`, ตรวจทั้งพอร์ตที่ถูกจองและ socket บน `127.0.0.1`, พร้อม `flock` กันการสร้างพร้อมกันแล้วได้พอร์ตซ้ำ
- สร้าง API token แยกต่อ instance และส่งให้ container ผ่าน environment; พอร์ต/API bind/token ถูกเก็บใน metadata ของ instance ไม่ใช่ `config.ini` ของ TeamTalk
- ปรับ Linux shared-data layout ให้โฟลเดอร์ใช้ group/setgid ที่สม่ำเสมอ เพื่อให้ SNTalkBot container และ Web Manager เขียน config/data ร่วมกันได้โดยไม่ย้อนกลับไปเจอ permission regression
- Installer ทำ preflight ก่อนติดตั้ง `curl`, `python3`, `flock`, CA certificates และ Docker; ถ้ามีอยู่แล้วจะข้ามและติดตั้งเฉพาะสิ่งที่ขาด
- `doctor`, `ls`, `ps`, `run`, `restart`, `update` และคำสั่งเดิมยังรักษาข้อมูล persistent ของแต่ละ instance ตามเดิม
- จำนวนคำสั่งหลัก TTUHelper เพิ่มเป็น 22 คำสั่ง

# TTUHelper 1.4.0

- เอกสารติดตั้งรองรับทั้งดาวน์โหลด ZIP จากหน้า Download และ `git clone` จาก GitHub
- คู่มือ cookies อธิบายการเลือก browser profile, `-ListProfiles`, profile path และ private/incognito export อย่างละเอียด

- `ttuhelper cks <name> [file]` รับไฟล์ Netscape cookies โดยตรงหรือใช้โหมด paste แบบเดิม
- `ttuhelper cks-all [file]` รองรับไฟล์เดียวสำหรับหลาย instance
- เพิ่ม `ttuhelper cks-check <name>` ตรวจ format/จำนวน record โดยไม่แสดงค่า cookie
- รองรับ Netscape `#HttpOnly_` records และแปลง CRLF จาก Windows เป็น LF ก่อนติดตั้ง
- หลังเปลี่ยน cookies จะแนะนำให้ restart instance เพื่อให้ yt-dlp reload session
- ย้ำว่าคุกกี้จริงอยู่ใน persistent data ไม่อยู่ใน Docker image/Git
- Cookie commands แยก role: `cks`/`cks-check` ใช้ Player/Full และ `cks-all` ข้าม Server Manager อัตโนมัติ

# TTUHelper 1.3.0

- เพิ่ม `ttuhelper migrate-ttmediabot [path]` สำหรับย้ายเฉพาะ TTMediaBot Docker Helper `config.json` v1
- เลือกโหมด Player / Server Manager / Full แบบทั้งชุดหรือทีละบอตได้
- แปลง config เป็น `config.ini` ล่าสุดจาก Docker image, คัดลอก cookies และเก็บ source เก่าไว้เป็น backup
- เพิ่ม `--dry-run` และสำรอง destination เดิมก่อนแทนที่

# TTUHelper 1.2.0

- เปลี่ยนชื่อในข้อความ help เป็น SNTalkBot Docker Helper (TTUHelper)
- เพิ่ม `ttuhelper version`
- ปรับ `ttuhelper help` ให้บอกหน้าที่ของทุกคำสั่งชัดเจน
- `help` และ `version` เรียกดูได้โดยไม่ต้องเป็น root
- ตัว installer ถ้า `apt-get update` ล้ม จะแจ้งวิธีรับมือกรณี repository เปลี่ยน Origin/Label/Suite แทนการหยุดแบบไม่บอกแนวทาง
- ปรับ `tools/git_sync_both.ps1` ให้ default path ของ SNTalkBot ตรงกับ `D:\SNTalkBot-Complete-Package\sntalkbot`
- ไม่เพิ่ม Telegram token หรือ secret ใด ๆ ลง helper
