# SystemToolset

[README](https://github.com/wachawo/pydantic-ai-toolbox/blob/main/README.md)

Read-only view of the host machine: CPU, memory, disks, uptime, load averages,
heaviest processes, network counters, and battery. Backed by psutil — install
the `system` extra. Nothing in this toolset can mutate the system, signal
processes, or read file contents, which makes it safe to hand to any agent
that needs to answer "how is this machine doing?".

```bash
pip install "pydantic-ai-toolbox[system]"
```

```python
from pydantic_ai_toolbox import SystemToolset

sys_info = SystemToolset(
    max_processes=50,   # hard cap for top_processes, wins over the per-call limit
)
```

## Tools

| Tool | Returns |
|---|---|
| `cpu_info()` | physical/logical cores, utilisation percent, frequency MHz |
| `memory_info()` | RAM/swap totals (GB), available, used percent |
| `disk_usage(path="/")` | total/free GB and `used_percent` for the filesystem containing `path` |
| `disk_partitions()` | device, mountpoint, fstype per mounted partition |
| `uptime()` | boot time (ISO-8601 UTC), uptime in hours |
| `load_avg()` | 1/5/15-minute load averages |
| `top_processes(sort_by="cpu"\|"memory", limit=10)` | pid, name, cpu percent, RSS MB — clamped to `max_processes` |
| `network_io()` | cumulative bytes/packets sent and received since boot |
| `battery()` | percent and plugged flag, or `None` without a battery |

## Notes

- `disk_usage.used_percent` is computed as `(total - free) / total` rather than
  psutil's `percent`: on macOS the latter describes the sealed APFS snapshot
  volume and routinely misleads agents into reporting a nearly-empty disk.
- `top_processes` skips processes that disappear or deny access mid-iteration
  instead of failing the whole call.

## Example

```python
from pydantic_ai import Agent
from pydantic_ai_toolbox import SystemToolset

agent = Agent(
    "openai:gpt-4o-mini",
    toolsets=[SystemToolset()],
    system_prompt="You are a sysadmin assistant. Use tools for real data.",
)
result = agent.run_sync("How much free disk space do I have?")
print(result.output)
```
