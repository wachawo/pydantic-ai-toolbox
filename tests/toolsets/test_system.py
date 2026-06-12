#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for SystemToolset."""

from __future__ import annotations

import pytest

pytest.importorskip("psutil")

from pydantic_ai_toolbox.toolsets.system import SystemToolset  # noqa: E402


class TestConstructor:
    def test_defaults(self) -> None:
        tk = SystemToolset()
        assert tk.max_processes == 50

    def test_registers_tools(self) -> None:
        tk = SystemToolset()
        names = set(tk.tools)
        assert {
            "cpu_info",
            "memory_info",
            "disk_usage",
            "disk_partitions",
            "uptime",
            "load_avg",
            "top_processes",
            "network_io",
            "battery",
        } <= names


class TestCpuMemory:
    def test_cpu_info_shape(self) -> None:
        info = SystemToolset().cpu_info()
        assert info["logical_cores"] >= 1
        assert 0.0 <= info["percent"] <= 100.0

    def test_memory_info_shape(self) -> None:
        info = SystemToolset().memory_info()
        assert info["total_gb"] > 0
        assert 0.0 <= info["used_percent"] <= 100.0
        assert info["available_gb"] <= info["total_gb"]


class TestDisk:
    def test_disk_usage_root(self) -> None:
        usage = SystemToolset().disk_usage("/")
        assert usage["total_gb"] > 0
        assert 0.0 <= usage["used_percent"] <= 100.0
        assert usage["free_gb"] <= usage["total_gb"]

    def test_disk_usage_consistent_percent(self) -> None:
        usage = SystemToolset().disk_usage("/")
        recomputed = (usage["total_gb"] - usage["free_gb"]) / usage["total_gb"] * 100
        assert abs(usage["used_percent"] - recomputed) < 1.0

    def test_disk_usage_missing_path_raises(self) -> None:
        with pytest.raises(OSError):
            SystemToolset().disk_usage("/definitely/not/a/path")

    def test_partitions_have_mountpoints(self) -> None:
        parts = SystemToolset().disk_partitions()
        assert parts
        assert all("mountpoint" in part for part in parts)


class TestUptimeLoad:
    def test_uptime_positive(self) -> None:
        info = SystemToolset().uptime()
        assert info["uptime_hours"] >= 0
        assert info["boot_time"].endswith("+00:00") or "T" in info["boot_time"]

    def test_load_avg_keys(self) -> None:
        load = SystemToolset().load_avg()
        assert set(load) == {"1min", "5min", "15min"}


class TestProcesses:
    def test_top_by_memory(self) -> None:
        procs = SystemToolset().top_processes(sort_by="memory", limit=5)
        assert 0 < len(procs) <= 5
        memory = [p["memory_mb"] for p in procs]
        assert memory == sorted(memory, reverse=True)

    def test_limit_clamped_to_max(self) -> None:
        tk = SystemToolset(max_processes=3)
        assert len(tk.top_processes(limit=100)) <= 3

    def test_limit_at_least_one(self) -> None:
        assert len(SystemToolset().top_processes(limit=0)) >= 1


class TestNetworkBattery:
    def test_network_io_counters(self) -> None:
        counters = SystemToolset().network_io()
        assert counters["bytes_sent"] >= 0
        assert counters["bytes_recv"] >= 0

    def test_battery_shape_or_none(self) -> None:
        state = SystemToolset().battery()
        if state is not None:
            assert 0.0 <= state["percent"] <= 100.0
            assert isinstance(state["plugged"], bool)
