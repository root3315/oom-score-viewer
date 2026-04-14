#!/usr/bin/env python3
"""
oom-score-viewer - Quick view of process OOM scores on Linux

Reads OOM (Out of Memory) scores from /proc filesystem and displays
them in a sorted, human-readable format.
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Optional


PROC_PATH = Path("/proc")

# ANSI color codes
COLOR_RED = "\033[91m"
COLOR_YELLOW = "\033[93m"
COLOR_GREEN = "\033[92m"
COLOR_RESET = "\033[0m"


def get_color_for_score(score: int) -> str:
    """Return ANSI color code based on OOM score severity."""
    if score >= 700:
        return COLOR_RED
    elif score >= 300:
        return COLOR_YELLOW
    else:
        return COLOR_GREEN


def supports_color() -> bool:
    """Check if the terminal supports color output."""
    if not hasattr(sys.stdout, "isatty"):
        return False
    if not sys.stdout.isatty():
        return False
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return True


def colorize_score(score: int, use_color: bool = True) -> str:
    """Return score string with appropriate color if enabled."""
    if not use_color:
        return str(score)
    color = get_color_for_score(score)
    return f"{color}{score}{COLOR_RESET}"


def get_process_info(pid: int) -> Optional[Tuple[str, int, int, int]]:
    """
    Get process name, OOM score, OOM score adj, and RSS for a given PID.

    Returns tuple of (name, oom_score, oom_score_adj, rss_kb) or None if
    process no longer exists or info unavailable.
    """
    proc_dir = PROC_PATH / str(pid)

    if not proc_dir.exists():
        return None

    try:
        name = "unknown"
        comm_path = proc_dir / "comm"
        if comm_path.exists():
            name = comm_path.read_text().strip()

        oom_score = 0
        oom_score_path = proc_dir / "oom_score"
        if oom_score_path.exists():
            oom_score = int(oom_score_path.read_text().strip())

        oom_score_adj = 0
        oom_score_adj_path = proc_dir / "oom_score_adj"
        if oom_score_adj_path.exists():
            oom_score_adj = int(oom_score_adj_path.read_text().strip())

        rss_kb = 0
        statm_path = proc_dir / "statm"
        if statm_path.exists():
            statm_data = statm_path.read_text().strip().split()
            if len(statm_data) >= 2:
                rss_pages = int(statm_data[1])
                page_size_kb = os.sysconf("SC_PAGE_SIZE") // 1024
                rss_kb = rss_pages * page_size_kb

        return (name, oom_score, oom_score_adj, rss_kb)

    except (PermissionError, ProcessLookupError, ValueError, FileNotFoundError):
        return None


def get_all_processes() -> List[Tuple[int, str, int, int, int]]:
    """
    Scan /proc and collect OOM info for all processes.

    Returns list of tuples: (pid, name, oom_score, oom_score_adj, rss_kb)
    """
    processes = []

    if not PROC_PATH.exists():
        print(f"Error: {PROC_PATH} does not exist", file=sys.stderr)
        return processes

    for entry in PROC_PATH.iterdir():
        if not entry.name.isdigit():
            continue

        pid = int(entry.name)
        info = get_process_info(pid)

        if info is not None:
            name, oom_score, oom_score_adj, rss_kb = info
            processes.append((pid, name, oom_score, oom_score_adj, rss_kb))

    return processes


def format_size(size_kb: int) -> str:
    """Format memory size in human-readable format."""
    if size_kb >= 1024 * 1024:
        return f"{size_kb / (1024 * 1024):.1f}G"
    elif size_kb >= 1024:
        return f"{size_kb / 1024:.1f}M"
    else:
        return f"{size_kb}K"


def processes_to_json(
    processes: List[Tuple[int, str, int, int, int]],
) -> str:
    """Convert a list of processes to a JSON string."""
    entries = []
    for pid, name, oom_score, oom_score_adj, rss_kb in processes:
        entries.append({
            "pid": pid,
            "name": name,
            "oom_score": oom_score,
            "oom_score_adj": oom_score_adj,
            "rss_kb": rss_kb,
        })
    return json.dumps({"processes": entries}, indent=2)


def display_processes(
    processes: List[Tuple[int, str, int, int, int]],
    limit: int = 0,
    filter_name: Optional[str] = None,
    show_all: bool = False,
    as_json: bool = False,
    sort_by: str = "oom",
) -> None:
    """Display process OOM information in a formatted table or JSON."""

    filtered = processes

    if filter_name:
        filtered = [p for p in processes if filter_name.lower() in p[1].lower()]

    if not show_all:
        filtered = [p for p in filtered if p[3] != -1000]

    if sort_by == "rss":
        sorted_processes = sorted(filtered, key=lambda x: x[4], reverse=True)
    else:
        sorted_processes = sorted(filtered, key=lambda x: x[2], reverse=True)

    if limit > 0:
        sorted_processes = sorted_processes[:limit]

    if as_json:
        print(processes_to_json(sorted_processes))
        return

    if not sorted_processes:
        print("No processes found matching criteria.")
        return

    use_color = supports_color()

    sort_label = "RSS" if sort_by == "rss" else "OOM"
    print(f"{'PID':>8}  {'NAME':<25}  {'OOM':>6}  {'ADJ':>6}  {'RSS':>10}")
    print("-" * 62)

    for pid, name, oom_score, oom_score_adj, rss_kb in sorted_processes:
        name_display = name[:24] if len(name) > 24 else name
        rss_display = format_size(rss_kb)

        adj_display = str(oom_score_adj)
        if oom_score_adj == -1000:
            adj_display = "LOCKED"

        score_display = colorize_score(oom_score, use_color)
        print(f"{pid:>8}  {name_display:<25}  {score_display:>6}  {adj_display:>6}  {rss_display:>10}")

    print("-" * 62)
    print(f"Total processes shown: {len(sorted_processes)}")
    print(f"Sorted by: {sort_label} (descending)")

    if not show_all:
        print("(Use --all to include processes with oom_score_adj=-1000)")


def display_single_process(pid: int, as_json: bool = False) -> None:
    """Display detailed OOM info for a single process."""
    info = get_process_info(pid)

    if info is None:
        print(f"Error: Cannot read info for PID {pid}", file=sys.stderr)
        sys.exit(1)

    name, oom_score, oom_score_adj, rss_kb = info

    if as_json:
        data = {
            "pid": pid,
            "name": name,
            "oom_score": oom_score,
            "oom_score_adj": oom_score_adj,
            "rss_kb": rss_kb,
        }

        if oom_score_adj == -1000:
            data["status"] = "OOM killer disabled for this process"
        elif oom_score_adj < 0:
            data["status"] = "Less likely to be killed"
        elif oom_score_adj > 0:
            data["status"] = "More likely to be killed"
        else:
            data["status"] = "Default OOM behavior"

        cmdline_path = PROC_PATH / str(pid) / "cmdline"
        if cmdline_path.exists():
            try:
                cmdline = cmdline_path.read_text().replace("\x00", " ").strip()
                if cmdline:
                    data["command"] = cmdline[:200]
            except (PermissionError, FileNotFoundError):
                pass

        print(json.dumps(data, indent=2))
        return

    use_color = supports_color()

    print(f"PID:           {pid}")
    print(f"Name:          {name}")

    score_display = colorize_score(oom_score, use_color)
    print(f"OOM Score:     {score_display}")
    print(f"OOM Score Adj: {oom_score_adj}")

    if oom_score_adj == -1000:
        print("Status:        OOM killer disabled for this process")
    elif oom_score_adj < 0:
        print("Status:        Less likely to be killed")
    elif oom_score_adj > 0:
        print("Status:        More likely to be killed")
    else:
        print("Status:        Default OOM behavior")

    print(f"RSS Memory:    {format_size(rss_kb)}")

    cmdline_path = PROC_PATH / str(pid) / "cmdline"
    if cmdline_path.exists():
        try:
            cmdline = cmdline_path.read_text().replace("\x00", " ").strip()
            if cmdline:
                print(f"Command:       {cmdline[:80]}")
        except (PermissionError, FileNotFoundError):
            pass


def main():
    parser = argparse.ArgumentParser(
        description="View OOM (Out of Memory) scores for Linux processes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Show all processes sorted by OOM score
  %(prog)s -n 20              Show top 20 processes by OOM score
  %(prog)s -p 1234            Show detailed info for PID 1234
  %(prog)s -f nginx           Filter processes matching 'nginx'
  %(prog)s --all              Include processes with OOM killer disabled
  %(prog)s --json             Output as JSON for scripting
  %(prog)s --sort rss         Sort by memory usage (RSS) instead of OOM score
        """
    )

    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=0,
        help="Limit number of processes shown (default: all)"
    )

    parser.add_argument(
        "-p", "--pid",
        type=int,
        help="Show detailed info for specific PID"
    )

    parser.add_argument(
        "-f", "--filter",
        type=str,
        dest="filter_name",
        help="Filter processes by name substring"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Include processes with oom_score_adj=-1000 (OOM killer disabled)"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output results as JSON"
    )

    parser.add_argument(
        "--sort",
        choices=["oom", "rss"],
        default="oom",
        help="Sort by OOM score (default) or RSS memory usage"
    )

    args = parser.parse_args()

    if args.pid is not None:
        display_single_process(args.pid, as_json=args.as_json)
    else:
        processes = get_all_processes()

        if not processes:
            print("Error: No processes found or unable to read /proc", file=sys.stderr)
            sys.exit(1)

        display_processes(
            processes,
            limit=args.limit,
            filter_name=args.filter_name,
            show_all=args.all,
            as_json=args.as_json,
            sort_by=args.sort,
        )


if __name__ == "__main__":
    main()
