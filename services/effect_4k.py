import asyncio
import uuid
from pathlib import Path
from config import DOWNLOADS_DIR

async def apply_4k_effect(input_path: str | Path) -> Path:
    """
    Videoga 4K / HDR tiniqlashtirish va ranglarni boyitish effektini beradi:
    - Unsharp filter (aniqlikni oshirish)
    - Contrast va saturation (to'yinganlik) kuchaytirish
    - 1080p / yuqori sifatga masshtablash
    """
    input_path = Path(input_path)
    output_filename = f"4k_{uuid.uuid4().hex[:8]}.mp4"
    output_path = DOWNLOADS_DIR / output_filename

    # FFmpeg 4K / HDR effekti filtri
    # unsharp - qirralarni tiniqlashtirish
    # eq - kontrast va rang to'yinganligini oshirish
    vf_filter = "unsharp=5:5:1.3:5:5:0.0,eq=contrast=1.12:brightness=0.02:saturation=1.25"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
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
        raise RuntimeError(f"FFmpeg 4K xatosi: {error_msg[-300:]}")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("4K video yaratilmadi.")

    return output_path
