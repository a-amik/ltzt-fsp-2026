"""Песочница для задач с кодом: решение кандидата на Python запускается отдельным процессом со скрытыми тестами.

Слои защиты, от внешнего к внутреннему:
1. Отдельный процесс `python -I -S` во временной пустой папке, с пустым окружением.
2. Лимиты ядра (setrlimit): процессорное время, память, размер файлов, число открытых файлов, новые процессы.
3. Жёсткий тайм-аут по часам и убийство процесса.
4. Аудит-хук Python (PEP 578), который нельзя снять изнутри: запрещены сеть, запуск процессов,
   запись в файлы, импорт ctypes и других модулей, обходящих хук.
5. На Linux, если позволяет ядро, — отдельное сетевое пространство (`unshare -rn`): сети нет вовсе.

Это изоляция уровня прототипа: для боевого режима решение уходит в контейнер без сети (gVisor/Firecracker),
интерфейс функции `run` при этом не меняется.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

CPU_SEC = 2
MEM_BYTES = 256 * 1024 * 1024
WALL_SEC = 4
MAX_OUT = 64 * 1024

PRELUDE = r'''
import sys, json
_BLOCK = ("socket.", "subprocess.", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork", "os.kill",
          "os.remove", "os.rename", "os.rmdir", "os.mkdir", "shutil.", "ctypes.", "winreg.", "urllib.", "http.")
_NO_IMPORT = {"ctypes", "_ctypes", "socket", "_socket", "subprocess", "multiprocessing", "threading", "_thread", "signal", "resource"}
def _hook(event, args):
    if event == "import" and args and str(args[0]).split(".")[0] in _NO_IMPORT:
        raise PermissionError("импорт запрещён в песочнице: " + str(args[0]))
    if event == "open" and len(args) > 1 and args[1] and any(c in str(args[1]) for c in "wax+"):
        raise PermissionError("запись в файлы запрещена")
    if event.startswith(_BLOCK):
        raise PermissionError("запрещено в песочнице: " + event)
_data = json.loads(sys.stdin.read())
sys.addaudithook(_hook)
_ns = {"__name__": "solution"}
try:
    exec(compile(_data["code"], "solution.py", "exec"), _ns)
except BaseException as e:
    print(json.dumps({"error": type(e).__name__ + ": " + str(e)[:200]})); raise SystemExit(0)
_fn = _ns.get(_data["fn"])
if not callable(_fn):
    print(json.dumps({"error": "нет функции " + _data["fn"]})); raise SystemExit(0)
_out = []
for _args in _data["tests"]:
    try:
        _out.append({"ok": True, "v": _fn(*_args)})
    except BaseException as e:
        _out.append({"ok": False, "e": type(e).__name__})
print(json.dumps({"results": _out}, default=str))
'''


def _limits():  # выполняется в дочернем процессе до exec
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SEC, CPU_SEC))
    try:
        resource.setrlimit(resource.RLIMIT_AS, (MEM_BYTES, MEM_BYTES))
    except (ValueError, OSError):  # macOS не даёт ограничить адресное пространство
        pass
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    if hasattr(resource, "RLIMIT_NPROC"):
        try:
            resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
        except (ValueError, OSError):
            pass
    os.setsid()


_UNSHARE: list[str] | None = None


def _netns_prefix() -> list[str]:
    """`unshare -rn`, если ядро разрешает непривилегированные пространства имён; иначе без него."""
    global _UNSHARE
    if _UNSHARE is None:
        _UNSHARE = []
        if sys.platform.startswith("linux") and shutil.which("unshare"):
            try:
                if subprocess.run(["unshare", "-rn", "true"], capture_output=True, timeout=3).returncode == 0:
                    _UNSHARE = ["unshare", "-rn"]
            except (OSError, subprocess.SubprocessError):
                pass
    return _UNSHARE


def run(code: str, fn: str, tests: list[tuple[list, object]]) -> dict:
    """Запустить решение на тестах. tests: [(аргументы, ожидаемое значение)]. Возвращает долю пройденных и разбор."""
    payload = json.dumps({"code": code, "fn": fn, "tests": [a for a, _ in tests]})
    with tempfile.TemporaryDirectory(prefix="rz-sbx-") as tmp:
        cmd = _netns_prefix() + [sys.executable, "-I", "-S", "-c", PRELUDE]
        try:
            p = subprocess.run(cmd, input=payload, capture_output=True, text=True, timeout=WALL_SEC, cwd=tmp,
                               env={"PYTHONIOENCODING": "utf-8"}, preexec_fn=_limits)
        except subprocess.TimeoutExpired:
            return {"passed": 0, "total": len(tests), "score": 0.0, "error": f"превышено время ({WALL_SEC} с)"}
    out = (p.stdout or "")[-MAX_OUT:].strip().splitlines()
    try:
        res = json.loads(out[-1]) if out else {}
    except json.JSONDecodeError:
        res = {}
    if "error" in res or "results" not in res:
        err = res.get("error") or ("процесс остановлен: превышены лимиты" if p.returncode else "решение ничего не вернуло")
        return {"passed": 0, "total": len(tests), "score": 0.0, "error": err}
    passed = sum(1 for r, (_, want) in zip(res["results"], tests) if r.get("ok") and json.dumps(r.get("v")) == json.dumps(want))
    return {"passed": passed, "total": len(tests), "score": round(passed / len(tests), 3) if tests else 0.0, "error": None}
