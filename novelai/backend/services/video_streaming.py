"""
Helpers de streaming de vídeo.
Para vídeos locais (gerados): serve com range requests.
Para vídeos externos (scraped): redireciona para a URL original.
"""
from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse, RedirectResponse
from pathlib import Path
import aiofiles
from loguru import logger


GENERATED_DIR = Path("generated_videos")
CHUNK_SIZE = 1024 * 1024  # 1 MB


async def stream_video(request: Request, video_url: str):
    if video_url.startswith("/generated/"):
        return await _stream_local(request, video_url)
    return RedirectResponse(url=video_url)


async def _stream_local(request: Request, video_path_str: str):
    filename = video_path_str.replace("/generated/", "")
    file_path = GENERATED_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        start, end = _parse_range(range_header, file_size)
        length = end - start + 1

        async def iterfile():
            async with aiofiles.open(file_path, "rb") as f:
                await f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = await f.read(min(CHUNK_SIZE, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
            "Content-Type": "video/mp4",
        }
        return StreamingResponse(iterfile(), status_code=206, headers=headers)

    async def full_file():
        async with aiofiles.open(file_path, "rb") as f:
            while True:
                chunk = await f.read(CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        full_file(),
        media_type="video/mp4",
        headers={"Content-Length": str(file_size), "Accept-Ranges": "bytes"},
    )


def _parse_range(range_header: str, file_size: int) -> tuple[int, int]:
    try:
        range_str = range_header.replace("bytes=", "")
        start_str, end_str = range_str.split("-")
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        end = min(end, file_size - 1)
        return start, end
    except Exception:
        return 0, file_size - 1
