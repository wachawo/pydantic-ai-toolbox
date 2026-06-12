#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Host system information toolset (psutil-backed, read-only)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

from ..base import BaseToolset, tool

logger = logging.getLogger(__name__)

DEFAULT_MAX_PROCESSES = 50
BYTES_PER_GB = 1024**3
BYTES_PER_MB = 1024**2


def require_psutil() -> Any:
    try:
        import psutil
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            "SystemToolset requires psutil. Install it with: pip install 'pydantic-ai-toolbox[system]'"
        ) from exc
    return psutil


class SystemToolset(BaseToolset):
    """Read-only view of the host: CPU, memory, disks, uptime, load, processes, network, battery.

    Every tool reports observations only — nothing here can mutate the system,
    signal processes, or read file contents. Process listings are capped at
    `max_processes` per call (constructor cap wins over the per-call argument).
    """

    def __init__(self, max_processes: int = DEFAULT_MAX_PROCESSES) -> None:
        require_psutil()  # fail fast at construction, not on first tool call
        self.max_processes = max_processes
        super().__init__()
        logger.info(f"SystemToolset ready: max_processes={self.max_processes}")

    @tool
    def cpu_info(self) -> dict:
        """Return CPU information: physical/logical core counts, current utilisation percent, frequency in MHz."""
        psutil = require_psutil()
        freq = psutil.cpu_freq()
        return {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "percent": psutil.cpu_percent(interval=0.1),
            "freq_mhz": round(freq.current) if freq else None,
        }

    @tool
    def memory_info(self) -> dict:
        """Return RAM and swap usage: totals, available, and used percent (GB, rounded to 0.1)."""
        psutil = require_psutil()
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "total_gb": round(mem.total / BYTES_PER_GB, 1),
            "available_gb": round(mem.available / BYTES_PER_GB, 1),
            "used_percent": mem.percent,
            "swap_total_gb": round(swap.total / BYTES_PER_GB, 1),
            "swap_used_percent": swap.percent,
        }

    @tool
    def disk_usage(self, path: str = "/") -> dict:
        """Return disk usage for the filesystem containing `path`: total and free GB plus used percent.

        `used_percent` is computed as (total - free) / total, which is unambiguous
        across platforms (psutil's own `percent` measures the APFS snapshot volume
        on macOS and confuses agents)."""
        psutil = require_psutil()
        usage = psutil.disk_usage(path)
        return {
            "path": path,
            "total_gb": round(usage.total / BYTES_PER_GB, 1),
            "free_gb": round(usage.free / BYTES_PER_GB, 1),
            "used_percent": round((usage.total - usage.free) / usage.total * 100, 1),
        }

    @tool
    def disk_partitions(self) -> list[dict]:
        """List mounted disk partitions: device, mountpoint, and filesystem type."""
        psutil = require_psutil()
        return [
            {"device": part.device, "mountpoint": part.mountpoint, "fstype": part.fstype}
            for part in psutil.disk_partitions(all=False)
        ]

    @tool
    def uptime(self) -> dict:
        """Return the boot time (ISO-8601 UTC) and uptime in hours."""
        psutil = require_psutil()
        import time

        boot = psutil.boot_time()
        return {
            "boot_time": datetime.fromtimestamp(boot, tz=timezone.utc).isoformat(),
            "uptime_hours": round((time.time() - boot) / 3600, 1),
        }

    @tool
    def load_avg(self) -> dict:
        """Return the 1/5/15-minute load averages."""
        psutil = require_psutil()
        one, five, fifteen = psutil.getloadavg()
        return {"1min": round(one, 2), "5min": round(five, 2), "15min": round(fifteen, 2)}

    @tool
    def top_processes(self, sort_by: Literal["cpu", "memory"] = "cpu", limit: int = 10) -> list[dict]:
        """List the heaviest processes by CPU or memory: pid, name, cpu percent, RSS in MB.

        `limit` is clamped to the toolset's `max_processes`."""
        psutil = require_psutil()
        limit = max(1, min(limit, self.max_processes))
        processes: list[dict] = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                info = proc.info
                mem = info.get("memory_info")
                processes.append(
                    {
                        "pid": info["pid"],
                        "name": info.get("name") or "?",
                        "cpu_percent": info.get("cpu_percent") or 0.0,
                        "memory_mb": round(mem.rss / BYTES_PER_MB, 1) if mem else 0.0,
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        key = "cpu_percent" if sort_by == "cpu" else "memory_mb"
        processes.sort(key=lambda item: item[key], reverse=True)
        return processes[:limit]

    @tool
    def network_io(self) -> dict:
        """Return cumulative network I/O since boot: bytes and packets sent/received."""
        psutil = require_psutil()
        counters = psutil.net_io_counters()
        return {
            "bytes_sent": counters.bytes_sent,
            "bytes_recv": counters.bytes_recv,
            "packets_sent": counters.packets_sent,
            "packets_recv": counters.packets_recv,
        }

    @tool
    def battery(self) -> dict | None:
        """Return battery state (percent, plugged-in flag) or None when no battery is present."""
        psutil = require_psutil()
        state = psutil.sensors_battery()
        if state is None:
            return None
        return {"percent": round(state.percent, 1), "plugged": bool(state.power_plugged)}


def main() -> None:
    pass


if __name__ == "__main__":
    main()
