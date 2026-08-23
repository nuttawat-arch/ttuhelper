# ย้ายจาก TTMediaBot Docker Helper เก่ามา SNTalkBot

> ฟังก์ชันนี้รองรับ **เฉพาะ TTMediaBot Docker Helper รุ่นเก่า** ที่เก็บแต่ละบอตเป็นโฟลเดอร์ย่อยและมี `config.json` แบบ `config_version: 1` เท่านั้น ไม่ใช่ตัวนำเข้าทั่วไปสำหรับโปรเจกต์บอตเก่าทุกชนิด

โครงสร้างที่รองรับมีลักษณะนี้:

```text
/opt/ttmediabot-docker-helper/
  BackgroundPlayer/config.json
  BackgroundPlayer/cookies.txt
  nd/config.json
  nd/cookies.txt
  PinkRose/config.json
  ...
```

## สิ่งที่ต้องทำ

อัปเดต TTUHelper ให้เป็นรุ่น 1.3.0 หรือใหม่กว่า แล้วรัน:

```bash
sudo ttuhelper migrate-ttmediabot
```

ถ้าโฟลเดอร์เก่าอยู่ที่ค่าเริ่มต้น ให้กด Enter ตอนถูกถาม path:

```text
Legacy TTMediaBot root (default: /opt/ttmediabot-docker-helper):
```

ถ้าเก็บไว้ที่อื่น ให้พิมพ์ path เช่น:

```text
/opt/ttmediabot-docker-helper
```

หรือระบุ path ในคำสั่งได้เลย:

```bash
sudo ttuhelper migrate-ttmediabot /opt/ttmediabot-docker-helper
```

## เลือกประเภทบอต

Helper จะถาม:

```text
1) Player Bot ทุกตัว
2) Server Manager ทุกตัว
3) Full Bot ทุกตัว
4) เลือกประเภททีละตัว
```

TTMediaBot เก่าเป็น Player เป็นหลัก ดังนั้นถ้าบอตเก่าทุกตัวใช้เล่นเพลง ให้เลือก `1`

ถ้ามีหลายหน้าที่ปะปนกัน ให้เลือก `4` แล้ว Helper จะถามทีละโฟลเดอร์ เช่น:

```text
BackgroundPlayer ทำงานประเภทไหน?
1) Player Bot
2) Server Manager
3) Full Bot
```

## สิ่งที่ย้ายให้

ระบบจะสร้าง instance ใหม่ที่:

```text
/opt/sntalkbot-bots/<ชื่อเดิม>/
```

และย้ายค่าที่ใช้ร่วมกันได้ เช่น:

- Hostname, TCP port, UDP port และ encrypted
- Nickname, username, password
- Channel และ channel password
- Language
- Status และ gender
- รายชื่อ admin
- Blocked commands
- Default volume, max volume และ seek step
- TeamTalk SDK license ถ้ามี
- `cookies.txt`

ระบบจะสร้าง `config.ini` รูปแบบล่าสุดจาก Docker image ที่ใช้อยู่จริง ไม่เอา `config.json` เก่าไปใช้ตรง ๆ

Sound-device ID เก่า เช่น `output_device=1` และ `input_device=5` จะไม่ถูกยกมา เพราะระบบ Docker ใหม่ใช้ audio bridge อัตโนมัติ ค่าใหม่จะเป็น `auto`

## ไฟล์ที่ไม่ย้ายเข้า runtime ใหม่

`TTMediaBot.log` และ `TTMediaBotCache.dat` จะไม่ถูกนำเข้า SNTalkBot เพราะรูปแบบ runtime/cache ต่างกัน

แต่โฟลเดอร์ TTMediaBot เก่าจะ **ไม่ถูกลบ** จึงยังเก็บ log/cache เดิมไว้ตรวจย้อนหลังได้

ใน instance ใหม่ยังมี:

```text
legacy-config.json
MIGRATED_FROM_TTMEDIABOT.txt
```

เพื่อให้ตรวจย้อนกลับได้ว่าค่ามาจากที่ไหน

## หลังแปลงเสร็จ

Helper จะถามว่าจะเริ่ม/รีสตาร์ตบอตทั้งหมดด้วย SNTalkBot image ล่าสุดหรือไม่:

```text
Start/restart all imported bots now ...? [Y/n]:
```

กด Enter เพื่อทำต่อ บอตเก่าที่ใช้ชื่อ container เดียวกันจะถูกแทนด้วย container SNTalkBot ใหม่ แต่ข้อมูลต้นทางยังอยู่

ตรวจผลด้วย:

```bash
sudo ttuhelper ls
sudo ttuhelper ps
sudo ttuhelper logs <ชื่อบอต>
```

ควรเก็บ `/opt/ttmediabot-docker-helper` ไว้จนกว่าจะตรวจว่าบอตใหม่ทุกตัว login, join channel และเล่นเพลงได้ครบ

## ทดลองดูก่อนโดยไม่เปลี่ยนไฟล์

```bash
sudo ttuhelper migrate-ttmediabot /opt/ttmediabot-docker-helper --dry-run
```

คำสั่งนี้ตรวจหาโฟลเดอร์ที่รองรับและแสดงแผนการย้าย แต่ไม่สร้าง instance และไม่เปลี่ยน container

## ถ้าปลายทางมี instance ชื่อเดียวกันอยู่แล้ว

Helper จะไม่ทับเงียบ ๆ แต่จะถามก่อน ถ้ายืนยัน ระบบจะสำรอง instance SNTalkBot เดิมไว้ใต้:

```text
/opt/sntalkbot-bots/.migration-backups/
```

แล้วจึงแทนที่ด้วยข้อมูลที่นำเข้า
