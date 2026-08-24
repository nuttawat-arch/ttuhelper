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
