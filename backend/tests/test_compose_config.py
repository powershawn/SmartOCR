import json
import os
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_frontend_port_can_be_overridden_for_deployment() -> None:
    env = os.environ.copy()
    env["FRONTEND_PORT"] = "80"
    result = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    config = json.loads(result.stdout)
    publications = config["services"]["frontend"]["ports"]
    assert any(
        str(publication["published"]) == "80"
        and str(publication["target"]) == "80"
        and publication["host_ip"] == "0.0.0.0"
        for publication in publications
    )
