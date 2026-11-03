"""Defense in depth for reviewed code, not a sandbox for arbitrary untrusted Python."""

import importlib
import os
import sys
from pathlib import Path

from src.core.config import PROJECT_ROOT


def install_policy(work: Path, source: Path, memory: int):
    allowed = [
        Path(sys.prefix).resolve(),
        Path(sys.base_prefix).resolve(),
        (PROJECT_ROOT / "src").resolve(),
        work.resolve(),
    ]
    protected = {".env", ".llm_env", ".secrets", "auth.json", "config.toml"}
    denied = {
        "socket.connect",
        "socket.bind",
        "subprocess.Popen",
        "os.system",
        "os.exec",
        "os.spawn",
        "os.fork",
        "ctypes.dlopen",
        "os.link",
        "os.symlink",
    }

    def audit(event, args):
        if event in denied or event.startswith(("os.exec", "os.spawn")):
            raise PermissionError("策略工作进程不允许此系统能力：" + event)
        if event == "open" and args and not isinstance(args[0], int):
            target = Path(args[0]).resolve()
            flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
            writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC))
            if target.name in protected or target.name.startswith((".llm_env.", ".env.")):
                raise PermissionError("策略不能读取配置凭据")
            if writing and not target.is_relative_to(work.resolve()):
                raise PermissionError("策略不能写入工作目录以外的文件")
            if not writing and target != source.resolve() and not any(target.is_relative_to(base) for base in allowed):
                raise PermissionError("策略不能读取未授权目录")
        if event in {"os.remove", "os.rename", "os.rmdir", "os.mkdir", "os.chmod", "os.truncate"}:
            for raw in args[:2] if event == "os.rename" else args[:1]:
                if isinstance(raw, (str, bytes)) and not Path(os.fsdecode(raw)).resolve().is_relative_to(
                    work.resolve()
                ):
                    raise PermissionError("策略不能修改工作目录以外的路径")

    sys.addaudithook(audit)
    if os.name != "nt":
        resource = importlib.import_module("resource")
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
