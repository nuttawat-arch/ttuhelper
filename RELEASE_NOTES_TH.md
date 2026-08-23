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
