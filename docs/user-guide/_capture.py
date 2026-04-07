"""Helper to capture authenticated screenshots for the user-guide.

Usage: .venv/bin/python docs/user-guide/_capture.py shots.json
shots.json: list of {"url": "...", "out": "filename.png", "wait": "selector_or_ms_optional", "full_page": false}
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.auth import get_user_model, login  # noqa: E402
from django.contrib.sessions.backends.db import SessionStore  # noqa: E402
from django.http import HttpRequest  # noqa: E402

# Disable debug toolbar for clean shots
settings.INTERNAL_IPS = []

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()
if not user:
    raise SystemExit("No superuser found")

# Create a session for the admin user
request = HttpRequest()
request.session = SessionStore()
login(request, user, backend="django.contrib.auth.backends.ModelBackend")
request.session.save()
session_key = request.session.session_key

cfg_path = sys.argv[1]
with open(cfg_path) as f:
    shots = json.load(f)

out_dir = os.path.join(os.getcwd(), "docs/user-guide/screenshots")
os.makedirs(out_dir, exist_ok=True)

from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1400, "height": 900}, device_scale_factor=2)
    context.add_cookies(
        [
            {
                "name": "sessionid",
                "value": session_key,
                "domain": "localhost",
                "path": "/",
                "httpOnly": True,
            }
        ]
    )
    page = context.new_page()
    for shot in shots:
        url = shot["url"]
        out = os.path.join(out_dir, shot["out"])
        full_page = shot.get("full_page", False)
        print(f"-> {url} -> {out}")
        page.goto(f"http://localhost:8000{url}", wait_until="networkidle", timeout=30000)
        wait = shot.get("wait")
        if isinstance(wait, int):
            page.wait_for_timeout(wait)
        elif isinstance(wait, str):
            try:
                page.wait_for_selector(wait, timeout=5000)
            except Exception as e:
                print("  wait failed:", e)
        # Hide debug toolbar if it slipped through
        page.evaluate("(() => { const t=document.getElementById('djDebug'); if(t) t.remove(); })()")
        page.screenshot(path=out, full_page=full_page)
    browser.close()
print("done")
