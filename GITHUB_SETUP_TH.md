# วิธีสร้าง Git repository และอัปขึ้น GitHub

## สำคัญ: `.git` กับ `.gitignore` ไม่ใช่อย่างเดียวกัน

- `.git/` คือโฟลเดอร์ metadata ภายในเครื่อง เกิดจากคำสั่ง `git init` และ Git ใช้เก็บประวัติ/branch/remote
- `.gitignore` คือไฟล์ที่ **ควรอยู่บน GitHub** เพื่อบอก Git ว่าไฟล์ใดไม่ควรถูก commit
- ปกติเรา **ไม่อัปโหลดโฟลเดอร์ `.git/` เข้า GitHub เป็นไฟล์** แต่ใช้ Git อ่านข้อมูลจาก `.git/` แล้ว `push` commit ขึ้นไป

## วิธีเริ่ม repo ใหม่

แตกโฟลเดอร์ `ttuhelper` แล้วเข้าไปในโฟลเดอร์:

```bash
cd ttuhelper
```

เริ่ม Git:

```bash
git init
```

ถ้าต้องการ branch หลักชื่อ `main`:

```bash
git branch -M main
```

ตรวจไฟล์:

```bash
git status
```

เพิ่มไฟล์ทั้งหมดที่ไม่ถูก `.gitignore` ตัดออก:

```bash
git add .
```

commit ครั้งแรก:

```bash
git commit -m "Initial release of ttuhelper"
```

จากนั้นสร้าง repository ว่างบน GitHub เช่นชื่อ:

```text
ttuhelper
```

อย่าเลือกให้ GitHub สร้าง README/License เพิ่มถ้า repo ฝั่งเครื่องมีไฟล์เหล่านี้อยู่แล้ว จะได้ไม่ต้องแก้ conflict ตอน push ครั้งแรก

ผูก remote โดยเปลี่ยน URL ให้เป็น repo ของคุณ:

```bash
git remote add origin https://github.com/USERNAME/ttuhelper.git
```

ตรวจ remote:

```bash
git remote -v
```

push ครั้งแรก:

```bash
git push -u origin main
```

## อัปเดตครั้งต่อไป

หลังแก้ source:

```bash
git status
git add .
git commit -m "Update ttuhelper"
git push
```

## ถ้า GitHub ขอ Personal Access Token

เมื่อใช้ HTTPS ปัจจุบัน GitHub อาจให้ใช้ Personal Access Token แทนรหัสผ่านบัญชี ให้สร้าง token ใน GitHub แล้วใส่ token ในช่อง password เมื่อ Git ขอ credential

## วิธี clone ลง Linux Server

หลัง repo อยู่บน GitHub:

```bash
git clone https://github.com/USERNAME/ttuhelper.git
cd ttuhelper
sudo ./install.sh
```

หลังติดตั้ง คำสั่ง global คือ:

```bash
sudo ttuhelper doctor
sudo ttuhelper new
```

## อัปเดต helper source บน Server

การ `ttuhelper update` หมายถึงอัปเดต **Docker bot image** ไม่ใช่อัปเดต shell helper จาก GitHub

ถ้าต้องการอัปเดตตัว helper เอง:

```bash
cd /path/to/ttuhelper
git pull
sudo ./install.sh
```

`install.sh` จะติดตั้ง `ttuhelper.sh` รุ่นใหม่ทับ `/usr/local/bin/ttuhelper` แต่จะไม่แตะ `/usr/local/bin/tthelper` ของระบบเก่า


## อัปเดตสอง repository ด้วยคำสั่งเดียว

หลังจากสร้างและ push ทั้ง `ttuhelper` และ `sntalkbot` ครั้งแรกสำเร็จแล้ว สามารถใช้:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\git_sync_both.ps1
```

ค่าเริ่มต้นสคริปต์มองหา:

```text
D:\ttuhelper
D:\sntalkbot
```

มันจะ add/commit เฉพาะเมื่อมีการเปลี่ยนแปลง จากนั้น `git pull --rebase` และ `git push` ให้ทั้งสอง repo อัตโนมัติ รายละเอียดอยู่ใน `GIT_AUTO_SYNC_TH.md`
