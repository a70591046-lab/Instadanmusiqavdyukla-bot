import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! Iltimos .env faylini tekshiring.")

DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True, parents=True)

import sys
# ByeDPI / Proxy sozlamasi: Windowsda lokal ByeDPI, Linux/Serverda esa to'g'ridan-to'g'ri (None)
PROXY = os.getenv("PROXY", "").strip() or None
if not PROXY and sys.platform == "win32":
    PROXY = "socks5://127.0.0.1:10808"
