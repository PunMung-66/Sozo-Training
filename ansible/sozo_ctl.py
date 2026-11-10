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
import base64
import binascii
import hashlib
import json
import re
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
    ("code",    "slurm2_fetch_code.yml",    "Fetch / update code (git, choose branch)"),
    ("dataset", "slurm3_fetch_dataset.yml", "Fetch dataset (dvc pull)"),
    ("submit",  "slurm4_submit_job.yml",    "Run a Slurm job or shell script"),
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


def load_repository(server):
    """Read the repository URL and default branch from the selected inventory host."""
    out = subprocess.run(
        ["ansible-inventory", "-i", INVENTORY, "--host", server],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        sys.exit(f"ansible-inventory failed:\n{out.stderr}")

    variables = json.loads(out.stdout)
    repo_name = variables.get("repo_name")
    repo_url = variables.get("github_repo")
    if not repo_url or not repo_name:
        sys.exit(f"Inventory for '{server}' must define github_repo and repo_name.")

    repo_url = repo_url.replace("{{ repo_name }}", repo_name)
    return repo_url, variables.get("repo_branch", "main")


def load_remote_branches(repo_url):
    """Return branch names from the repository's remote HEAD refs."""
    out = subprocess.run(
        ["git", "ls-remote", "--heads", repo_url],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        sys.exit(f"Could not list branches for {repo_url}:\n{out.stderr}")

    branches = sorted(
        line.split("\t", 1)[1][len("refs/heads/"):]
        for line in out.stdout.splitlines()
        if "\trefs/heads/" in line
    )
    if not branches:
        sys.exit(f"No remote branches found for {repo_url}.")
    return branches


def scan_job_files(server):
    """Find Slurm batch files and shell scripts in the selected server's checkout."""
    cmd = [
        "ansible-playbook", "-i", INVENTORY, "./slurm4_submit_job.yml",
        "--limit", server,
        "--extra-vars", json.dumps({"list_job_files": True}),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        details = "\n".join(part for part in (out.stdout, out.stderr) if part)
        sys.exit(f"Could not scan for Slurm job files:\n{details}")

    match = re.search(r"SOZO_JOB_FILES_B64=([A-Za-z0-9+/=]+)", out.stdout)
    if not match:
        sys.exit("Ansible scan completed but returned no Slurm job file list.")
    try:
        payload = base64.b64decode(match.group(1), validate=True).decode()
        paths = json.loads(payload)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        sys.exit(f"Could not read scanned Slurm job files: {exc}")
    if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
        sys.exit("Ansible returned an invalid list of Slurm job files.")
    return sorted(paths)


def run_playbook(server, key, playbook, repo_branch=None, job_file=None):
    """Run one playbook, stream output, save log named by its sha256. Returns exit code."""
    LOG_DIR.mkdir(exist_ok=True)
    cmd = ["ansible-playbook", "-i", INVENTORY, f"./{playbook}", "--limit", server]
    extra_vars = {}
    if repo_branch is not None:
        extra_vars["repo_branch"] = repo_branch
    if job_file is not None:
        extra_vars["job_file"] = job_file
    if extra_vars:
        cmd.extend(["--extra-vars", json.dumps(extra_vars)])
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

    repo_branch = None
    if any(key in ("setup", "code") for key, _ in picked):
        repo_url, default_branch = load_repository(server)
        branches = load_remote_branches(repo_url)
        print(f"Remote repository has {len(branches)} branches.")
        repo_branch = questionary.select(
            "Select repository branch:",
            choices=branches,
            default=default_branch if default_branch in branches else None,
        ).ask()
        if repo_branch is None:
            print("Cancelled.")
            return

    job_file = None
    if any(key == "submit" for key, _ in picked):
        print("Scanning the remote project for .sbatch and .sh files...")
        job_files = scan_job_files(server)
        if not job_files:
            print("No .sbatch or .sh files found in the remote project.")
            return
        job_file = questionary.select(
            "Select job script to run:",
            choices=[
                questionary.Choice(path, value=path)
                for path in job_files
            ],
        ).ask()
        if job_file is None:
            print("Cancelled.")
            return

    summary = " -> ".join(k for k, _ in picked)
    if job_file:
        summary += f" ({job_file.rsplit('/', 1)[-1]})"
    branch_summary = f" using branch '{repo_branch}'" if repo_branch else ""
    if not questionary.confirm(
        f"Run [{summary}] on {server}{branch_summary}?", default=False
    ).ask():
        print("Cancelled.")
        return

    for key, pb in picked:          # keeps workflow order, stops on first failure
        branch = repo_branch if key in ("setup", "code") else None
        selected_job = job_file if key == "submit" else None
        if run_playbook(server, key, pb, repo_branch=branch, job_file=selected_job) != 0:
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