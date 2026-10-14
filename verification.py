from __future__ import annotations
import asyncio
import os
import shlex
from pathlib import Path

ALLOWED_PROGRAMS = {"pytest", "python", "python3", "npm", "npx", "ruff", "mypy", "git"}

async def run_check(root: str | Path, command: str, timeout: int = 120) -> dict:
    root = Path(root).resolve()
    parts = shlex.split(command, posix=(os.name != "nt"))
    if not parts or Path(parts[0]).name.lower() not in ALLOWED_PROGRAMS:
        return {"command": command, "returncode": 126, "stdout": "", "stderr": "Command not allowed"}
    if any(x in {";", "&&", "||", "|", ">", "<", "$(", "`"} for x in parts):
        return {"command": command, "returncode": 126, "stdout": "", "stderr": "Shell operators not allowed"}
    proc = await asyncio.create_subprocess_exec(*parts, cwd=root, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {"command": command, "returncode": proc.returncode, "stdout": out.decode(errors="replace")[-10000:], "stderr": err.decode(errors="replace")[-10000:]}
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return {"command": command, "returncode": 124, "stdout": "", "stderr": "Timed out"}
