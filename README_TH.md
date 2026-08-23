# TTUHelper — ตัวช่วยจัดการ SNTalkBot บน Linux/Docker

TTUHelper ใช้สร้างและจัดการ SNTalkBot หลาย instance จาก Docker image เดียว แต่ละ instance มี `config.ini`, cookies, cache, favorites และข้อมูลของตัวเอง

ค่าเริ่มต้น:

```text
Image: nuttawat0295/sntalkbot:latest
Data root: /opt/sntalkbot-bots
Config helper: /etc/default/ttuhelper
Command: /usr/local/bin/ttuhelper
```

ตัวติดตั้งไม่ลบหรือเขียนทับคำสั่ง `tthelper` ของระบบเก่า

## ติดตั้ง

```bash
git clone https://github.com/nuttawat-arch/ttuhelper.git
cd ttuhelper
chmod +x install.sh ttuhelper.sh
sudo ./install.sh
sudo ttuhelper doctor
```

ถ้า `apt-get update` แจ้งว่า repository เปลี่ยน `Origin/Label/Suite` ให้ตรวจว่าเป็น repository ที่คุณใช้อยู่จริง แล้วรัน:

```bash
sudo apt-get update --allow-releaseinfo-change
sudo ./install.sh
```

## สร้างบอต

```bash
sudo ttuhelper new
```

เลือกโหมด:

```text
1 = Full Bot
2 = Player Bot
3 = Server Manager
```

เริ่มบอต:

```bash
sudo ttuhelper run <ชื่อบอต>
```

## คำสั่งทั้งหมด

| คำสั่ง | ใช้ทำอะไร |
|---|---|
| `ttuhelper new` | สร้าง instance ใหม่และเลือกโหมด Full / Player / Server Manager |
| `ttuhelper run <name>` | เริ่มบอตจาก config/data ของ instance นั้น |
| `ttuhelper stop <name>` | หยุดและลบ container แต่เก็บ config/data ไว้ |
| `ttuhelper restart <name>` | รีสตาร์ตบอตหนึ่งตัวโดยสร้าง container ใหม่ |
| `ttuhelper logs <name>` | ดูบันทึกการทำงานแบบสด กด `Ctrl+C` เพื่อออก |
| `ttuhelper ls` | ดูรายชื่อ instance ทั้งหมดพร้อมสถานะ running/stopped |
| `ttuhelper ps` | ดู container ที่ TTUHelper จัดการ พร้อมสถานะและ image |
| `ttuhelper start-all` | เริ่มทุก instance ที่มี `config.ini` |
| `ttuhelper stop-all` | หยุด container ทุกตัวโดยไม่ลบข้อมูลถาวร |
| `ttuhelper pull` | ดาวน์โหลด Docker image/tag ที่ตั้งไว้ |
| `ttuhelper update` | pull image ใหม่ แล้วอัปเดตเฉพาะ instance ที่กำลังรัน โดยรักษาข้อมูลเดิม |
| `ttuhelper cks <name>` | แทนที่ `cookies.txt` ของ instance หนึ่งตัว |
| `ttuhelper cks-all` | ใส่ cookies ชุดเดียวให้ทุก instance |
| `ttuhelper limit <name>` | ตั้งข้อจำกัด CPU/RAM มีผลหลัง restart |
| `ttuhelper edit <name>` | เปิด `config.ini` ค่าเริ่มต้นใช้ `nano` |
| `ttuhelper path <name>` | แสดงตำแหน่งโฟลเดอร์ config/data ของ instance |
| `ttuhelper doctor` | ตรวจ Docker daemon, image, data root และค่าหลักของ helper |
| `ttuhelper version` | แสดงเวอร์ชัน TTUHelper |
| `ttuhelper help` | แสดงคำอธิบายคำสั่งทั้งหมด |

## ดู log

```bash
sudo ttuhelper logs <ชื่อบอต>
```

กด `Ctrl+C` เพื่อออกจากการดู log บอตยังทำงานต่อ

## แก้ config แล้วรีสตาร์ต

```bash
sudo ttuhelper edit <ชื่อบอต>
sudo ttuhelper restart <ชื่อบอต>
```

## อัปเดต Docker image

```bash
sudo ttuhelper update
```

คำสั่งนี้จะ:

1. จำ instance ที่กำลังรัน
2. pull image/tag ที่กำหนด
3. recreate เฉพาะ instance เหล่านั้น
4. mount config/data เดิมกลับเข้า container ใหม่

instance ที่หยุดอยู่จะยังคงหยุดอยู่

## เปลี่ยน image/tag

แก้:

```bash
sudo nano /etc/default/ttuhelper
```

ตัวอย่าง:

```text
TTU_IMAGE_REPO="nuttawat0295/sntalkbot"
TTU_TAG="2026.08.23-r6"
TTU_BOTS_ROOT="/opt/sntalkbot-bots"
```

แล้ว:

```bash
sudo ttuhelper pull
sudo ttuhelper update
```

## แหล่งทางการ

- SNTalkBot: https://github.com/nuttawat-arch/sntalkbot
- TTUHelper: https://github.com/nuttawat-arch/ttuhelper
- Docker Hub: https://hub.docker.com/r/nuttawat0295/sntalkbot
- Download: https://ttdl.nuttawat.ddnsfree.com
