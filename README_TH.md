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

เลือกได้ 2 วิธีตามสะดวก

### วิธี A: ดาวน์โหลด ZIP จากหน้า SNTalkBot Download

```bash
sudo apt-get update
sudo apt-get install -y curl unzip
sudo mkdir -p /opt/ttuhelper
sudo curl -fL https://ttdl.nuttawat.ddnsfree.com/downloads/TTUHelper-latest.zip -o /tmp/TTUHelper.zip
sudo unzip -o /tmp/TTUHelper.zip -d /opt/ttuhelper
cd /opt/ttuhelper
sudo chmod +x install.sh ttuhelper.sh
sudo ./install.sh
sudo ttuhelper doctor
```

### วิธี B: Clone source จาก GitHub

```bash
sudo apt-get update
sudo apt-get install -y git
cd /opt
sudo git clone https://github.com/nuttawat-arch/ttuhelper.git
cd /opt/ttuhelper
sudo chmod +x install.sh ttuhelper.sh
sudo ./install.sh
sudo ttuhelper doctor
```

ถ้าเคย clone ไว้แล้ว:

```bash
cd /opt/ttuhelper
sudo git pull --ff-only
sudo ./install.sh
sudo ttuhelper doctor
```

`git pull` ใช้อัปเดต source ของ TTUHelper ส่วน `ttuhelper update` ใช้อัปเดต SNTalkBot Docker image/instance ที่กำลังรัน

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
| `ttuhelper delete <name>` | สำรองแล้วลบ instance; CLI ต้องพิมพ์ชื่อยืนยันตรงทุกตัวอักษร |
| `ttuhelper logs <name>` | ดูบันทึกการทำงานแบบสด กด `Ctrl+C` เพื่อออก |
| `ttuhelper ls` | ดูรายชื่อ instance ทั้งหมดพร้อมสถานะ running/stopped |
| `ttuhelper ps` | ดู container ที่ TTUHelper จัดการ พร้อมสถานะและ image |
| `ttuhelper start-all` | เริ่มทุก instance ที่มี `config.ini` |
| `ttuhelper stop-all` | หยุด container ทุกตัวโดยไม่ลบข้อมูลถาวร |
| `ttuhelper pull` | ดาวน์โหลด Docker image/tag ที่ตั้งไว้ |
| `ttuhelper update` | pull image ใหม่ แล้วอัปเดตเฉพาะ instance ที่กำลังรัน โดยรักษาข้อมูลเดิม |
| `ttuhelper migrate-ttmediabot [path]` | ย้าย TTMediaBot Docker Helper `config.json` v1 ไป SNTalkBot ใหม่ |
| `ttuhelper cks <name> [file]` | แทนที่ `cookies.txt` ของ instance หนึ่งตัวจากไฟล์หรือ stdin |
| `ttuhelper cks-all [file]` | ใส่ cookies ชุดเดียวให้ทุก instance จากไฟล์หรือ stdin |
| `ttuhelper cks-check <name>` | ตรวจรูปแบบและจำนวน cookie โดยไม่แสดงค่า secret |
| `ttuhelper limit <name>` | ตั้งข้อจำกัด CPU/RAM มีผลหลัง restart |
| `ttuhelper edit <name>` | เปิด `config.ini` ค่าเริ่มต้นใช้ `nano` |
| `ttuhelper path <name>` | แสดงตำแหน่งโฟลเดอร์ config/data ของ instance |
| `ttuhelper doctor` | ตรวจ Docker daemon, image, data root และค่าหลักของ helper |
| `ttuhelper version` | แสดงเวอร์ชัน TTUHelper |
| `ttuhelper help` | แสดงคำอธิบายคำสั่งทั้งหมด |

## Realtime API สำหรับ Web Manager

TTUHelper 1.5.0 จัดพอร์ต API ภายในให้แต่ละ instance อัตโนมัติจากช่วง `20000-27999` และ bind เฉพาะ `127.0.0.1` เมื่อใช้ SNTalkBot 5.1.0 ขึ้นไป พอร์ตจะไม่ถูกเลือกซ้ำกับ instance อื่นและมี lock ป้องกันการสร้างพร้อมกัน

ข้อมูลถูกเก็บใน `instance.conf` ของแต่ละ instance เช่น `api_port`, `api_bind` และ token ภายใน ห้ามเปิดช่วง `20000-27999` ผ่าน Firewall/Router และไม่ควร Reverse Proxy API ของบอตออก Internet ให้ Web Manager เป็นผู้เรียก API จาก localhost เท่านั้น

## ลบ instance อย่างปลอดภัย

```bash
sudo ttuhelper delete <ชื่อบอต>
```

CLI จะให้พิมพ์ชื่อ instance ซ้ำเพื่อยืนยัน ก่อนลบ TTUHelper จะหยุด container และสร้าง backup แบบ root-only ใต้ `/opt/sntalkbot-deleted-backups/` แล้วจึงลบโฟลเดอร์ instance ที่ตรวจสอบ path แล้วเท่านั้น


## ย้ายจาก TTMediaBot Docker Helper เก่า

รองรับเฉพาะโครงสร้าง TTMediaBot Docker Helper ที่แต่ละโฟลเดอร์มี `config.json` แบบ `config_version: 1` ไม่รองรับโปรเจกต์เก่าทุกชนิด

```bash
sudo ttuhelper migrate-ttmediabot
```

ค่าเริ่มต้นจะถามหา `/opt/ttmediabot-docker-helper` แล้วให้เลือกว่าจะนำเข้าทุกตัวเป็น Player, Server Manager, Full หรือเลือกทีละตัว ระบบสร้าง `config.ini` ใหม่ใน `/opt/sntalkbot-bots`, คัดลอก `cookies.txt` และสามารถแทน container เดิมด้วย SNTalkBot image ล่าสุดได้ทันที โดยไม่ลบโฟลเดอร์ TTMediaBot เก่า

ทดลองตรวจอย่างเดียว:

```bash
sudo ttuhelper migrate-ttmediabot /opt/ttmediabot-docker-helper --dry-run
```

อ่านรายละเอียด: `MIGRATE_TTMEDIABOT_TH.md`

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


## YouTube cookies

ดูขั้นตอนแบบละเอียดใน `YOUTUBE_COOKIES_TH.md` SNTalkBot มี default cookie bootstrap ให้ Player/Full; `ttuhelper cks` ใช้แทน `/app/data/cookies.txt` ด้วยชุดของผู้ใช้ใน persistent data โดยไม่ถูก default overwrite

## ถ้า `git pull --ff-only` แจ้ง local changes

อย่าลบ `/opt/ttuhelper` หรือ `/opt/sntalkbot-bots` ทิ้งทันที ให้ตรวจและสำรองก่อน:

```bash
cd /opt/ttuhelper
git status --short
git diff -- install.sh ttuhelper.sh | sudo tee /root/ttuhelper-local-before-reset.diff >/dev/null
sudo cp -a /opt/ttuhelper /root/ttuhelper-source-backup-$(date +%Y%m%d-%H%M%S)
git fetch origin
git reset --hard origin/main
sudo ./install.sh
sudo ttuhelper doctor
```

คำสั่ง `git reset --hard` ด้านบนกระทบเฉพาะ Git working tree `/opt/ttuhelper`; ไม่แตะ `/etc/default/ttuhelper` และไม่แตะข้อมูล instance ใน `/opt/sntalkbot-bots/`
