#!/usr/bin/env python3
"""XploClone doctor / preflight — prints CPU/RAM/disk/GPU/Docker status.

Usage:
    python3 scripts/doctor.py            # human-readable report, exit 0/1
    python3 scripts/doctor.py --json     # machine-readable JSON

Exit 0 = ready for CPU test mode. Exit 1 = something is missing for the
requested mode (Docker missing, or --gpu and no NVIDIA GPU). Warnings
do not fail the check — they are printed as WARN lines. No secrets are
printed: .env values are reported as set/empty only, never their values.
No network calls, no model downloads.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], timeout: int = 10) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (out.stdout or "").strip() or None
    except Exception:
        return None


def _cpu_info() -> dict:
    cores = os.cpu_count() or 0
    model = "unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                model = line.split(":", 1)[1].strip()
                break
    except OSError:
        model = platform.processor() or "unknown"
    return {"cores": cores, "model": model}


def _mem_gb() -> dict:
    total = free = 0.0
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                total = int(line.split()[1]) / 1024 / 1024
            elif line.startswith("MemAvailable:"):
                free = int(line.split()[1]) / 1024 / 1024
    except OSError:
        pass
    return {"total_gb": round(total, 1), "available_gb": round(free, 1)}


def _disk_gb() -> dict:
    try:
        usage = shutil.disk_usage(REPO)
        return {
            "total_gb": round(usage.total / 1e9, 1),
            "free_gb": round(usage.free / 1e9, 1),
        }
    except OSError:
        return {"total_gb": 0.0, "free_gb": 0.0}


def _gpu_info() -> dict:
    out = _run(
        ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"]
    )
    if out:
        parts = [p.strip() for p in out.split(",")]
        return {
            "present": True,
            "name": parts[0] if parts else "unknown",
            "vram": parts[1] if len(parts) > 1 else "unknown",
            "driver": parts[2] if len(parts) > 2 else "unknown",
        }
    return {"present": False, "name": None, "vram": None, "driver": None}


def _docker_info() -> dict:
    docker = shutil.which("docker") is not None
    compose = False
    if docker:
        compose = (
            _run(["docker", "compose", "version"]) is not None
            or shutil.which("docker-compose") is not None
        )
    return {
        "docker": docker,
        "compose": compose,
        "version": _run(["docker", "--version"]) if docker else None,
    }


def _env_status() -> dict:
    env_file = REPO / ".env"
    status: dict[str, object] = {"file_present": env_file.exists(), "vars": {}}
    if not env_file.exists():
        return status
    wanted = [
        "XPLOCLONE_API_KEY_HASH",
        "XPLOCLONE_API_KEY",
        "XPLOCLONE_WEB_PASSWORD_HASH",
        "XPLOCLONE_WEB_SESSION_SECRET",
        "XPLOCLONE_DEVICE",
        "XPLOCLONE_ENGINE",
    ]
    values: dict[str, str] = {}
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, val = line.split("=", 1)
            values[key.strip()] = val.strip()
    status["vars"] = {k: ("set" if values.get(k) else "empty/missing") for k in wanted}
    return status


def _reference_status() -> dict:
    ref = REPO / "api" / "reference"
    found = {}
    for name in ("mubashir-en-us.wav", "mubashir-en-gb.wav", "mubashir-ur.wav"):
        p = ref / name
        size = round(p.stat().st_size / 1e6, 1) if p.is_file() else 0.0
        found[name] = {"present": p.is_file(), "size_mb": size}
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="XploClone preflight doctor")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--gpu", action="store_true", help="require an NVIDIA GPU")
    args = parser.parse_args()

    report = {
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python": sys.version.split()[0],
        "cpu": _cpu_info(),
        "memory": _mem_gb(),
        "disk": _disk_gb(),
        "gpu": _gpu_info(),
        "docker": _docker_info(),
        "env": _env_status(),
        "reference_clips": _reference_status(),
    }
    warnings: list[str] = []
    errors: list[str] = []
    if report["cpu"]["cores"] < 4:
        warnings.append(
            f"Only {report['cpu']['cores']} CPU cores — CPU mode will be slow "
            "(Nano wants 8 threads)."
        )
    if report["memory"]["total_gb"] and report["memory"]["total_gb"] < 8:
        warnings.append(
            f"Only {report['memory']['total_gb']} GB RAM — 8 GB minimum for CPU "
            "mode, 16 GB recommended."
        )
    if report["disk"]["free_gb"] < 10:
        warnings.append(
            f"Only {report['disk']['free_gb']} GB disk free — models + images need ~10 GB."
        )
    if not report["docker"]["docker"]:
        errors.append("Docker is not installed (required for ./install.sh).")
    elif not report["docker"]["compose"]:
        errors.append("Docker Compose was not found.")
    if args.gpu and not report["gpu"]["present"]:
        errors.append("GPU mode requested but no NVIDIA GPU was detected (nvidia-smi).")
    if not report["gpu"]["present"]:
        warnings.append("No NVIDIA GPU — GPU mode unavailable; CPU mode (Nano) is the fallback.")
    if not report["reference_clips"]["mubashir-en-us.wav"]["present"]:
        warnings.append(
            "No mubashir-en-us.wav reference clip — English voices will report unavailable."
        )
    if not report["reference_clips"]["mubashir-en-gb.wav"]["present"]:
        warnings.append(
            "No mubashir-en-gb.wav reference clip — English voices will report unavailable."
        )
    report["warnings"] = warnings
    report["errors"] = errors
    report["ready_cpu"] = not errors
    report["ready_gpu"] = not errors and bool(report["gpu"]["present"])

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("XploClone doctor — preflight report")
        print(f"  OS:        {report['os']}")
        print(f"  Python:    {report['python']}")
        print(f"  CPU:       {report['cpu']['cores']} cores — {report['cpu']['model']}")
        print(
            f"  Memory:    {report['memory']['total_gb']} GB total, "
            f"{report['memory']['available_gb']} GB available"
        )
        print(f"  Disk free: {report['disk']['free_gb']} GB")
        gpu = report["gpu"]
        if gpu["present"]:
            gpu_line = f"yes — {gpu['name']} ({gpu['vram']}, driver {gpu['driver']})"
        else:
            gpu_line = "no NVIDIA GPU detected"
        print(f"  GPU:       {gpu_line}")
        print(
            f"  Docker:    {'yes' if report['docker']['docker'] else 'NO'}  "
            f"Compose: {'yes' if report['docker']['compose'] else 'NO'}"
        )
        env_state = "present" if report["env"]["file_present"] else "missing — run ./install.sh"
        print(f"  .env:      {env_state}")
        for name, info in report["reference_clips"].items():
            state = f"present ({info['size_mb']} MB)" if info["present"] else "missing"
            print(f"  {name}: {state}")
        for w in warnings:
            print(f"  WARN: {w}")
        for e in errors:
            print(f"  ERROR: {e}")
        print(f"  Ready for CPU mode: {'yes' if report['ready_cpu'] else 'no'}")
        print(f"  Ready for GPU mode: {'yes' if report['ready_gpu'] else 'no'}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
