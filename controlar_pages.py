#!/usr/bin/env python3
"""Evita que la integración Git de Pages publique la raíz del repositorio."""

import json
import os
from urllib.request import Request, urlopen


PROJECT = "olbsanpedro"
OWNER = "jotapeflorez"
REPOSITORY = "olb"


def main():
    account = os.environ["CLOUDFLARE_ACCOUNT_ID"].strip()
    token = os.environ["CLOUDFLARE_API_TOKEN"].strip()
    if not account or not token or "\r" in token or "\n" in token:
        raise RuntimeError("La credencial de Pages contiene caracteres de control o está vacía")
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/pages/projects/{PROJECT}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def consultar(data=None):
        method = "PATCH" if data is not None else "GET"
        request = Request(url, data=data, headers=headers, method=method)
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
        if payload.get("success") is not True or not isinstance(payload.get("result"), dict):
            raise RuntimeError("Cloudflare no confirmó la configuración del proyecto")
        return payload["result"]

    project = consultar()
    source = project.get("source") or {}
    config = source.get("config") or {}
    if (
        project.get("name") != PROJECT
        or source.get("type") != "github"
        or config.get("owner") != OWNER
        or config.get("repo_name") != REPOSITORY
        or config.get("production_branch") != "main"
    ):
        raise RuntimeError("El proyecto Pages no corresponde al repositorio OLB esperado")

    if config.get("production_deployments_enabled") is not False or config.get("preview_deployment_setting") != "none":
        change = {
            "source": {
                "type": "github",
                "config": {"production_deployments_enabled": False, "preview_deployment_setting": "none"},
            }
        }
        consultar(json.dumps(change).encode("utf-8"))

    current = consultar().get("source", {}).get("config", {})
    if current.get("production_deployments_enabled") is not False or current.get("preview_deployment_setting") != "none":
        raise RuntimeError("Cloudflare todavía permite publicar automáticamente desde Git")
    print("Publicaciones automáticas de Git desactivadas; Pages queda bajo el despliegue diario validado")


if __name__ == "__main__":
    main()
