import logging
import socket
import subprocess
import sys
import time
from pathlib import Path
from config import BASE_DIR

logger = logging.getLogger(__name__)

CIADPI_EXE = BASE_DIR / "byedpi" / "ciadpi.exe"
_dpi_process = None

def is_port_in_use(port: int = 10808) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', port)) == 0
    except Exception:
        return False

def start_dpi_service(port: int = 10808) -> bool:
    """
    Instagram va YouTube blokirovkalarini (ConnectionResetError 10054 / TSPU DPI)
    avtomatik aylanib o'tish uchun lokal ByeDPI SOCKS5 xizmatini ishga tushiradi.
    """
    global _dpi_process

    if is_port_in_use(port):
        logger.info(f"ByeDPI SOCKS5 xizmati allaqachon 127.0.0.1:{port} portida ishlamoqda.")
        return True

    if not CIADPI_EXE.exists():
        logger.warning(f"ciadpi.exe topilmadi: {CIADPI_EXE}")
        return False

    cmd = [
        str(CIADPI_EXE),
        "-i", "127.0.0.1",
        "-p", str(port),
        "--split", "1",
        "--disorder", "3+s",
        "--auto=torst",
        "--tlsrec", "1+s"
    ]

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW

    try:
        _dpi_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags
        )
        # Port ochilishini 1-2 soniya kutish
        for _ in range(10):
            time.sleep(0.2)
            if is_port_in_use(port):
                logger.info(f"ByeDPI xizmati muvaffaqiyatli ishga tushdi (127.0.0.1:{port}).")
                return True
        logger.warning("ByeDPI porti o'z vaqtida ochilmadi, ammo jarayon davom etmoqda.")
        return True
    except Exception as e:
        logger.error(f"ByeDPI xizmatini yoqishda xatolik: {e}")
        return False

def stop_dpi_service():
    global _dpi_process
    if _dpi_process:
        try:
            _dpi_process.terminate()
            logger.info("ByeDPI xizmati to'xtatildi.")
        except Exception:
            pass
        _dpi_process = None
