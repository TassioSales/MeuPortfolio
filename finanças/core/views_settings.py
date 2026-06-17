"""Settings view: configure API tokens and integrations."""
import os
import sys
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

import core.market_data as market_data


def _find_env_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / ".env"
    from django.conf import settings
    return Path(settings.BASE_DIR) / ".env"


def _read_env() -> dict:
    env_path = _find_env_path()
    result = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                result[key.strip()] = val.strip()
    return result


def _write_env(env: dict) -> None:
    env_path = _find_env_path()
    lines = [f"{k}={v}" for k, v in env.items()]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@login_required
def settings_view(request):
    env = _read_env()
    current_token = env.get("BRAPI_TOKEN", "") or os.environ.get("BRAPI_TOKEN", "")
    token_active = bool(current_token)

    if request.method == "POST":
        new_token = request.POST.get("brapi_token", "").strip()
        env["BRAPI_TOKEN"] = new_token
        try:
            _write_env(env)
            os.environ["BRAPI_TOKEN"] = new_token
            market_data._BRAPI_TOKEN = new_token
            if new_token:
                messages.success(request, "Token BRAPI salvo e ativado com sucesso!")
            else:
                messages.info(request, "Token removido. Usando Yahoo Finance como fonte de dados.")
        except Exception as e:
            messages.error(request, f"Erro ao salvar token: {e}")
        return redirect("settings")

    context = {
        "current_token": current_token,
        "token_active": token_active,
        "token_masked": (current_token[:4] + "••••••••" + current_token[-4:]) if len(current_token) > 8 else current_token,
        "env_path": str(_find_env_path()),
    }
    return render(request, "core/settings.html", context)
