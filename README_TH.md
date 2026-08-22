# TTUtilities Docker Helper (ttuhelper) — จัดการหลายบอตบน Linux ด้วย Docker

โฟลเดอร์นี้เป็นฝั่งที่ติดตั้งบน **Ubuntu/Debian Server** หลังจาก image ของ `01-SNTalkBot-DockerHub-Image` ถูก push ไปที่ Docker Hub แล้ว ตัว helper ใช้ Docker image เดียวสร้างบอตได้หลาย instance โดยแต่ละ instance มี `config.ini`, `cookies.txt`, log/cache/favorites และ PulseAudio ภายใน container ของตัวเอง จึงใช้บอตตัวเดียวกันกับ TeamTalk หลายเซิร์ฟเวอร์หรือหลายห้องได้โดยไม่ต้องทำหลาย profile ในโปรแกรมหลัก

ค่าเริ่มต้นใช้ image:

```text
nuttawat0295/sntalkbot:latest
```

เหตุผลที่คง repository นี้ไว้เป็นค่าเริ่มต้น เพราะ helper เดิมของคุณใช้อยู่แล้ว ถ้าจะเปลี่ยน repository/tag ให้แก้ `/etc/default/ttuhelper`

## ชื่อคำสั่งใหม่และการอยู่ร่วมกับ Helper เก่า

โปรเจกต์นี้ใช้คำสั่ง global **`ttuhelper`** และไฟล์โปรแกรม `ttuhelper.sh` โดยตั้งใจไม่ใช้ `tthelper` ของโปรเจกต์เดิม เพื่อให้ติดตั้งสองระบบบน Linux Server เครื่องเดียวกันได้

```text
เก่า: tthelper   -> ปล่อยไว้ให้บอต/ระบบเก่าใช้ต่อ
ใหม่: ttuhelper  -> ใช้จัดการ SN TalkBot
```

ตัวติดตั้งใหม่ **ไม่ลบ ไม่เขียนทับ และไม่สร้าง alias ของ `/usr/local/bin/tthelper`** ถ้าพบของเก่า จะเพียงแจ้งว่าพบแล้วและปล่อยไว้ตามเดิม

ไฟล์ config ของ helper ใหม่อยู่ที่:

```text
/etc/default/ttuhelper
```


## ติดตั้งครั้งแรก — ใช้คำสั่งเดียว

หลัง clone หรือแตกไฟล์บน Ubuntu/Debian Server ให้ `cd` เข้ามาในโฟลเดอร์ `ttuhelper` แล้วรันเพียง:

```bash
sudo ./install.sh
```

คำสั่งเดียวนี้จะติดตั้ง Docker หากยังไม่มี, เปิด Docker service, ติดตั้ง `ttuhelper` เป็นคำสั่ง global ที่ `/usr/local/bin/ttuhelper`, สร้างพื้นที่ `/opt/sntalkbot-bots`, สร้าง `/etc/default/ttuhelper` ในการติดตั้งครั้งแรก และ pull image จาก Docker Hub ให้เสร็จ หากรัน `install.sh` ซ้ำเพื่ออัปเดต helper จะเก็บ `/etc/default/ttuhelper` เดิมไว้ไม่ทับค่า repository/tag ที่คุณตั้งเอง

หลังจากนั้นไม่ต้อง `cd` กลับมาโฟลเดอร์ helper อีก เรียก `sudo ttuhelper ...` ได้จากทุกที่

## สร้างบอตใหม่

```bash
sudo ttuhelper new
```

ระบบจะถามชื่อ instance, nickname, hostname/IP ของ TeamTalk, TCP/UDP port, encrypted connection, username/password, channel, รายชื่อผู้มีสิทธิ์ admin ของบอต และ **โหมดการทำงานของบอต** จากนั้น helper จะดึง `config_default.ini` **จาก Docker image รุ่นที่ใช้อยู่จริง** แล้วสร้าง `config.ini` ของ instance ทำให้ config template ไม่ล้าหลัง source

โหมดที่เลือกได้มี 3 แบบ:

```text
1) Full Bot       = เปิดทั้งระบบเล่นเพลงและระบบจัดการเซิร์ฟเวอร์
2) Player Bot     = เปิดเฉพาะระบบเล่นเพลง/คิว/YouTube/YouTube Music
3) Server Manager = เปิดเฉพาะระบบจัดการเซิร์ฟเวอร์ ไม่มีฟีเจอร์เล่นเพลง
```

helper จะเขียนค่าลงใน `[features]` ของ `config.ini` ดังนี้:

```ini
[features]
player_enabled = True/False
server_management_enabled = True/False
```

โฟลเดอร์แต่ละ instance อยู่ที่:

```text
/opt/sntalkbot-bots/<ชื่อบอต>/
```

## เริ่มบอต

```bash
sudo ttuhelper run <ชื่อบอต>
```

ตัวอย่าง:

```bash
sudo ttuhelper run radio1
sudo ttuhelper run server2
```

แต่ละ container ใช้ data directory ของตัวเองและ `--restart unless-stopped` หากเครื่อง reboot Docker จะนำบอตที่เคยรันกลับขึ้นมาให้อัตโนมัติ

## คำสั่งทั้งหมดของ helper

```text
ttuhelper new                 สร้าง instance ใหม่
ttuhelper run <name>          เริ่ม instance
ttuhelper stop <name>         หยุดและลบ container แต่เก็บ config/data
ttuhelper restart <name>      recreate instance หนึ่งตัว
ttuhelper logs <name>         ดู log แบบสด
ttuhelper ls                  รายชื่อ instance ทั้งหมดและสถานะ
ttuhelper ps                  ดู container ที่ helper จัดการ
ttuhelper start-all           เริ่มทุก instance ที่มี config
ttuhelper stop-all            หยุด container ของ helper ทั้งหมด
ttuhelper pull                pull image ที่กำหนด
ttuhelper update              pull image ใหม่และ recreate เฉพาะบอตที่กำลังรัน
ttuhelper cks <name>          อัปเดต cookies.txt หนึ่ง instance
ttuhelper cks-all             ใส่ cookies ครั้งเดียวให้ทุก instance
ttuhelper limit <name>        จำกัด CPU/RAM ของ instance
ttuhelper edit <name>         แก้ config.ini ผ่าน $EDITOR; ค่าเริ่มต้น nano
ttuhelper path <name>         แสดง path data ของ instance
ttuhelper doctor              ตรวจ Docker, image และค่าของ helper
ttuhelper help                แสดง help
```

## การอัปเดตที่ถูกต้อง

โปรเจกต์ใหม่นี้ถือ Docker image เป็น immutable runtime ดังนั้น `ttuhelper update` **จะไม่เข้าไป pip install ทับ dependency ภายใน container** แบบ helper เก่า แต่จะ:

1. จำรายชื่อ instance ที่กำลังรัน
2. `docker pull` image/tag ล่าสุด
3. recreate container แต่ละตัวด้วย image ใหม่
4. mount โฟลเดอร์ `/opt/sntalkbot-bots/<name>` เดิมกลับเข้าไป

config, cookies, favorites, cache และ log จึงยังอยู่ แต่ runtime code/dependency มาจาก image ชุดเดียวกันทั้งหมด

## YouTube cookies

หนึ่ง instance:

```bash
sudo ttuhelper cks radio1
```

ทุก instance:

```bash
sudo ttuhelper cks-all
```

แปะ cookies แบบ Netscape แล้วกด `Ctrl+D` ไฟล์จะถูกเก็บเป็น `/app/data/cookies.txt` ภายใน container และ `config.ini` ที่ helper สร้างจะชี้ `cookiefile_path` มาที่ไฟล์นี้ให้แล้ว

## เปลี่ยน Docker Hub repository หรือ tag

แก้ไฟล์:

```bash
sudo nano /etc/default/ttuhelper
```

ตัวอย่าง:

```text
TTU_IMAGE_REPO="nuttawat0295/sntalkbot"
TTU_TAG="latest"
TTU_BOTS_ROOT="/opt/sntalkbot-bots"
```

จากนั้น:

```bash
sudo ttuhelper update
```

## หมายเหตุเรื่องระบบเสียง

แต่ละบอตเป็นคนละ Docker container ดังนั้น PulseAudio null sink และ MPV ของแต่ละ instance แยกจากกัน ถึงชื่อ sink ภายในจะสร้างจากชื่อ instance ก็ไม่ชนกันข้าม container เสียงหลายบอตจึงไม่ไหลข้ามกัน

helper ใช้ `--network host` เพื่อให้ instance ที่ต้องเชื่อม TeamTalk server บนเครื่อง Linux เดียวกันผ่าน `localhost`/local IP ทำงานได้เหมือน helper เดิม โดยไม่มี inbound port ของบอตที่ต้อง publish เพิ่ม


## ปรับโหมดภายหลัง

หากสร้าง instance ไปแล้วแต่ต้องการเปลี่ยนโหมดภายหลัง ให้แก้ไฟล์ `config.ini` ของ instance นั้น แล้ว restart บอต:

```bash
sudo ttuhelper edit <ชื่อบอต>
sudo ttuhelper restart <ชื่อบอต>
```

ตัวอย่างการตั้งค่า:

```ini
[features]
player_enabled = True
server_management_enabled = False
```

ความหมาย:

- `True/True` = Full Bot
- `True/False` = Player Bot
- `False/True` = Server Manager

ไม่แนะนำให้ตั้ง `False/False` เพราะจะเหลือเฉพาะคำสั่งทั่วไปอย่าง `/help`, `/about`, `/weather`, `/search` บางส่วนเท่านั้น

## โครงสร้างใช้งานที่แนะนำ

หากคุณมี TeamTalk server เดียว แต่มีหลายห้อง และต้องการให้มีบอตเพลงหลายตัว แต่บอตจัดการเซิร์ฟเวอร์เพียงตัวเดียว ให้สร้างประมาณนี้:

```text
manager-main      -> Server Manager -> อยู่ห้องหลัก
music-room-1      -> Player Bot     -> อยู่ห้อง Music 1
music-room-2      -> Player Bot     -> อยู่ห้อง Music 2
music-room-3      -> Player Bot     -> อยู่ห้อง Music 3
```

รูปแบบนี้ช่วยลดความวุ่นวาย เพราะบอตเพลงจะไม่โหลดคำสั่งจัดการเซิร์ฟเวอร์ทั้งหมด และบอตจัดการเซิร์ฟเวอร์จะไม่สร้าง Music Player/queue/prefetch หรือโหลดคำสั่งเล่นเพลง (แต่ TTS ของระบบยังอาจใช้ libmpv สำหรับเล่นเสียงพูด)


## ตัวอย่าง workflow แบบครบตั้งแต่ปล่อย image ถึงเปิดหลายบอต

### ฝั่งเครื่อง build image

1. เข้าโฟลเดอร์ `01-SNTalkBot-DockerHub-Image`
2. ล็อกอิน Docker Hub
3. สั่ง publish

```bash
cd 01-SNTalkBot-DockerHub-Image
docker login
./publish.sh
```

ถ้าต้องการปล่อยเป็นเวอร์ชันเฉพาะ เช่น `2026.08.22-mode`:

```bash
TTU_IMAGE_REPO=nuttawat0295/sntalkbot TTU_TAG=2026.08.22-mode ./publish.sh
```

### ฝั่งเซิร์ฟเวอร์จริง

1. ติดตั้ง helper ครั้งแรก

```bash
cd 02-Server-Helper
sudo ./install.sh
```

2. ตรวจว่า helper เห็น image/tag อะไรอยู่

```bash
sudo ttuhelper doctor
```

3. ถ้าจะใช้ tag อื่น ให้แก้ค่าใน `/etc/default/ttuhelper`

```bash
sudo nano /etc/default/ttuhelper
```

ตัวอย่าง:

```text
TTU_IMAGE_REPO="nuttawat0295/sntalkbot"
TTU_TAG="2026.08.22-mode"
TTU_BOTS_ROOT="/opt/sntalkbot-bots"
```

4. pull image ที่ตั้งค่าไว้

```bash
sudo ttuhelper pull
```

5. สร้าง instance

```bash
sudo ttuhelper new
```

6. เริ่มบอต

```bash
sudo ttuhelper run manager-main
sudo ttuhelper run music-room-1
sudo ttuhelper run music-room-2
```

7. ตรวจสถานะและ log

```bash
sudo ttuhelper ls
sudo ttuhelper ps
sudo ttuhelper logs manager-main
```

## การดึง image เวอร์ชันใหม่ลงเซิร์ฟเวอร์

ถ้ายังใช้ repo/tag เดิม เช่น `latest`:

```bash
sudo ttuhelper update
```

helper จะ pull image ล่าสุด แล้ว recreate เฉพาะ instance ที่กำลังรันอยู่

ถ้าจะเปลี่ยนไปใช้ tag ใหม่:

```bash
sudo nano /etc/default/ttuhelper
sudo ttuhelper update
```

## การย้อนกลับไปใช้ image รุ่นก่อน (rollback)

helper ไม่มีคำสั่ง `rollback` แยก แต่ทำได้ง่ายโดยเปลี่ยน `TTU_TAG` หรือ `TTU_IMAGE_REPO` ให้ชี้ไป tag เก่า แล้วสั่ง update อีกครั้ง

ตัวอย่างย้อนจาก `latest` กลับไป `2026.08.22`:

```bash
sudo nano /etc/default/ttuhelper
# แก้ TTU_TAG="2026.08.22"
sudo ttuhelper update
```

ถ้าต้องการให้บอตตัวใดยังไม่ต้องตาม image ใหม่ ให้หยุดบอตนั้นก่อน แล้วค่อย update ตัวอื่น:

```bash
sudo ttuhelper stop music-room-2
sudo ttuhelper update
```

จากนั้นค่อยกลับมาเริ่มบอตเดิมเมื่อพร้อม:

```bash
sudo ttuhelper run music-room-2
```

## การแก้ config ของแต่ละบอต

แก้ผ่าน helper:

```bash
sudo ttuhelper edit manager-main
```

ดู path ของข้อมูล:

```bash
sudo ttuhelper path manager-main
```

ไฟล์สำคัญในแต่ละ instance คือ:

```text
config.ini
cookies.txt
instance.conf
limits.conf (ถ้ามี)
```

แก้เสร็จแล้วให้ recreate/restart:

```bash
sudo ttuhelper restart manager-main
```


## เตรียมขึ้น GitHub

repo นี้มี `.gitignore`, `LICENSE`, `NOTICE.md` และ `GITHUB_SETUP_TH.md` ให้แล้ว ดูขั้นตอน `git init`, commit, เพิ่ม remote และ push ครั้งแรกได้ใน `GITHUB_SETUP_TH.md`

หมายเหตุ: `.git/` จะถูกสร้างในเครื่องด้วย `git init`; ไม่ใช่โฟลเดอร์ที่ควรอัปโหลดเป็นไฟล์บนหน้า GitHub
