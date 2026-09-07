"""LDPlayer console integration; all commands target one explicit instance."""
from dataclasses import dataclass
import json
import locale
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from typing import Callable, List, Optional, Set, Tuple

from pubg_control.config.constants import PACKAGES
from pubg_control.core.models import Instance
from pubg_control.core.exceptions import (
    ADBConnectionError,
    GameLaunchError,
    LDPlayerCommandError,
    LDPlayerNotFoundError,
)

logger = logging.getLogger(__name__)


def installation_paths() -> List[Path]:
    """Read installation metadata, including custom paths on other computers."""
    if os.name != "nt":
        return []
    import winreg

    paths: List[Path] = []
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(
                    hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", 0, winreg.KEY_READ | view
                ) as root:
                    for i in range(winreg.QueryInfoKey(root)[0]):
                        try:
                            with winreg.OpenKey(root, winreg.EnumKey(root, i)) as key:
                                name = winreg.QueryValueEx(key, "DisplayName")[0]
                                if not re.search(r"ldplayer|leidian|雷电", name, re.I):
                                    continue
                                for field in ("InstallLocation", "DisplayIcon", "UninstallString"):
                                    try:
                                        value = winreg.QueryValueEx(key, field)[0]
                                        if field != "InstallLocation":
                                            match = re.match(r'"([^"]+)"|(.+?\.exe)', value, re.I)
                                            if not match:
                                                continue
                                            value = next(x for x in match.groups() if x)
                                        paths.append(Path(os.path.expandvars(value)))
                                    except OSError:
                                        pass
                        except OSError:
                            continue
            except OSError:
                pass

    # Running LDPlayer also identifies portable/custom installations without registry entries.
    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "@(Get-CimInstance Win32_Process -Filter \"Name='dnplayer.exe' OR Name='ldplayer.exe'\" | Select-Object -ExpandProperty ExecutablePath) | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            timeout=8,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        values = json.loads(result.stdout.decode("utf-8-sig", errors="replace") or "[]")
        if isinstance(values, str):
            values = [values]
        paths.extend(Path(value) for value in (values or []) if value)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        logger.debug("Failed checking running processes for LDPlayer paths: %s", exc)

    return paths


def find_console(preferred: str = "") -> str:
    """Discover the ldconsole.exe or dnconsole.exe binary path."""
    if preferred:
        saved = Path(preferred)
        if saved.name.lower() in ("ldconsole.exe", "dnconsole.exe") and saved.is_file():
            return str(saved.resolve())
    candidates = [Path(preferred)] if preferred else []
    candidates.extend(
        Path(value)
        for name in ("ldconsole.exe", "dnconsole.exe")
        if (value := shutil.which(name))
    )
    candidates.extend(installation_paths())
    roots = [
        Path(f"{drive}:/") / folder
        for drive in "CDEFGHIJKLMNOPQRSTUVWXYZ"
        for folder in ("LDPlayer", "leidian", "Program Files/LDPlayer")
    ]
    for candidate in candidates:
        root = candidate if candidate.is_dir() else candidate.parent
        roots.insert(0, root)
    for candidate in candidates:
        if candidate.name.lower() in ("ldconsole.exe", "dnconsole.exe") and candidate.is_file():
            return str(candidate.resolve())
    for root in roots:
        for folder in (root, root / "LDPlayer9", root / "LDPlayer4"):
            for name in ("ldconsole.exe", "dnconsole.exe"):
                candidate = folder / name
                if candidate.is_file():
                    return str(candidate)
    return ""


class LDPlayer:
    """Enterprise client for controlling LDPlayer instances via console commands and ADB."""

    def __init__(self, console: str | Path):
        self.console = Path(console)
        if (
            self.console.name.lower() not in ("ldconsole.exe", "dnconsole.exe")
            or not self.console.is_file()
        ):
            raise ValueError("Hãy chọn ldconsole.exe hoặc dnconsole.exe trong thư mục LDPlayer.")

    def command(self, *args, timeout: int = 20) -> str:
        """Execute a command against the ldconsole CLI."""
        cmd_list = [str(self.console), *map(str, args)]
        logger.debug("Running LDPlayer command: %s", cmd_list)
        result = subprocess.run(
            cmd_list,
            cwd=self.console.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

        def decode(data: bytes) -> str:
            try:
                return data.decode("utf-8").strip()
            except UnicodeDecodeError:
                return data.decode(locale.getpreferredencoding(False), errors="replace").strip()

        output, error = decode(result.stdout), decode(result.stderr)
        if result.returncode:
            raise RuntimeError(error or output or f"LDPlayer trả mã lỗi {result.returncode}.")
        return output

    def instances(self) -> List[Instance]:
        """Query all emulator instances registered in LDPlayer."""
        rows: List[Instance] = []
        for line in self.command("list2").splitlines():
            fields = line.split(",")
            if len(fields) >= 7:
                try:
                    rows.append(
                        Instance(
                            index=int(fields[0]),
                            name=fields[1],
                            hwnd=int(fields[2]),
                            ready=fields[4] == "1",
                        )
                    )
                except ValueError:
                    continue
        return rows

    def adb(self, index: int, command: str) -> str:
        """Run an ADB shell command on a specific emulator instance."""
        return self.command("adb", "--index", index, "--command", command)

    def connect_adb(self, index: int) -> str:
        """Let LDPlayer resolve its own device/port; verify ADB and retrieve resolution."""
        output = self.adb(index, "shell echo PU_ADB_CONNECTED")
        if "PU_ADB_CONNECTED" not in output.splitlines():
            raise RuntimeError(
                "ADB chưa sẵn sàng. Bật Open local connection trong LDPlayer và khởi động lại máy ảo, sau đó bấm Làm mới. "
                + output[:200]
            )
        return self.adb(index, "shell wm size").strip()

    def open(
        self,
        index: int,
        package: str,
        cancel: threading.Event,
        report: Callable[[str], None],
        game: bool = True,
        timeout: int = 150,
    ) -> Optional[Tuple[Instance, str]]:
        """Launch an emulator instance, wait for boot, and start the game package."""
        rows = self.instances()
        selected = next((row for row in rows if row.index == index), None)
        if selected is None:
            raise RuntimeError("Máy ảo đã bị xóa hoặc không tồn tại. Hãy làm mới danh sách.")

        if not selected.ready:
            report("Đang khởi động LDPlayer…")
            self.command("launch", "--index", index)

        deadline = time.monotonic() + timeout
        adb_errors = 0

        while time.monotonic() < deadline:
            if cancel.is_set():
                return None
            selected = next((row for row in self.instances() if row.index == index), None)
            if selected and selected.ready:
                if not game:
                    break
                boot = self.adb(index, "shell getprop sys.boot_completed")
                if "1" in boot.splitlines():
                    break
                if "not found" in boot or "offline" in boot or "error:" in boot:
                    adb_errors += 1
                    if adb_errors >= 8:
                        raise RuntimeError(
                            "LDPlayer đã mở nhưng ADB chưa kết nối. Trong LDPlayer, vào Settings → Other settings → ADB debugging → Open local connection, lưu và khởi động lại giả lập rồi thử lại."
                        )
            if cancel.wait(2):
                return None
        else:
            raise TimeoutError("LDPlayer chưa sẵn sàng sau 150 giây. Kiểm tra cửa sổ giả lập rồi thử lại.")

        if not game:
            return selected, "LDPlayer đã sẵn sàng."

        report("Đang kiểm tra PUBG đã cài…")
        installed: Set[str] = set(
            re.findall(r"^package:([^\s]+)", self.adb(index, "shell pm list packages"), re.MULTILINE)
        )
        if not installed:
            raise RuntimeError("Chưa đọc được ứng dụng trong LDPlayer. Kiểm tra kết nối ADB trong cài đặt giả lập.")

        if not package:
            candidates = [val for val in PACKAGES.values() if val and val in installed]
            if len(candidates) > 1:
                raise RuntimeError("Có nhiều bản PUBG. Hãy chọn bản muốn mở trong mục Phiên bản game.")
            if not candidates:
                raise RuntimeError("Chưa tìm thấy PUBG Mobile trong máy ảo này. Hãy cài game trong LDPlayer rồi thử lại.")
            package = candidates[0]

        if package not in installed:
            raise RuntimeError("Bản PUBG đã chọn chưa được cài trên máy ảo này. Chọn đúng phiên bản hoặc cài game trước.")

        if cancel.is_set():
            return None

        report("Đang mở PUBG Mobile…")
        self.command("runapp", "--index", index, "--packagename", package)
        for _ in range(12):
            if cancel.wait(1):
                return None
            if re.search(r"\b\d+\b", self.adb(index, f"shell pidof {package}")):
                return selected, f"PUBG đã khởi chạy ({package})."

        raise RuntimeError("Đã gửi lệnh mở nhưng chưa xác nhận được PUBG đang chạy. Kiểm tra màn hình LDPlayer.")
