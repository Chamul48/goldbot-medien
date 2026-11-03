"""Benachrichtigungen: Windows-Hinweis (Toast) und optional Telegram.

Telegram (optional): Bot bei @BotFather anlegen, Token als Umgebungsvariable
GOLDBOT_TELEGRAM_TOKEN setzen und die eigene Chat-ID in config.yaml unter
notify.telegram_chat_id eintragen. Der Token gehört nicht in die config.
"""

from __future__ import annotations

import base64
import logging
import os
import subprocess
import sys
from typing import Any

import requests

log = logging.getLogger(__name__)

# App-ID von Windows PowerShell – damit zeigt Windows den Hinweis ohne Installation an
_PS_APP_ID = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"

_TOAST_SCRIPT = r"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$x = $t.GetElementsByTagName('text')
$x.Item(0).AppendChild($t.CreateTextNode($env:GOLDBOT_TOAST_TITLE)) | Out-Null
$x.Item(1).AppendChild($t.CreateTextNode($env:GOLDBOT_TOAST_BODY)) | Out-Null
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('%s').Show([Windows.UI.Notifications.ToastNotification]::new($t))
""" % _PS_APP_ID


def windows_toast(title: str, body: str) -> bool:
    if sys.platform != "win32":
        return False
    encoded = base64.b64encode(_TOAST_SCRIPT.encode("utf-16-le")).decode()
    env = {**os.environ, "GOLDBOT_TOAST_TITLE": title[:120], "GOLDBOT_TOAST_BODY": body[:250]}
    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            env=env, timeout=20, capture_output=True, check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("Windows-Hinweis fehlgeschlagen (%s).", exc.__class__.__name__)
        return False


def telegram(text: str, chat_id: str, token: str | None = None) -> bool:
    token = token or os.environ.get("GOLDBOT_TELEGRAM_TOKEN")
    if not (token and chat_id):
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": True},
            timeout=20,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        log.warning("Telegram-Nachricht fehlgeschlagen (%s).", exc.__class__.__name__)
        return False


def send(cfg: dict[str, Any], title: str, body: str, details: str = "") -> list[str]:
    """Schickt eine Nachricht über alle eingeschalteten Kanäle. Gibt die genutzten Kanäle zurück."""
    ncfg = cfg.get("notify", {}) or {}
    used = []
    if ncfg.get("windows", True) and windows_toast(title, body):
        used.append("windows")
    chat_id = str(ncfg.get("telegram_chat_id") or "")
    if chat_id and telegram(f"{title}\n\n{details or body}", chat_id):
        used.append("telegram")
    return used
