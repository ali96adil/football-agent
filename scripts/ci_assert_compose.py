#!/usr/bin/env python3
"""Assert the security-relevant shape of the rendered Compose model."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def load_compose_model() -> dict:
    raw_model = "" if sys.stdin.isatty() else sys.stdin.read()
    if not raw_model.strip():
        result = subprocess.run(
            [
                "docker",
                "compose",
                "--env-file",
                str(REPOSITORY_ROOT / ".env.ci"),
                "config",
                "--format",
                "json",
            ],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            if result.stderr:
                print(result.stderr.rstrip(), file=sys.stderr)
            raise SystemExit(result.returncode)
        raw_model = result.stdout

    try:
        return json.loads(raw_model)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"compose assertion failed: invalid Compose JSON: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"compose assertion failed: {message}")


def assert_compose_model(model: dict) -> None:
    services = model["services"]
    networks = model["networks"]

    published = sorted(name for name, service in services.items() if service.get("ports"))
    require(published == ["proxy"], f"only proxy may publish ports, got {published}")

    private_name = next(
        name for name in networks if name == "football_private" or name.endswith("_football_private")
    )
    egress_name = next(
        name for name in networks if name == "football_egress" or name.endswith("_football_egress")
    )
    ingress_name = next(
        name for name in networks if name == "football_ingress" or name.endswith("_football_ingress")
    )
    require((networks[private_name] or {}).get("internal") is True, "football_private must be internal")
    require(not (networks[egress_name] or {}).get("internal", False), "football_egress must provide egress")
    require(
        not (networks[ingress_name] or {}).get("internal", False),
        "football_ingress must permit published proxy ports",
    )

    postgres_networks = set(services["postgres"].get("networks", {}))
    require(postgres_networks == {private_name}, "postgres must exist only on football_private")
    require(not services["postgres"].get("ports"), "postgres must not publish a host port")

    for service_name in ("api", "worker"):
        attached = set(services[service_name].get("networks", {}))
        require(private_name in attached, f"{service_name} must reach postgres")
        require(egress_name in attached, f"{service_name} must have egress")

    require(egress_name in services["frontend"].get("networks", {}), "frontend must have egress")
    proxy_networks = set(services["proxy"].get("networks", {}))
    require(ingress_name in proxy_networks, "proxy must join football_ingress")
    require(
        services["worker"].get("command") == ["python", "-m", "scripts.worker"],
        "worker must run as a module so /app remains on the Python import path",
    )
    for upstream in ("api", "frontend"):
        upstream_networks = set(services[upstream].get("networks", {}))
        require(proxy_networks & upstream_networks, f"proxy cannot reach {upstream}")

    for service_name in ("postgres", "api", "frontend"):
        require(
            bool(services[service_name].get("healthcheck")),
            f"{service_name} must retain its internal healthcheck",
        )


def main() -> None:
    assert_compose_model(load_compose_model())


if __name__ == "__main__":
    main()
