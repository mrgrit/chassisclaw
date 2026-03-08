import shutil
import subprocess
from fastapi import APIRouter

router = APIRouter()

def _has_cmd(name: str) -> bool:
    return shutil.which(name) is not None

@router.get("/capabilities")
def capabilities():
    return {
        "ok": True,
        "sudo": _has_cmd("sudo"),
        "systemctl": _has_cmd("systemctl"),
        "docker": _has_cmd("docker"),
        "package_manager": "apt" if _has_cmd("apt") else ("dnf" if _has_cmd("dnf") else ("yum" if _has_cmd("yum") else None)),
        "python": subprocess.getoutput("python3 --version"),
        "node": subprocess.getoutput("node --version") if _has_cmd("node") else None,
    }
