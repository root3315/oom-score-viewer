# oom-score-viewer

Quick view of process OOM scores on Linux. Because sometimes you need to know which process the OOM killer will murder first when memory runs out.

## What is OOM Score?

Linux has this thing called the OOM (Out of Memory) killer. When the system runs out of memory, it needs to kill something to keep going. The OOM score determines which process gets the axe first.

- **Higher score** = more likely to be killed
- **Lower score** = less likely to be killed
- **-1000** = OOM killer is disabled for this process (it's protected)
- **1000** = basically a death sentence when memory runs out

## Installation

No fancy setup needed:

```bash
chmod +x oom_score_viewer.py
./oom_score_viewer.py
```

Or run it with Python directly:

```bash
python3 oom_score_viewer.py
```

## Usage

Show all processes sorted by OOM score:

```bash
./oom_score_viewer.py
```

Show only the top 15 processes:

```bash
./oom_score_viewer.py -n 15
```

Sort by memory usage (RSS) instead of OOM score:

```bash
./oom_score_viewer.py --sort rss
./oom_score_viewer.py --sort rss -n 10
```

Get detailed info for a specific PID:

```bash
./oom_score_viewer.py -p 1234
```

Filter by process name:

```bash
./oom_score_viewer.py -f nginx
./oom_score_viewer.py -f python
```

Include processes with OOM killer disabled (normally hidden):

```bash
./oom_score_viewer.py --all
```

Output as JSON for scripting and automation:

```bash
./oom_score_viewer.py --json
./oom_score_viewer.py -p 1234 --json
./oom_score_viewer.py -f nginx --json | jq '.processes[].pid'
```

## Output

```
     PID  NAME                        OOM    ADJ         RSS
--------------------------------------------------------------
    1234  java                       1523      0       2.1G
    5678  chrome                     1204      0     850.5M
     901  node                        892      0     420.3M
--------------------------------------------------------------
Total processes shown: 3
Sorted by: OOM (descending)
```

Columns:
- **PID** - Process ID
- **NAME** - Process name (from /proc/[pid]/comm)
- **OOM** - Current OOM score (0-1000 typically)
- **ADJ** - OOM score adjustment (-1000 to 1000)
- **RSS** - Resident Set Size (actual memory used)

## Sorting

- **`--sort oom`** (default) - Sort by OOM score, highest first
- **`--sort rss`** - Sort by memory usage (RSS), highest first

## Color Output

OOM scores are color-coded for quick visual assessment:

- **Red** - High score (≥700): Process is very likely to be killed
- **Yellow** - Medium score (300-699): Moderate risk
- **Green** - Low score (<300): Low risk

Color output is automatic when running in a supported terminal. Set `NO_COLOR=1` to disable colors.

## Why I Made This

I was debugging a server that kept getting OOM killed and got tired of running `cat /proc/*/oom_score` in a loop. This script does that but actually shows you something useful.

## Requirements

- Python 3.6+
- Linux (obviously, since we're reading /proc)
- Root/sudo helps but not required (you'll see what you have permission to read)

## Notes

- Processes with `oom_score_adj = -1000` are hidden by default since they're protected from OOM killer
- You might see fewer processes without sudo due to permission restrictions
- OOM scores change dynamically based on memory usage

## License

Do whatever you want with it.
