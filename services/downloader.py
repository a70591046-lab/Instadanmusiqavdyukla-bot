import asyncio
import os
import re
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
import aiohttp
import yt_dlp

from config import DOWNLOADS_DIR, BASE_DIR, PROXY

class DownloaderService:
    @staticmethod
    def is_url(text: str) -> bool:
        url_regex = re.compile(
            r'^(?:http|ftp)s?://' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' # domain...
            r'localhost|' # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
            r'(?::\d+)?' # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_regex.match(text.strip()))

    @staticmethod
    def extract_urls(text: str) -> List[str]:
        return re.findall(r'(https?://[^\s]+)', text)

    @classmethod
    async def download_tiktok_tikwm(cls, url: str) -> Optional[Dict[str, Any]]:
        """TikWM API orqali TikTok videosini tezgina va suv belgisiz yuklash"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://www.tikwm.com/api/", data={"url": url}, timeout=15) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    if data.get("code") == 0 and "data" in data:
                        info = data["data"]
                        video_url = info.get("play")
                        music_url = info.get("music")
                        title = info.get("title", "TikTok Video")

                        if not video_url:
                            return None

                        # Videoni yuklab olish
                        file_id = uuid.uuid4().hex[:8]
                        video_path = DOWNLOADS_DIR / f"tiktok_{file_id}.mp4"

                        async with session.get(video_url) as v_resp:
                            if v_resp.status == 200:
                                with open(video_path, "wb") as f:
                                    f.write(await v_resp.read())

                        # Agar musiqa bor bo'lsa
                        music_path = None
                        if music_url:
                            music_path = DOWNLOADS_DIR / f"tiktok_{file_id}.mp3"
                            async with session.get(music_url) as m_resp:
                                if m_resp.status == 200:
                                    with open(music_path, "wb") as f:
                                        f.write(await m_resp.read())

                        return {
                            "title": title,
                            "video_path": video_path,
                            "audio_path": music_path,
                            "duration": info.get("duration", 0),
                            "source": "tiktok"
                        }
        except Exception as e:
            print(f"TikWM xatosi: {e}")
            return None

    @classmethod
    async def download_instagram_parth(cls, url: str) -> Optional[Dict[str, Any]]:
        """parth_dl orqali Instagram reel/post yuklab olish"""
        def _download():
            try:
                from parth_dl import InstagramDownloader
                downloader = InstagramDownloader(quiet=True, overwrite=True)
                file_id = uuid.uuid4().hex[:8]
                out_file = DOWNLOADS_DIR / f"insta_{file_id}.mp4"
                res = downloader.download(url, output_path=str(out_file))
                if isinstance(res, list) and res:
                    return Path(res[0])
                elif res and Path(res).exists():
                    return Path(res)
                elif out_file.exists() and out_file.stat().st_size > 0:
                    return out_file
            except Exception as e:
                print(f"parth_dl xatosi: {e}")
            return None

        video_path = await asyncio.to_thread(_download)
        if video_path and video_path.exists():
            return {
                "title": "Instagram Video",
                "video_path": video_path,
                "audio_path": None,
                "duration": 0,
                "source": "instagram"
            }
        return None

    @classmethod
    async def download_ytdlp(cls, url: str, is_audio: bool = False) -> Dict[str, Any]:
        """yt-dlp orqali umumiy yuklash (YouTube, Instagram, TikTok, Facebook va h.k.)"""
        def _download():
            file_id = uuid.uuid4().hex[:8]
            ext = "mp3" if is_audio else "mp4"
            out_template = str(DOWNLOADS_DIR / f"media_{file_id}.%(ext)s")

            ydl_opts: Dict[str, Any] = {
                "outtmpl": out_template,
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "nocheckcertificate": True,
                "socket_timeout": 25,
                "max_filesize": 50 * 1024 * 1024, # 50MB telegram cheklovi
            }

            if PROXY:
                ydl_opts["proxy"] = PROXY

            if is_audio:
                ydl_opts.update({
                    "format": "bestaudio/best",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                })
            else:
                ydl_opts.update({
                    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "merge_output_format": "mp4",
                })

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
            except Exception as e:
                # Agar format topilmasa, eng sodda 'best' bilan qayta urinib ko'rish
                if not is_audio:
                    ydl_opts["format"] = "best"
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                else:
                    raise e

            title = info.get("title", "Media")
            duration = info.get("duration", 0)

            # Qidirilgan fayl nomini topish
            expected_file = DOWNLOADS_DIR / f"media_{file_id}.{ext}"
            if expected_file.exists():
                return {
                    "title": title,
                    "file_path": expected_file,
                    "duration": duration,
                    "source": "yt-dlp"
                }

            # Fayl kengaytmasi boshqa bo'lishi mumkin
            for f in DOWNLOADS_DIR.glob(f"media_{file_id}.*"):
                if f.is_file() and f.stat().st_size > 0:
                    return {
                        "title": title,
                        "file_path": f,
                        "duration": duration,
                        "source": "yt-dlp"
                    }

            raise RuntimeError("Fayl yuklandi, ammo diskda topilmadi.")

        return await asyncio.to_thread(_download)

    @classmethod
    async def download_media(cls, url: str) -> Dict[str, Any]:
        """Har qanday URL dan eng mos usul orqali video yuklash"""
        clean_url = url.strip()

        # 1. TikTok havolasi bo'lsa:
        if "tiktok.com" in clean_url or "douyin.com" in clean_url:
            tik_res = await cls.download_tiktok_tikwm(clean_url)
            if tik_res:
                return tik_res

        # 2. Instagram bo'lsa (yt-dlp proxy orqali ajoyib ishlaydi):
        if "instagram.com" in clean_url:
            try:
                res = await cls.download_ytdlp(clean_url, is_audio=False)
                return {
                    "title": res["title"],
                    "video_path": res["file_path"],
                    "audio_path": None,
                    "duration": res.get("duration", 0),
                    "source": "instagram-ytdlp"
                }
            except Exception:
                # Fallback: parth_dl
                insta_res = await cls.download_instagram_parth(clean_url)
                if insta_res:
                    return insta_res
                raise

        # 3. Umumiy yt-dlp bilan yuklash (YouTube va boshqalar):
        res = await cls.download_ytdlp(clean_url, is_audio=False)
        return {
            "title": res["title"],
            "video_path": res["file_path"],
            "audio_path": None,
            "duration": res.get("duration", 0),
            "source": "yt-dlp"
        }


    @classmethod
    async def extract_audio_from_video(cls, video_path: Path) -> Path:
        """Mavjud videodan MP3 formatda audio ajratib olish (FFmpeg yordamida)"""
        audio_filename = f"audio_{uuid.uuid4().hex[:8]}.mp3"
        audio_path = DOWNLOADS_DIR / audio_filename

        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "libmp3lame",
            "-ab", "192k",
            "-ar", "44100",
            str(audio_path)
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()

        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise RuntimeError("Audioni ajratib bo'lmadi.")

        return audio_path

    @classmethod
    async def search_music_youtube(cls, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """YouTube orqali musiqa qidirish (tez, faqat metadata, yuklamaydi)"""
        def _search():
            ydl_opts: Dict[str, Any] = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "skip_download": True,
                "noplaylist": True,
            }
            if PROXY:
                ydl_opts["proxy"] = PROXY

            results = []
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
                    if not info or "entries" not in info:
                        return results
                    for entry in info["entries"]:
                        if not entry:
                            continue
                        video_id = entry.get("id", "")
                        if not video_id:
                            continue
                        title = entry.get("title", "Noma'lum")
                        duration = entry.get("duration") or 0
                        uploader = entry.get("uploader") or entry.get("channel") or ""
                        # "Artist - Title" shaklida bo'lsa ajratamiz
                        artist = ""
                        clean_title = title
                        if " - " in title:
                            parts = title.split(" - ", 1)
                            artist = parts[0].strip()
                            clean_title = parts[1].strip()
                        elif uploader:
                            artist = uploader.replace(" - Topic", "").strip()
                        results.append({
                            "id": video_id,
                            "url": f"https://www.youtube.com/watch?v={video_id}",
                            "title": clean_title,
                            "artist": artist,
                            "duration": int(duration),
                        })
            except Exception as e:
                print(f"YouTube qidiruv xatosi: {e}")
            return results

        return await asyncio.to_thread(_search)

    @classmethod
    async def download_audio_by_url(cls, url: str) -> Path:
        """YouTube URL dan to'liq audio (MP3) yuklash"""
        def _download():
            file_id = uuid.uuid4().hex[:8]
            out_template = str(DOWNLOADS_DIR / f"track_{file_id}.%(ext)s")

            ydl_opts: Dict[str, Any] = {
                "outtmpl": out_template,
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
                "max_filesize": 45 * 1024 * 1024,
                "socket_timeout": 30,
            }
            if PROXY:
                ydl_opts["proxy"] = PROXY

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)

            # MP3 faylini topish
            mp3_file = DOWNLOADS_DIR / f"track_{file_id}.mp3"
            if mp3_file.exists() and mp3_file.stat().st_size > 50 * 1024:
                return mp3_file
            for f in DOWNLOADS_DIR.glob(f"track_{file_id}.*"):
                if f.is_file() and f.stat().st_size > 50 * 1024:
                    return f
            raise RuntimeError("Audio fayl topilmadi yoki juda kichik.")

        return await asyncio.to_thread(_download)


    @classmethod
    async def get_deezer_track(cls, track_id: str) -> Optional[Dict[str, Any]]:
        """Deezer track ID orqali musiqa ma'lumotlarini olish"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.deezer.com/track/{track_id}"
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        return None
                    item = await resp.json()
                    if "error" in item:
                        return None
                    return {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "artist": item.get("artist", {}).get("name", "Noma'lum"),
                        "duration": item.get("duration", 0),
                        "preview": item.get("preview"),
                        "link": item.get("link"),
                        "cover": item.get("album", {}).get("cover_medium")
                    }
        except Exception as e:
            print(f"Deezer get_track xatosi: {e}")
            return None

    @classmethod
    async def download_full_audio(cls, artist: str, title: str) -> Path:
        """To'liq qo'shiqni (full track MP3) YouTube yoki SoundCloud orqali yuklab olish"""
        def _download():
            file_id = uuid.uuid4().hex[:8]
            out_template = str(DOWNLOADS_DIR / f"full_{file_id}.%(ext)s")

            ydl_opts: Dict[str, Any] = {
                "outtmpl": out_template,
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
                "max_filesize": 45 * 1024 * 1024,
                "socket_timeout": 25,
            }

            if PROXY:
                ydl_opts["proxy"] = PROXY

            clean_artist = "" if artist in ["Noma'lum", "Unknown", None] else artist.strip()
            clean_title = title.strip()
            clean_query = f"{clean_artist} {clean_title}".strip()

            queries = [
                f"scsearch1:{clean_query}",
                f"ytsearch1:{clean_query} audio",
                f"ytsearch1:{clean_query}"
            ]

            for q in queries:
                try:
                    opts = dict(ydl_opts)
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(q, download=True)
                        if info:
                            expected_file = DOWNLOADS_DIR / f"full_{file_id}.mp3"
                            if expected_file.exists() and expected_file.stat().st_size > 200 * 1024:
                                return expected_file
                            for f in DOWNLOADS_DIR.glob(f"full_{file_id}.*"):
                                if f.is_file() and f.stat().st_size > 200 * 1024:
                                    return f
                except Exception as e:
                    print(f"Qidiruv xatosi ({q}): {e}")
                    continue

            raise RuntimeError("To'liq musiqa topilmadi.")

        return await asyncio.to_thread(_download)


    @classmethod
    async def download_preview_audio(cls, preview_url: str, title: str) -> Path:
        """Deezer audiosini yuklab berish (fallback)"""
        file_id = uuid.uuid4().hex[:8]
        audio_path = DOWNLOADS_DIR / f"music_{file_id}.mp3"
        async with aiohttp.ClientSession() as session:
            async with session.get(preview_url, timeout=15) as resp:
                if resp.status == 200:
                    with open(audio_path, "wb") as f:
                        f.write(await resp.read())
                    return audio_path
        raise RuntimeError("Musiqani yuklab bo'lmadi.")

