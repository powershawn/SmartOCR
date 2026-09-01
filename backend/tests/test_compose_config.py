import json
import os
import subprocess
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"


def render_compose_config(frontend_port: Optional[str]) -> dict:
    env = os.environ.copy()
    env.pop("COMPOSE_FILE", None)
    if frontend_port is None:
        env.pop("FRONTEND_PORT", None)
    else:
        env["FRONTEND_PORT"] = frontend_port
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(COMPOSE_FILE),
            "config",
            "--format",
            "json",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def test_frontend_port_can_be_overridden_for_deployment() -> None:
    config = render_compose_config("80")
    publications = config["services"]["frontend"]["ports"]
    assert any(
        str(publication["published"]) == "80"
        and str(publication["target"]) == "80"
        and publication["host_ip"] == "0.0.0.0"
        for publication in publications
    )


def test_frontend_port_defaults_to_8080() -> None:
    config = render_compose_config(None)
    publications = config["services"]["frontend"]["ports"]
    assert any(
        str(publication["published"]) == "8080"
        and str(publication["target"]) == "80"
        and publication["host_ip"] == "0.0.0.0"
        for publication in publications
    )
