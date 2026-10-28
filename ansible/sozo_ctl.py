#!/usr/bin/env python3
"""
sozo_ctl.py - menu interface for managing servers and running Ansible playbooks.

Run from the ansible directory:
    uv run --with questionary python sozo_ctl.py
or:
    pip install questionary && python3 sozo_ctl.py

Flow: pick a server -> tick actions -> confirm -> output is shown live and saved
as logs/<sha256>.log (filename = hash of content). logs/index.tsv keeps a history.
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import questionary

INVENTORY = "./inventory.yml"
LOG_DIR = Path("logs")
INDEX = LOG_DIR / "index.tsv"

# (key, playbook, description) - order is the normal workflow order
ACTIONS = [
    ("setup",   "slurm1_setup_tool.yml",    "Setup server (uv, DVC, git, clone repo, venv)"),
    ("code",    "slurm2_fetch_code.yml",    "Fetch / update code (git, checkout main)"),
    ("dataset", "slurm3_fetch_dataset.yml", "Fetch dataset (dvc pull)"),
    ("submit",  "slurm4_submit_job.yml",    "Submit Slurm job (sbatch)"),
]


def load_servers(group="server"):
    """Read host names of a group from the ansible inventory."""
    out = subprocess.run(
        ["ansible-inventory", "-i", INVENTORY, "--list"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        sys.exit(f"ansible-inventory failed:\n{out.stderr}")
    data = json.loads(out.stdout)

    def hosts_of(name):
        g = data.get(name, {})
        hosts = list(g.get("hosts", []))
        for child in g.get("children", []):
            hosts += hosts_of(child)
        return hosts

    return sorted(set(hosts_of(group)))


def run_playbook(server, key, playbook):
    """Run one playbook, stream output, save log named by its sha256. Returns exit code."""
    LOG_DIR.mkdir(exist_ok=True)
    cmd = ["ansible-playbook", "-i", INVENTORY, f"./{playbook}", "--limit", server]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"=== {ts} | server={server} | action={key} ===\n", f"$ {' '.join(cmd)}\n\n"]
    print("".join(lines), end="")

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        print(line, end="")
        lines.append(line)
    code = proc.wait()
    lines.append(f"\n[exit code {code}]\n")

    content = "".join(lines).encode()
    digest = hashlib.sha256(content).hexdigest()
    (LOG_DIR / f"{digest}.log").write_bytes(content)
    with INDEX.open("a") as f:
        f.write(f"{ts}\t{server}\t{key}\t{code}\t{digest}\n")

    status = "OK" if code == 0 else "FAILED"
    print(f"\n[{status}] log saved: {LOG_DIR / (digest + '.log')}\n")
    return code


def run_menu():
    servers = load_servers()
    if not servers:
        print("No servers found in group 'server'.")
        return

    server = questionary.select("Select server:", choices=servers).ask()
    if server is None:
        return

    picked = questionary.checkbox(
        "Select actions (space = toggle, enter = confirm):",
        choices=[questionary.Choice(f"{k:8} {d}", value=(k, pb)) for k, pb, d in ACTIONS],
    ).ask()
    if not picked:
        print("Nothing selected.")
        return

    summary = " -> ".join(k for k, _ in picked)
    if not questionary.confirm(f"Run [{summary}] on {server}?", default=False).ask():
        print("Cancelled.")
        return

    for key, pb in picked:          # keeps workflow order, stops on first failure
        if run_playbook(server, key, pb) != 0:
            print(f"Stopped: '{key}' failed.")
            break


def logs_menu():
    if not INDEX.exists():
        print("No logs yet.")
        return
    rows = [l.rstrip("\n").split("\t") for l in INDEX.read_text().splitlines() if l.strip()]
    choices = [
        questionary.Choice(
            f"{ts}  {srv:12} {act:8} exit={code}  {h[:12]}", value=h
        )
        for ts, srv, act, code, h in reversed(rows)
    ]
    h = questionary.select("Select log:", choices=choices).ask()
    if not h:
        return

    path = LOG_DIR / f"{h}.log"
    data = path.read_bytes()
    print(f"\n----- {path} -----")
    print(data.decode(errors="replace"))
    ok = hashlib.sha256(data).hexdigest() == h
    print("[integrity] " + ("hash matches filename" if ok else "MISMATCH - log was modified!"))


def main():
    if not Path(INVENTORY).exists():
        sys.exit(f"Cannot find {INVENTORY} - run this from the ansible directory.")
    while True:
        choice = questionary.select(
            "Sozo Server Manager",
            choices=["Run actions on a server", "View logs", "Quit"],
        ).ask()
        if choice == "Run actions on a server":
            run_menu()
        elif choice == "View logs":
            logs_menu()
        else:
            break


if __name__ == "__main__":
    main()