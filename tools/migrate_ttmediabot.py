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

# Migration is a schema translation, never a blind config copy.  Only these
# legacy paths have a supported semantic equivalent in current SNTalkBot.
MAPPED_LEGACY_PATHS = {
    "general.language", "general.blocked_commands", "general.send_channel_messages",
    "player.default_volume", "player.max_volume", "player.seek_step", "player.volume_fading",
    "teamtalk.hostname", "teamtalk.tcp_port", "teamtalk.udp_port", "teamtalk.encrypted",
    "teamtalk.username", "teamtalk.password", "teamtalk.nickname", "teamtalk.channel",
    "teamtalk.channel_password", "teamtalk.status", "teamtalk.gender",
    "teamtalk.reconnection_attempts", "teamtalk.reconnection_timeout",
    "teamtalk.users.admins", "teamtalk.license_name", "teamtalk.license_key",
}
SUPPORTED_LANGUAGES = {"en", "th", "ar", "pt"}


def scalar_text(value, default=None, *, max_len=4096):
    """Return a safe scalar string or default; containers are never stringified."""
    if value is None or isinstance(value, (dict, list, tuple, set)):
        return default
    text = str(value).strip()
    if not text:
        return default
    return text[:max_len]


def bounded_int(value, default=None, *, minimum=None, maximum=None):
    try:
        if isinstance(value, bool):
            raise ValueError
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    if minimum is not None and number < minimum:
        return default
    if maximum is not None and number > maximum:
        return default
    return number


def strict_bool(value, default=None):
    if isinstance(value, bool):
        return value
    text = scalar_text(value)
    if text is None:
        return default
    text = text.casefold()
    if text in {"1", "true", "yes", "on", "y"}:
        return True
    if text in {"0", "false", "no", "off", "n"}:
        return False
    return default


def set_if(cfg, section, key, value):
    """Overlay only a validated value onto a field that exists in the template.

    Migration must never invent a current SNTalkBot key merely because the old
    TTMediaBot had a similarly named setting.  The release template is the
    authoritative schema; absent targets are treated as unsupported and dropped.
    """
    if value is None or not cfg.has_option(section, key):
        return False
    cfg.set(section, key, str(value))
    return True


def _leaf_paths(value, prefix=""):
    paths = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(child, dict):
                paths.extend(_leaf_paths(child, key_path))
            else:
                paths.append(key_path)
    return paths


def migration_field_summary(old):
    leaves = set(_leaf_paths(old))
    ignored = sorted(path for path in leaves if path != "config_version" and path not in MAPPED_LEGACY_PATHS)
    mapped = sorted(path for path in leaves if path in MAPPED_LEGACY_PATHS)
    return mapped, ignored




# Current-config repair rules used only for instances that were previously
# migrated from TTMediaBot.  The current SNTalkBot template remains the schema
# authority; these rules only make safe coercions before falling back to the
# template default.
CURRENT_CHOICE_RULES = {
    ("bot", "language"): {"en", "th", "ar", "pt"},
    ("bot", "gender"): {"0", "256", "4096"},
    ("bot", "char_limit_mode"): {"1", "2"},
    ("bot", "blacklist_mode"): {"1", "2"},
    ("playback", "channel_messages_mode"): {"private", "silent"},
    ("playback", "play_mode"): {"1", "2", "3"},
}

CURRENT_RANGE_RULES = {
    ("server", "tcp_port"): (1, 65535),
    ("server", "udp_port"): (1, 65535),
    ("bot", "random_message_interval"): (0, 1000000),
    ("bot", "char_limit"): (0, 1000000),
    ("bot", "video_deletion_timer"): (0, 1000000),
    ("bot", "jail_timer_seconds"): (0, 1000000),
    ("bot", "jail_flood_count"): (0, 1000000),
    ("bot", "reconnection_attempts"): (-1, 1000000),
    ("bot", "reconnection_timeout"): (1, 3600),
    ("playback", "seek_step"): (1, 3600),
    ("playback", "default_volume"): (0, 100),
    ("playback", "max_volume"): (1, 150),
    ("account_requests", "smtp_port"): (1, 65535),
    ("account_requests", "otp_expiry_seconds"): (1, 86400),
    ("account_requests", "max_attempts"): (1, 1000),
    ("account_requests", "smtp_timeout"): (1, 3600),
    ("ssh", "port"): (1, 65535),
    ("logging", "max_bytes"): (0, 2**63 - 1),
    ("logging", "backup_count"): (0, 1000000),
}

CURRENT_FLOAT_RANGE_RULES = {
    ("playback", "volume_fading"): (0.0, 30.0),
    ("playback", "audio_buffer"): (0.01, 120.0),
    ("playback", "speed"): (0.1, 8.0),
    ("playback", "announcement_google_speed"): (0.1, 8.0),
    ("playback", "announcement_volume"): (0.0, 10.0),
    ("tts", "google_speed"): (0.1, 8.0),
}


def _read_ini(path: Path) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser(interpolation=None)
    with path.open("r", encoding="utf-8") as fh:
        cfg.read_file(fh)
    return cfg


def _ini_string(cfg: configparser.ConfigParser) -> str:
    import io
    buf = io.StringIO()
    cfg.write(buf)
    return buf.getvalue()


def _role_from_instance(instance_dir: Path) -> str:
    conf = instance_dir / "instance.conf"
    if conf.is_file():
        for raw in conf.read_text(encoding="utf-8", errors="replace").splitlines():
            if raw.startswith("mode="):
                value = raw.split("=", 1)[1].strip().lower()
                if value in ROLE_MAP:
                    return value
    return "player"


def _legacy_source_from_instance(instance_dir: Path) -> Path | None:
    conf = instance_dir / "instance.conf"
    if conf.is_file():
        for raw in conf.read_text(encoding="utf-8", errors="replace").splitlines():
            if raw.startswith("migrated_from="):
                value = raw.split("=", 1)[1].strip()
                if value:
                    return Path(value)
    marker = instance_dir / "MIGRATED_FROM_TTMEDIABOT.txt"
    if marker.is_file():
        for raw in marker.read_text(encoding="utf-8", errors="replace").splitlines():
            if raw.startswith("Source:"):
                value = raw.split(":", 1)[1].strip()
                if value:
                    return Path(value)
    return None


def _is_migrated_instance(instance_dir: Path) -> bool:
    if (instance_dir / "MIGRATED_FROM_TTMEDIABOT.txt").is_file():
        return True
    conf = instance_dir / "instance.conf"
    return conf.is_file() and "migrated_from=" in conf.read_text(encoding="utf-8", errors="replace")


def _coerce_existing_value(section: str, key: str, value, default: str):
    """Return (normalized_value, action) without ever exposing a secret value."""
    text = "" if value is None else str(value).strip()
    default_text = "" if default is None else str(default).strip()
    skey = (section.lower(), key.lower())

    # These two fields are the list-like values imported from TTMediaBot v1.
    # Older migrator/config edits may have left container-like text or malformed
    # entries.  Repair them conservatively instead of keeping a poisoned string.
    if skey == ("bot", "blocked_commands"):
        if text.lstrip().startswith(("[", "{", "(")):
            return default_text, "defaulted"
        normalized = blocked_text([part.strip() for part in text.split(",") if part.strip()])
        if text and not normalized:
            return default_text, "defaulted"
        return normalized, "kept" if normalized == text else "coerced"

    if skey == ("accounts", "authorized_users"):
        if text.lstrip().startswith(("[", "{", "(")):
            return default_text, "defaulted"
        cleaned = []
        seen = set()
        for part in text.split(","):
            item = part.strip()
            if not item or len(item) > 255 or any(ord(ch) < 32 for ch in item):
                continue
            if item not in seen:
                seen.add(item); cleaned.append(item)
        normalized = ",".join(cleaned)
        if text and not normalized:
            return default_text, "defaulted"
        return normalized, "kept" if normalized == text else "coerced"

    if skey in CURRENT_CHOICE_RULES:
        candidate = text.casefold() if skey == ("bot", "language") else text
        if candidate in CURRENT_CHOICE_RULES[skey]:
            return candidate, "kept" if candidate == text else "coerced"
        return default_text, "defaulted"

    if default_text.casefold() in {"true", "false"}:
        parsed = strict_bool(text, None)
        if parsed is None:
            return default_text, "defaulted"
        normalized = "True" if parsed else "False"
        return normalized, "kept" if normalized.casefold() == text.casefold() else "coerced"

    if re.fullmatch(r"-?\d+", default_text or ""):
        try:
            # Accept integral float-like legacy/current values such as "50.0".
            number_f = float(text)
            if not number_f.is_integer():
                raise ValueError
            number = int(number_f)
        except (TypeError, ValueError, OverflowError):
            return default_text, "defaulted"
        bounds = CURRENT_RANGE_RULES.get(skey)
        if bounds and not (bounds[0] <= number <= bounds[1]):
            return default_text, "defaulted"
        normalized = str(number)
        return normalized, "kept" if normalized == text else "coerced"

    if re.fullmatch(r"-?(?:\d+\.\d+|\d+\.)", default_text or ""):
        try:
            number = float(text)
            if not (number == number and abs(number) != float("inf")):
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            return default_text, "defaulted"
        bounds = CURRENT_FLOAT_RANGE_RULES.get(skey)
        if bounds and not (bounds[0] <= number <= bounds[1]):
            return default_text, "defaulted"
        normalized = format(number, "g")
        return normalized, "kept" if normalized == text else "coerced"

    # Text/password/device/list-style fields are already strings in INI.  Keep
    # them verbatim after trimming only the surrounding whitespace introduced by
    # hand edits.  Empty is valid for optional fields and secrets.
    return text, "kept"


def _enforce_role(cfg: configparser.ConfigParser, role: str):
    player_enabled, manager_enabled, _ = ROLE_MAP.get(role, ROLE_MAP["player"])
    set_if(cfg, "features", "player_enabled", bool_text(player_enabled))
    set_if(cfg, "features", "server_management_enabled", bool_text(manager_enabled))
    if not manager_enabled:
        set_if(cfg, "bot", "intercept_channel_messages", "False")
        set_if(cfg, "bot", "welcome_broadcast", "False")
        set_if(cfg, "bot", "welcome_mode", "0")
        set_if(cfg, "bot", "profanity_filter_enabled", "False")


def repair_one_migrated(template: Path, instance_dir: Path):
    """Repair one already-migrated config against the current template.

    Valid current values are preserved. Missing keys receive current defaults,
    unsupported keys disappear, and malformed typed values are safely coerced or
    defaulted. If the INI itself cannot be parsed, rebuild from the preserved
    legacy config.json when available rather than guessing credentials.
    """
    template_cfg = _read_ini(template)
    config_path = instance_dir / "config.ini"
    role = _role_from_instance(instance_dir)
    repaired = []
    defaulted = []
    dropped = []
    rebuilt_from_legacy = False

    current = None
    parse_error = None
    if config_path.is_file():
        try:
            current = _read_ini(config_path)
        except Exception as exc:
            parse_error = type(exc).__name__

    if current is None:
        source_dir = _legacy_source_from_instance(instance_dir)
        legacy_path = source_dir / "config.json" if source_dir else None
        if legacy_path and legacy_path.is_file():
            try:
                old = load_json(legacy_path)
                ok, _reason = is_legacy_ttmediabot_config(old)
                if ok:
                    new_cfg = convert_one(template, old, role)
                    rebuilt_from_legacy = True
                    repaired.append("config.ini:rebuilt-from-preserved-legacy")
                else:
                    return {"name": instance_dir.name, "changed": False, "failed": True, "reason": "legacy-source-no-longer-supported", "parse_error": parse_error}
            except Exception as exc:
                return {"name": instance_dir.name, "changed": False, "failed": True, "reason": f"legacy-rebuild-{type(exc).__name__}", "parse_error": parse_error}
        else:
            return {"name": instance_dir.name, "changed": False, "failed": True, "reason": "config-unparseable-and-legacy-source-missing", "parse_error": parse_error}
    else:
        new_cfg = configparser.ConfigParser(interpolation=None)
        for section in template_cfg.sections():
            new_cfg.add_section(section)
            for key, default in template_cfg.items(section):
                if current.has_option(section, key):
                    value, action = _coerce_existing_value(section, key, current.get(section, key, raw=True), default)
                    new_cfg.set(section, key, value)
                    if action == "coerced":
                        repaired.append(f"{section}.{key}")
                    elif action == "defaulted":
                        defaulted.append(f"{section}.{key}")
                else:
                    new_cfg.set(section, key, default)
                    defaulted.append(f"{section}.{key}")
        for section in current.sections():
            if not template_cfg.has_section(section):
                dropped.append(f"{section}.*")
                continue
            for key in current[section]:
                if not template_cfg.has_option(section, key):
                    dropped.append(f"{section}.{key}")
        _enforce_role(new_cfg, role)

    old_text = config_path.read_text(encoding="utf-8", errors="replace") if config_path.is_file() else ""
    new_text = _ini_string(new_cfg)
    changed = old_text != new_text
    return {
        "name": instance_dir.name, "changed": changed, "failed": False,
        "role": role, "repaired_fields": sorted(set(repaired)),
        "defaulted_fields": sorted(set(defaulted)), "dropped_fields": sorted(set(dropped)),
        "rebuilt_from_legacy": rebuilt_from_legacy, "parse_error": parse_error,
        "_new_text": new_text,
    }


def repair_existing_migrated(template: Path, dest_root: Path, only_name: str | None = None):
    dest_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report_dir = dest_root / ".migration-reports"
    backup_root = dest_root / ".migration-repair-backups" / stamp
    report_dir.mkdir(parents=True, exist_ok=True)
    report_dir.chmod(0o700)
    results = []

    candidates = []
    if only_name:
        path = dest_root / only_name
        if path.is_dir() and _is_migrated_instance(path):
            candidates = [path]
    else:
        candidates = [p for p in sorted(dest_root.iterdir(), key=lambda x: x.name.lower()) if p.is_dir() and not p.name.startswith(".") and _is_migrated_instance(p)]

    for instance_dir in candidates:
        result = repair_one_migrated(template, instance_dir)
        new_text = result.pop("_new_text", None)
        if result.get("changed") and new_text is not None:
            config_path = instance_dir / "config.ini"
            backup_dir = backup_root / instance_dir.name
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_dir.chmod(0o700)
            if config_path.is_file():
                shutil.copy2(config_path, backup_dir / "config.ini")
                (backup_dir / "config.ini").chmod(0o600)
            tmp = instance_dir / ".config.ini.repair.tmp"
            tmp.write_text(new_text, encoding="utf-8")
            tmp.chmod(0o640)
            tmp.replace(config_path)
            config_path.chmod(0o640)
            result["backup"] = str(backup_dir / "config.ini") if (backup_dir / "config.ini").exists() else None
            print(f"ซ่อม config ที่ migrate แล้ว: {instance_dir.name}")
        elif result.get("failed"):
            print(f"WARNING: ซ่อม {instance_dir.name} อัตโนมัติไม่ได้: {result.get('reason')}", file=sys.stderr)
        results.append(result)

    report = {
        "repair": "previously migrated TTMediaBot instances -> current SNTalkBot config schema",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "destination_root": str(dest_root),
        "schema_policy": "current-template + preserve-valid-current-values + safe-coercion",
        "secret_values_logged": False,
        "results": results,
    }
    report_path = report_dir / f"ttmediabot-repair-{stamp}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.chmod(0o600)
    changed = sum(1 for row in results if row.get("changed"))
    failed = sum(1 for row in results if row.get("failed"))
    print(f"ตรวจ config ที่ migrate แล้ว {len(results)} instance; ซ่อม {changed}; ซ่อมไม่ได้ {failed}")
    print(f"Migration repair report: {report_path}")
    return results


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
    seen = set()
    for item in values:
        # Never stringify nested legacy objects into a current username list.
        text = scalar_text(item, None, max_len=255)
        if text and text not in seen:
            seen.add(text)
            cleaned.append(text)
    return ",".join(cleaned)


def blocked_text(values) -> str:
    if not isinstance(values, list):
        return ""
    out = []
    seen = set()
    for item in values:
        text = scalar_text(item, None, max_len=128)
        if text is None:
            continue
        name = text.lstrip("/").lower()
        # Current command names are simple token-like strings; reject old
        # containers/whitespace payloads instead of poisoning blocked_commands.
        if not re.fullmatch(r"[a-z0-9_.-]{1,64}", name):
            continue
        if name not in seen:
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
    """Translate one supported TTMediaBot v1 config into current SNTalkBot schema.

    The current SNTalkBot template is authoritative: every current field starts
    from its release default, only explicitly supported legacy values are
    overlaid, invalid/missing legacy values leave that default untouched, and
    unsupported legacy keys never enter config.ini.
    """
    cfg = configparser.ConfigParser(interpolation=None)
    with template.open("r", encoding="utf-8") as fh:
        cfg.read_file(fh)

    general = old.get("general", {}) if isinstance(old.get("general"), dict) else {}
    player = old.get("player", {}) if isinstance(old.get("player"), dict) else {}
    tt = old.get("teamtalk", {}) if isinstance(old.get("teamtalk"), dict) else {}
    users = tt.get("users", {}) if isinstance(tt.get("users"), dict) else {}

    player_enabled, manager_enabled, _ = ROLE_MAP[role]
    set_if(cfg, "features", "player_enabled", bool_text(player_enabled))
    set_if(cfg, "features", "server_management_enabled", bool_text(manager_enabled))

    # TeamTalk connection. Required values were checked during discovery, but
    # still coerce them so malformed legacy scalar types cannot poison config.ini.
    set_if(cfg, "server", "address", scalar_text(tt.get("hostname"), "localhost", max_len=255))
    tcp = bounded_int(tt.get("tcp_port"), 10333, minimum=1, maximum=65535)
    udp = bounded_int(tt.get("udp_port"), tcp, minimum=1, maximum=65535)
    set_if(cfg, "server", "tcp_port", tcp)
    set_if(cfg, "server", "udp_port", udp)
    encrypted = strict_bool(tt.get("encrypted"), None)
    set_if(cfg, "server", "encrypted", bool_text(encrypted) if encrypted is not None else None)
    set_if(cfg, "server", "username", scalar_text(tt.get("username"), None, max_len=255))
    # Empty password is valid, but non-scalar containers are not.
    password = tt.get("password")
    if password is not None and not isinstance(password, (dict, list, tuple, set)):
        set_if(cfg, "server", "password", str(password))

    language = scalar_text(general.get("language"), None, max_len=16)
    if language:
        language = language.casefold().replace("_", "-").split("-", 1)[0]
        if language in SUPPORTED_LANGUAGES:
            set_if(cfg, "bot", "language", language)
    set_if(cfg, "bot", "nickname", scalar_text(tt.get("nickname"), None, max_len=255))
    set_if(cfg, "bot", "default_channel", scalar_text(tt.get("channel"), None, max_len=1024))
    channel_password = tt.get("channel_password")
    if channel_password is not None and not isinstance(channel_password, (dict, list, tuple, set)):
        set_if(cfg, "bot", "channel_password", str(channel_password))
    set_if(cfg, "bot", "status_message", scalar_text(tt.get("status"), None, max_len=512))
    gender = GENDER_MAP.get((scalar_text(tt.get("gender"), "") or "").casefold())
    set_if(cfg, "bot", "gender", gender)
    set_if(cfg, "bot", "reconnection_attempts", bounded_int(tt.get("reconnection_attempts"), None, minimum=-1, maximum=1000000))
    set_if(cfg, "bot", "reconnection_timeout", bounded_int(tt.get("reconnection_timeout"), None, minimum=1, maximum=3600))
    blocked = blocked_text(general.get("blocked_commands"))
    if blocked:
        set_if(cfg, "bot", "blocked_commands", blocked)

    # A migrated Player should not accidentally gain manager-side monitoring.
    if not manager_enabled:
        set_if(cfg, "bot", "intercept_channel_messages", "False")
        set_if(cfg, "bot", "welcome_broadcast", "False")
        set_if(cfg, "bot", "welcome_mode", "0")
        set_if(cfg, "bot", "profanity_filter_enabled", "False")

    admins = csv_text(users.get("admins"))
    if admins:
        set_if(cfg, "accounts", "authorized_users", admins)
    set_if(cfg, "accounts", "detect_server_admins", "True")

    # Device IDs are deliberately not portable into the Docker audio bridge.
    set_if(cfg, "playback", "input_device", "auto")
    set_if(cfg, "playback", "output_device", "auto")
    set_if(cfg, "playback", "cookiefile_path", "/app/data/cookies.txt")
    set_if(cfg, "playback", "default_volume", bounded_int(player.get("default_volume"), None, minimum=0, maximum=100))
    set_if(cfg, "playback", "max_volume", bounded_int(player.get("max_volume"), None, minimum=1, maximum=150))
    set_if(cfg, "playback", "seek_step", bounded_int(player.get("seek_step"), None, minimum=1, maximum=3600))
    channel_messages = strict_bool(general.get("send_channel_messages"), None)
    set_if(cfg, "playback", "send_channel_messages", bool_text(channel_messages) if channel_messages is not None else None)
    # TTMediaBot v1 volume_fading is an enable/disable flag.  Its separate
    # volume_fading_interval controls the old implementation's step timing and
    # has no equivalent in current SNTalkBot, so only the boolean maps to the
    # current fade_enabled field; the current duration remains the template default.
    fading_enabled = strict_bool(player.get("volume_fading"), None)
    if fading_enabled is not None:
        set_if(cfg, "playback", "fade_enabled", bool_text(fading_enabled))

    license_name = tt.get("license_name")
    license_key = tt.get("license_key")
    if license_name is not None and not isinstance(license_name, (dict, list, tuple, set)):
        set_if(cfg, "teamtalk_license", "license_name", str(license_name))
    if license_key is not None and not isinstance(license_key, (dict, list, tuple, set)):
        set_if(cfg, "teamtalk_license", "license_key", str(license_key))

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
        try:
            cpu = float(cpu_match.group(1))
        except ValueError:
            cpu = 0.0
        if 0 < cpu <= 1024:
            lines.append(f"cpu={cpu:g}")
    if mem_match:
        memory = mem_match.group(1).strip()
        if re.fullmatch(r"[1-9][0-9]*(?:[kKmMgGtT])?", memory):
            lines.append(f"memory={memory.lower()}")
    if lines:
        (dest_dir / "limits.conf").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Migrate legacy TTMediaBot Docker Helper instances to TTUHelper/SNTalkBot")
    ap.add_argument("--source")
    ap.add_argument("--dest-root", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--mode", choices=["prompt", "player", "manager", "full", "ask"], default="prompt")
    ap.add_argument("--yes", action="store_true", help="Skip final confirmation")
    ap.add_argument("--replace", action="store_true", help="Replace existing SNTalkBot instance directories after backing them up")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--names-file")
    ap.add_argument("--repair-existing", action="store_true", help="Repair configs of previously migrated instances against the current template")
    ap.add_argument("--repair-name", help="Repair only one migrated instance name")
    args = ap.parse_args()

    dest_root = Path(args.dest_root).expanduser().resolve()
    template = Path(args.template).expanduser().resolve()
    if not template.is_file():
        fail(f"SNTalkBot config template not found: {template}")
    if args.repair_existing:
        repair_existing_migrated(template, dest_root, args.repair_name)
        return
    if not args.source:
        fail("--source is required unless --repair-existing is used")
    source = Path(args.source).expanduser().resolve()
    if not source.is_dir():
        fail(f"Legacy root not found: {source}")

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
    print("  สร้าง config.ini จาก template ปัจจุบันของ SNTalkBot แล้วทับเฉพาะค่า legacy ที่รองรับจริง")
    print("  server/port/encryption, nickname, login, channel, language, status/gender")
    print("  admin usernames, blocked commands, volume/max volume/seek, license และ cookies.txt")
    print("  ค่า legacy ที่ SNTalkBot ไม่มีหรือชนิด/ช่วงไม่ถูกต้องจะถูกทิ้ง; ค่าที่ SNTalkBot ต้องมีแต่ของเก่าไม่มีจะใช้ default ปัจจุบัน")
    print("  sound-device ID เก่าจะเปลี่ยนเป็น auto สำหรับ Docker audio bridge ใหม่")
    print("  raw config.json, TTMediaBot.log และ TTMediaBotCache.dat จะไม่ย้าย; โฟลเดอร์เก่ายังอยู่ที่เดิมเป็น backup")
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

            # Do not copy raw legacy config into the active runtime instance. The
            # original source directory is intentionally preserved in place and the
            # migration report records field names only, without secret values.
            mapped_fields, ignored_fields = migration_field_summary(data)
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
            (staged / "instance.conf").chmod(0o640)
            (staged / "MIGRATED_FROM_TTMEDIABOT.txt").chmod(0o640)
            limits_file = staged / "limits.conf"
            if limits_file.exists():
                limits_file.chmod(0o640)
            staged_items.append((source_dir, name, role, staged, cookies.is_file(), mapped_fields, ignored_fields))

        # Commit staged directories only after every conversion succeeded.
        for source_dir, name, role, staged, cookies_copied, mapped_fields, ignored_fields in staged_items:
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
                "schema_policy": "current-template + supported-legacy-allowlist",
                "mapped_legacy_fields": mapped_fields,
                "ignored_legacy_fields": ignored_fields,
                "raw_legacy_config_copied": False,
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
        "schema_policy": "current-template + supported-legacy-allowlist",
        "unsupported_values": "dropped",
        "missing_current_values": "kept from current SNTalkBot template defaults",
        "source_preserved": True,
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
