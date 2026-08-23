# การย้ายจากระบบเก่า

ถ้าต้องการย้าย **TTMediaBot Docker Helper ที่มี `config.json` v1** แบบอัตโนมัติ ให้ใช้ `ttuhelper migrate-ttmediabot` และอ่าน `MIGRATE_TTMEDIABOT_TH.md`

หมายเหตุ: ตัวนำเข้านี้รองรับเฉพาะ TTMediaBot Docker Helper รูปแบบที่ระบุ ไม่ใช่โปรเจกต์บอตเก่าทุกแบบ

## Config

เดิม helper สร้าง `config.json` สำหรับ TTMediaBot โดยตรง รุ่นนี้สร้าง `config.ini` ตาม SN TalkBot และใช้ template จาก Docker image ที่กำลังใช้อยู่จริงทุกครั้งที่ `ttuhelper new`

## Runtime

เดิม helper override command ภายใน container เพื่อเรียก `TTMediaBot.sh -c data/config.json ...` รุ่นใหม่ไม่ override runtime ของ image แต่ปล่อยให้ `docker-entrypoint.sh` ของ SN TalkBot เตรียม PulseAudio bridge แล้วเรียก `main.py -f /app/data/config.ini` เอง

## หลายบอต

ยังคงแนวทางหนึ่งโฟลเดอร์ต่อหนึ่ง container โดยรุ่นใหม่ใช้ `/opt/sntalkbot-bots/<name>` เป็นค่าเริ่มต้น ทำให้เรียก `ttuhelper` จาก directory ไหนก็ได้ ไม่ต้องเก็บโฟลเดอร์ลูกค้าไว้ข้างสคริปต์ และยังตรวจโฟลเดอร์ legacy `/opt/ttutilities-bots` เพื่อใช้ข้อมูลเดิมต่อได้

## Update

เดิม `update` เข้าไป `pip install --upgrade -r requirements.txt` ภายในแต่ละ container แล้ว restart รุ่นใหม่ใช้แนว immutable image: pull image จาก Docker Hub แล้ว recreate container ที่กำลังรันด้วย image ใหม่ โดย mount data folder เดิมกลับเข้าไป

## Cookies

`cks` ยังอัปเดตทีละ instance ส่วน `cks-all` ตอนนี้อัปเดตทุก instance folder ไม่จำกัดเฉพาะ container ที่กำลังมีอยู่

## Resource limits

ยังมี `limit <name>` แต่เก็บ CPU/RAM เป็นค่าที่ตรวจรูปแบบแล้วใน `limits.conf` และประกอบเป็น Docker arguments แบบ array เพื่อลดปัญหาการแทรก raw command-line option

## การย้ายชื่อโปรเจกต์หลักเป็น SNTalkBot

รุ่นใหม่ใช้ data root เริ่มต้น `/opt/sntalkbot-bots` แต่เพื่อไม่ทำข้อมูลเดิมหาย `ttuhelper` จะตรวจ `/opt/ttutilities-bots` อัตโนมัติ หากพบโฟลเดอร์เดิมและยังไม่มีโฟลเดอร์ใหม่ จะใช้โฟลเดอร์เดิมต่อทันที

หากต้องการกำหนดเอง ให้ตั้ง `TTU_BOTS_ROOT` ใน `/etc/default/ttuhelper`
