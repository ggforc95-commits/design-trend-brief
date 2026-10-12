"""Install weekly macOS launch agent; run from the repository with Python 3.9+."""
import json
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABEL = "com.ggforc.design-trend-brief"

def run():
    config = Path.home() / "Library/Application Support/DesignTrendBrief/config.json"
    if not config.exists():
        raise SystemExit("Missing local config.json. Complete API configuration first.")
    values = json.loads(config.read_text())
    if not isinstance(values, dict) or not all(isinstance(v, str) for v in values.values()):
        raise SystemExit("Config values must be strings.")
    env = os.environ.copy()
    env.update(values)
    # Inherit local/VPN networking. Keep credentials out of the plist and logs.
    subprocess.run([sys.executable, str(ROOT / "send_brief.py")],
                   cwd=ROOT, env=env, check=True)

def install():
    if sys.platform != "darwin":
        raise SystemExit("Run this installer on your Mac.")
    config_dir = Path.home() / "Library/Application Support/DesignTrendBrief"
    config_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(config_dir, 0o700)
    config = config_dir / "config.json"
    if not config.exists():
        config.write_text(json.dumps({
            "OPENAI_API_KEY": "",
            "OPENAI_MODEL": "",
            "WECOM_WEBHOOK_URL": ""
        }, indent=2) + "\n")
    os.chmod(config, 0o600)
    logs = config_dir / "logs"
    logs.mkdir(exist_ok=True)
    agents = Path.home() / "Library/LaunchAgents"
    agents.mkdir(parents=True, exist_ok=True)
    plist = agents / (LABEL + ".plist")
    job = {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, str(Path(__file__).resolve()), "run"],
        "WorkingDirectory": str(ROOT),
        "StartCalendarInterval": {"Weekday": 1, "Hour": 9, "Minute": 0},
        "StandardOutPath": str(logs / "stdout.log"),
        "StandardErrorPath": str(logs / "stderr.log"),
        "ProcessType": "Background",
    }
    with plist.open("wb") as output:
        plistlib.dump(job, output)
    domain = "gui/" + str(os.getuid())
    subprocess.run(["launchctl", "bootout", domain + "/" + LABEL],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["launchctl", "bootstrap", domain, str(plist)], check=True)
    print("Weekly Monday 09:00 job installed, using the Mac's local timezone.")
    print("Before the first run, complete the private config at: " + str(config))
    print("The Mac must be logged in and able to reach the company API and WeCom.")
    print("No message has been sent by installation.")

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"install", "run"}:
        raise SystemExit("Usage: python3 macos/schedule.py install|run")
    if sys.argv[1] == "install":
        install()
    else:
        run()
