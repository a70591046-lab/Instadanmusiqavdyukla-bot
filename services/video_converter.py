import asyncio
import os
import subprocess
import uuid
from pathlib import Path
from config import DOWNLOADS_DIR

async def convert_to_video_note(input_path: str | Path) -> Path:
    """
    Videoni Telegram Dumaloq Video (Video Note) formatiga o'tkazadi:
    - 1:1 kvadrat qilib kesish (crop)
    - 480x480 o'lcham
    - Maksimal 60 soniya
    - H.264 video va AAC audio
    """
    input_path = Path(input_path)
    output_filename = f"note_{uuid.uuid4().hex[:8]}.mp4"
    output_path = DOWNLOADS_DIR / output_filename

    # FFmpeg buyrug'i
    # crop='min(iw,ih)':'min(iw,ih)' - markazdan eng kichik tomon bo'yicha kvadrat kesadi
    # scale=480:480 - 480x480 o'lchamga keltiradi
    # -t 60 - video note maksimal 60 soniya bo'lishi shart
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-t", "60",
        "-vf", "crop=min(iw\\,ih):min(iw\\,ih),scale=480:480",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "26",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-movflags", "+faststart",
        str(output_path)
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode(errors="replace")
        raise RuntimeError(f"FFmpeg xatoligi: {error_msg[-300:]}")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("Dumaloq video yaratilmadi.")

    return output_path
