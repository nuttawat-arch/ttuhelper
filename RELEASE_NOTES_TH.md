# TTUHelper 1.2.0

- เปลี่ยนชื่อในข้อความ help เป็น SNTalkBot Docker Helper (TTUHelper)
- เพิ่ม `ttuhelper version`
- ปรับ `ttuhelper help` ให้บอกหน้าที่ของทุกคำสั่งชัดเจน
- `help` และ `version` เรียกดูได้โดยไม่ต้องเป็น root
- ตัว installer ถ้า `apt-get update` ล้ม จะแจ้งวิธีรับมือกรณี repository เปลี่ยน Origin/Label/Suite แทนการหยุดแบบไม่บอกแนวทาง
- ปรับ `tools/git_sync_both.ps1` ให้ default path ของ SNTalkBot ตรงกับ `D:\SNTalkBot-Complete-Package\sntalkbot`
- ไม่เพิ่ม Telegram token หรือ secret ใด ๆ ลง helper
