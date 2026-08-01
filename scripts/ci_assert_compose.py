#!/usr/bin/env python3
"""Assert the security-relevant shape of the rendered Compose model."""
from __future__ import annotations

import json
import sys


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"compose assertion failed: {message}")


def main() -> None:
    model = json.load(sys.stdin)
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
    require((networks[private_name] or {}).get("internal") is True, "football_private must be internal")
    require(not (networks[egress_name] or {}).get("internal", False), "football_egress must provide egress")

    postgres_networks = set(services["postgres"].get("networks", {}))
    require(postgres_networks == {private_name}, "postgres must exist only on football_private")
    require(not services["postgres"].get("ports"), "postgres must not publish a host port")

    for service_name in ("api", "worker"):
        attached = set(services[service_name].get("networks", {}))
        require(private_name in attached, f"{service_name} must reach postgres")
        require(egress_name in attached, f"{service_name} must have egress")

    require(egress_name in services["frontend"].get("networks", {}), "frontend must have egress")
    proxy_networks = set(services["proxy"].get("networks", {}))
    for upstream in ("api", "frontend"):
        upstream_networks = set(services[upstream].get("networks", {}))
        require(proxy_networks & upstream_networks, f"proxy cannot reach {upstream}")

    for service_name in ("postgres", "api", "frontend"):
        require(
            bool(services[service_name].get("healthcheck")),
            f"{service_name} must retain its internal healthcheck",
        )


if __name__ == "__main__":
    main()
