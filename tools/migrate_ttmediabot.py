#!/usr/bin/env python3
from __future__ import annotations

import argparse
import configparser
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROLE_MAP = {
    "player": (True, False, "player"),
    "manager": (False, True, "manager"),
    "full": (True, True, "full"),
}

GENDER_MAP = {
    "m": "0",
    "male": "0",
    "0": "0",
    "f": "256",
    "female": "256",
    "256": "256",
    "n": "4096",
    "neutral": "4096",
    "4096": "4096",
}


def fail(message: str, code: int = 1) -> "None":
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def bool_text(value, default=False) -> str:
    if value is None:
        value = default
    if isinstance(value, bool):
        return "True" if value else "False"
    text = str(value).strip().lower()
    return "True" if text in {"1", "true", "yes", "on", "y"} else "False"


def csv_text(values) -> str:
    if not isinstance(values, list):
        return ""
    cleaned = []
    for item in values:
        text = str(item).strip()
        if text:
            cleaned.append(text)
    return ",".join(cleaned)


def blocked_text(values) -> str:
    if not isinstance(values, list):
        return ""
    out = []
    seen = set()
    for item in values:
        name = str(item).strip().lstrip("/").lower()
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return ",".join(out)


def sanitize_name(name: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,62}", name):
        return name
    out = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._-")
    if not out or not out[0].isalnum():
        out = f"bot_{out}" if out else "bot"
    return out[:63]


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        fail(f"Cannot read {path}: {exc}")


def is_legacy_ttmediabot_config(data: object) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "root is not a JSON object"
    if str(data.get("config_version", "")).strip() != "1":
        return False, "config_version is not 1"
    for section in ("general", "player", "teamtalk", "services"):
        if not isinstance(data.get(section), dict):
            return False, f"missing legacy section: {section}"
    tt = data["teamtalk"]
    for key in ("hostname", "tcp_port", "nickname", "channel"):
        if key not in tt:
            return False, f"missing teamtalk.{key}"
    player = data["player"]
    if "default_volume" not in player:
        return False, "missing player.default_volume"
    return True, ""


def discover(source: Path):
    valid = []
    skipped = []
    for child in sorted(source.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        cfg_path = child / "config.json"
        if not cfg_path.is_file():
            continue
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            skipped.append((child.name, f"invalid JSON: {exc}"))
            continue
        ok, reason = is_legacy_ttmediabot_config(data)
        if ok:
            valid.append((child, data))
        else:
            skipped.append((child.name, reason))
    return valid, skipped


def ask_role_all() -> str:
    print("เลือกประเภทของบอตที่จะนำเข้า:")
    print("  1) Player Bot ทุกตัว (เหมาะกับ TTMediaBot เก่า และเป็นค่าเริ่มต้น)")
    print("  2) Server Manager ทุกตัว")
    print("  3) Full Bot ทุกตัว (Player + Server Manager)")
    print("  4) เลือกประเภททีละตัว")
    answer = input("เลือก [1/2/3/4] (default: 1): ").strip() or "1"
    return {"1": "player", "2": "manager", "3": "full", "4": "ask"}.get(answer, "")


def ask_role_one(name: str) -> str:
    print(f"\n{name} ทำงานประเภทไหน?")
    print("  1) Player Bot")
    print("  2) Server Manager")
    print("  3) Full Bot")
    answer = input("เลือก [1/2/3] (default: 1): ").strip() or "1"
    role = {"1": "player", "2": "manager", "3": "full"}.get(answer)
    if not role:
        fail(f"Invalid mode selection for {name}")
    return role


def setv(cfg: configparser.ConfigParser, section: str, key: str, value) -> None:
    if not cfg.has_section(section):
        cfg.add_section(section)
    cfg.set(section, key, str(value))


def convert_one(template: Path, old: dict, role: str) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser(interpolation=None)
    with template.open("r", encoding="utf-8") as fh:
        cfg.read_file(fh)

    general = old.get("general", {})
    player = old.get("player", {})
    tt = old.get("teamtalk", {})
    users = tt.get("users", {}) if isinstance(tt.get("users"), dict) else {}

    player_enabled, manager_enabled, _ = ROLE_MAP[role]
    setv(cfg, "features", "player_enabled", bool_text(player_enabled))
    setv(cfg, "features", "server_management_enabled", bool_text(manager_enabled))

    setv(cfg, "server", "address", tt.get("hostname", "localhost"))
    setv(cfg, "server", "tcp_port", tt.get("tcp_port", 10333))
    setv(cfg, "server", "udp_port", tt.get("udp_port", tt.get("tcp_port", 10333)))
    setv(cfg, "server", "encrypted", bool_text(tt.get("encrypted", False)))
    setv(cfg, "server", "username", tt.get("username", ""))
    setv(cfg, "server", "password", tt.get("password", ""))

    language = str(general.get("language", "th") or "th").strip() or "th"
    setv(cfg, "bot", "language", language)
    setv(cfg, "bot", "nickname", tt.get("nickname", "SN TalkBot"))
    setv(cfg, "bot", "default_channel", tt.get("channel", "/") or "/")
    setv(cfg, "bot", "channel_password", tt.get("channel_password", ""))
    old_status = str(tt.get("status", "") or "").strip()
    setv(cfg, "bot", "status_message", old_status if old_status else "auto")
    setv(cfg, "bot", "gender", GENDER_MAP.get(str(tt.get("gender", "n")).strip().lower(), "4096"))
    setv(cfg, "bot", "reconnection_attempts", tt.get("reconnection_attempts", -1))
    setv(cfg, "bot", "reconnection_timeout", tt.get("reconnection_timeout", 10))
    setv(cfg, "bot", "blocked_commands", blocked_text(general.get("blocked_commands", [])))

    # A migrated Player should not accidentally gain manager-side public monitoring.
    if not manager_enabled:
        setv(cfg, "bot", "intercept_channel_messages", "False")
        setv(cfg, "bot", "welcome_broadcast", "False")
        setv(cfg, "bot", "welcome_mode", "0")
        setv(cfg, "bot", "profanity_filter_enabled", "False")

    setv(cfg, "accounts", "authorized_users", csv_text(users.get("admins", [])))
    setv(cfg, "accounts", "detect_server_admins", "True")

    setv(cfg, "playback", "input_device", "auto")
    setv(cfg, "playback", "output_device", "auto")
    setv(cfg, "playback", "cookiefile_path", "/app/data/cookies.txt")
    setv(cfg, "playback", "default_volume", player.get("default_volume", 50))
    setv(cfg, "playback", "max_volume", player.get("max_volume", 100))
    setv(cfg, "playback", "seek_step", player.get("seek_step", 5))
    setv(cfg, "playback", "send_channel_messages", bool_text(general.get("send_channel_messages", False)))
    setv(cfg, "playback", "fade_enabled", bool_text(player.get("volume_fading", True), True))

    setv(cfg, "teamtalk_license", "license_name", tt.get("license_name", ""))
    setv(cfg, "teamtalk_license", "license_key", tt.get("license_key", ""))

    return cfg


def parse_limits(source_dir: Path, dest_dir: Path) -> None:
    legacy = source_dir / "limit.txt"
    if not legacy.is_file():
        return
    text = legacy.read_text(encoding="utf-8", errors="replace")
    cpu_match = re.search(r"(?:^|\s)--cpus(?:=|\s+)([^\s]+)", text)
    mem_match = re.search(r"(?:^|\s)--memory(?:=|\s+)([^\s]+)", text)
    lines = []
    if cpu_match:
        lines.append(f"cpu={cpu_match.group(1)}")
    if mem_match:
        lines.append(f"memory={mem_match.group(1)}")
    if lines:
        (dest_dir / "limits.conf").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Migrate legacy TTMediaBot Docker Helper instances to TTUHelper/SNTalkBot")
    ap.add_argument("--source", required=True)
    ap.add_argument("--dest-root", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--mode", choices=["prompt", "player", "manager", "full", "ask"], default="prompt")
    ap.add_argument("--yes", action="store_true", help="Skip final confirmation")
    ap.add_argument("--replace", action="store_true", help="Replace existing SNTalkBot instance directories after backing them up")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--names-file")
    args = ap.parse_args()

    source = Path(args.source).expanduser().resolve()
    dest_root = Path(args.dest_root).expanduser().resolve()
    template = Path(args.template).expanduser().resolve()
    if not source.is_dir():
        fail(f"Legacy root not found: {source}")
    if not template.is_file():
        fail(f"SNTalkBot config template not found: {template}")

    valid, skipped = discover(source)
    if not valid:
        fail("No supported TTMediaBot config v1 instances were found. This importer does not support arbitrary old bot projects.")

    print(f"ตรวจพบ TTMediaBot config v1 ที่รองรับ: {len(valid)} ตัว")
    for child, _ in valid:
        print(f"  - {child.name}")
    if skipped:
        print(f"ข้าม config.json ที่ไม่ตรงรูปแบบ TTMediaBot ที่รองรับ: {len(skipped)}")
        for name, reason in skipped:
            print(f"  - {name}: {reason}")

    mode = args.mode
    if mode == "prompt":
        mode = ask_role_all()
        if not mode:
            fail("Invalid mode selection")

    plan = []
    used_names = set()
    for source_dir, data in valid:
        name = sanitize_name(source_dir.name)
        if name != source_dir.name:
            print(f"WARNING: ชื่อโฟลเดอร์ '{source_dir.name}' ไม่เหมาะกับ Docker รุ่นใหม่ จะใช้ชื่อ '{name}'")
        base = name
        suffix = 2
        while name.lower() in used_names:
            name = f"{base[:58]}-{suffix}"
            suffix += 1
        used_names.add(name.lower())
        role = ask_role_one(source_dir.name) if mode == "ask" else mode
        plan.append((source_dir, data, name, role))

    conflicts = [name for _, _, name, _ in plan if (dest_root / name).exists()]
    replace = args.replace
    if conflicts and not replace:
        print("พบ SNTalkBot instance ชื่อเดียวกันในปลายทาง:")
        for name in conflicts:
            print(f"  - {name}")
        if args.yes or args.dry_run:
            fail("Destination conflicts exist. Re-run with --replace if you intend to replace them.", 3)
        answer = input("สำรองของเดิมแล้วแทนที่ instance เหล่านี้หรือไม่? [y/N]: ").strip().lower()
        if answer in {"y", "yes"}:
            replace = True
        else:
            fail("Migration cancelled because destination conflicts were not approved.", 3)

    print("\nสิ่งที่จะย้าย:")
    print("  server/port/encryption, nickname, login, channel, language, status/gender")
    print("  admin usernames, blocked commands, volume/max volume/seek, license และ cookies.txt")
    print("  sound-device ID เก่าจะเปลี่ยนเป็น auto สำหรับ Docker audio bridge ใหม่")
    print("  TTMediaBot.log และ TTMediaBotCache.dat จะไม่ย้าย; โฟลเดอร์เก่ายังถูกเก็บไว้เป็น backup")
    print(f"ปลายทาง: {dest_root}")
    for _, _, name, role in plan:
        print(f"  - {name}: {ROLE_MAP[role][2]}")

    if args.dry_run:
        print("DRY RUN: ไม่มีไฟล์ใดถูกเปลี่ยนแปลง")
        return
    if not args.yes:
        answer = input("ดำเนินการย้ายตอนนี้หรือไม่? [Y/n]: ").strip().lower()
        if answer in {"n", "no"}:
            fail("Migration cancelled by user.", 4)

    dest_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_root = dest_root / ".migration-backups" / stamp
    staging_root = dest_root / ".migration-staging" / stamp
    report_dir = dest_root / ".migration-reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_dir.chmod(0o700)
    staging_root.mkdir(parents=True, exist_ok=False)
    staging_root.chmod(0o700)
    results = []

    # Stage every converted instance first. Existing destinations are untouched until
    # all supported legacy configs have converted successfully.
    staged_items = []
    try:
        for source_dir, data, name, role in plan:
            staged = staging_root / name
            staged.mkdir(parents=True, exist_ok=False)
            cfg = convert_one(template, data, role)
            with (staged / "config.ini").open("w", encoding="utf-8") as fh:
                cfg.write(fh)

            cookies = source_dir / "cookies.txt"
            if cookies.is_file():
                shutil.copy2(cookies, staged / "cookies.txt")
            else:
                (staged / "cookies.txt").write_text(
                    "# Netscape HTTP Cookie File\n# No legacy cookies.txt was found during migration.\n",
                    encoding="utf-8",
                )

            shutil.copy2(source_dir / "config.json", staged / "legacy-config.json")
            parse_limits(source_dir, staged)
            player_enabled, manager_enabled, mode_name = ROLE_MAP[role]
            (staged / "instance.conf").write_text(
                "\n".join([
                    "image=managed-by-ttuhelper-current-tag",
                    f"created={datetime.now(timezone.utc).isoformat()}",
                    f"migrated_from={source_dir}",
                    f"mode={mode_name}",
                    f"player_enabled={'True' if player_enabled else 'False'}",
                    f"server_management_enabled={'True' if manager_enabled else 'False'}",
                    "",
                ]),
                encoding="utf-8",
            )
            (staged / "MIGRATED_FROM_TTMEDIABOT.txt").write_text(
                "This instance was migrated from legacy TTMediaBot Docker Helper.\n"
                f"Source: {source_dir}\n"
                "The original source directory was intentionally left unchanged as a backup.\n"
                "TTMediaBot.log and TTMediaBotCache.dat were not imported into the new runtime.\n",
                encoding="utf-8",
            )
            (staged / "config.ini").chmod(0o640)
            (staged / "cookies.txt").chmod(0o640)
            (staged / "legacy-config.json").chmod(0o600)
            (staged / "instance.conf").chmod(0o640)
            (staged / "MIGRATED_FROM_TTMEDIABOT.txt").chmod(0o640)
            limits_file = staged / "limits.conf"
            if limits_file.exists():
                limits_file.chmod(0o640)
            staged_items.append((source_dir, name, role, staged, cookies.is_file()))

        # Commit staged directories only after every conversion succeeded.
        for source_dir, name, role, staged, cookies_copied in staged_items:
            dest = dest_root / name
            if dest.exists():
                if not replace:
                    fail(f"Destination unexpectedly exists: {dest}")
                backup_root.mkdir(parents=True, exist_ok=True)
                backup_root.chmod(0o700)
                backup_dest = backup_root / name
                if backup_dest.exists():
                    shutil.rmtree(backup_dest)
                shutil.move(str(dest), str(backup_dest))
                print(f"สำรอง SNTalkBot instance เดิม: {backup_dest}")
            shutil.move(str(staged), str(dest))
            _, _, mode_name = ROLE_MAP[role]
            results.append({
                "name": name,
                "mode": mode_name,
                "source": str(source_dir),
                "destination": str(dest),
                "cookies_copied": cookies_copied,
            })
            print(f"ย้ายแล้ว: {source_dir.name} -> {dest} ({mode_name})")
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root, ignore_errors=True)

    report = {
        "migration": "TTMediaBot Docker Helper config v1 -> TTUHelper/SNTalkBot",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source),
        "destination_root": str(dest_root),
        "results": results,
        "skipped": [{"name": n, "reason": r} for n, r in skipped],
    }
    report_path = report_dir / f"ttmediabot-{stamp}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.chmod(0o600)

    if args.names_file:
        Path(args.names_file).write_text("\n".join(item["name"] for item in results) + "\n", encoding="utf-8")

    print(f"Migration report: {report_path}")
    print("โฟลเดอร์ TTMediaBot ต้นทางยังอยู่ที่เดิมและไม่ได้ถูกลบ")


if __name__ == "__main__":
    main()
