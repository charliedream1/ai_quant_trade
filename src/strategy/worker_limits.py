"""OS memory/process limits supplement the reviewed-code policy on both platforms."""

import ctypes
import os
from ctypes import wintypes


class BasicLimit(ctypes.Structure):
    _fields_ = [
        ("process_time", ctypes.c_longlong),
        ("job_time", ctypes.c_longlong),
        ("flags", wintypes.DWORD),
        ("minimum", ctypes.c_size_t),
        ("maximum", ctypes.c_size_t),
        ("processes", wintypes.DWORD),
        ("affinity", ctypes.c_size_t),
        ("priority", wintypes.DWORD),
        ("scheduling", wintypes.DWORD),
    ]


class Counters(ctypes.Structure):
    _fields_ = [
        (name, ctypes.c_ulonglong) for name in ("read", "write", "other", "read_bytes", "write_bytes", "other_bytes")
    ]


class ExtendedLimit(ctypes.Structure):
    _fields_ = [
        ("basic", BasicLimit),
        ("io", Counters),
        ("process_memory", ctypes.c_size_t),
        ("job_memory", ctypes.c_size_t),
        ("peak_process", ctypes.c_size_t),
        ("peak_job", ctypes.c_size_t),
    ]


def attach_limits(process, maximum_memory: int):
    if os.name != "nt":
        return None
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    handle = kernel.CreateJobObjectW(None, None)
    limits = ExtendedLimit()
    limits.basic.flags = 0x2000 | 0x100 | 0x8  # Kill on close, memory bound, no descendants.
    limits.basic.processes = 2  # Windows venv launcher plus the actual interpreter.
    limits.process_memory = maximum_memory
    if (
        not handle
        or not kernel.SetInformationJobObject(handle, 9, ctypes.byref(limits), ctypes.sizeof(limits))
        or not kernel.AssignProcessToJobObject(handle, int(process._handle))
    ):
        if handle:
            kernel.CloseHandle(wintypes.HANDLE(handle))
        raise OSError("无法对策略工作进程设置系统资源限制")
    return handle


def close_limits(handle):
    if handle is not None and os.name == "nt":
        ctypes.WinDLL("kernel32").CloseHandle(wintypes.HANDLE(handle))
