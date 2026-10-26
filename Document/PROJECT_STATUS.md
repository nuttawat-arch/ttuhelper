# ttuhelper 1.5.10

## รอบ SNTalkBot Remote Console (ไม่เปลี่ยน Production Helper)

- **DONE:** ตรวจ API port/token และ Docker/instance lifecycle ว่ายังรองรับ Web Manager/TeamTalk actions ใหม่บน loopback เดิม
- **DONE:** ปรับเฉพาะ offline validator fixture ให้จำลอง `chown`/`install` โดยไม่ต้องอาศัย UID mapping ของ CI; production command ไม่เปลี่ยน
- **DONE:** `validate_helper.py` ผ่าน รวม batch update/queue preflight; unit tests ผ่านเมื่อรันในสภาพแวดล้อมเขียน temporary files ได้
- **DOING:** รอทดสอบร่วมบน Linux/Docker staging กับ Bot + Web Manager เวอร์ชันที่ปรับแล้ว
- **TODO:** ไม่ต้องเพิ่ม privileged bridge action สำหรับ TeamTalk SDK controls (จงเก็บเป็น local Bot API ต่อไป)

รอบ 26 ตุลาคม 2026: config safety และ Web Controls เสร็จแล้ว ดูรายละเอียดการแก้ วิธีใช้ และข้อจำกัดที่ [AUDIT_AND_CONTROLS_TH.md](AUDIT_AND_CONTROLS_TH.md)

สถานะ validation ผ่านแบบ offline; ต้องตรวจ TeamTalk/YouTube/PulseAudio/libmpv/NVDA บนเครื่องจริงก่อนรับรองการใช้งานจริงครบทุกกรณี
