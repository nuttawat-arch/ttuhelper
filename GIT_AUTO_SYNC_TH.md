# อัปเดต GitHub ของ TTUHelper และ SNTalkBot ด้วยคำสั่งเดียวบน Windows

ไฟล์ `tools/git_sync_both.ps1` ใช้ sync repository สองตัวอัตโนมัติ:

- `D:\ttuhelper`
- `D:\sntalkbot`

สคริปต์จะทำตามลำดับให้แต่ละ repo:

1. `git add -A`
2. commit เฉพาะเมื่อมีไฟล์เปลี่ยน
3. `git pull --rebase`
4. `git push`

ถ้า repo ใดไม่มีการเปลี่ยนแปลง จะไม่สร้าง commit เปล่า แต่ยัง pull/push ให้สถานะตรงกับ GitHub

## ใช้งาน

จาก PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\git_sync_both.ps1
```

ระบุข้อความ commit เอง:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\git_sync_both.ps1 -Message "Update player and helper"
```

ถ้าเก็บโปรเจกต์คนละตำแหน่ง:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\git_sync_both.ps1 `
  -HelperPath "D:\ttuhelper" `
  -MainPath "D:\Projects\sntalkbot" `
  -Message "Update both projects"
```

ข้อกำหนด: ทั้งสองโฟลเดอร์ต้อง `git init`, มี `origin` และ push ครั้งแรกสำเร็จแล้วก่อนใช้สคริปต์นี้
