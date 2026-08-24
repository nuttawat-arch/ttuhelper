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
