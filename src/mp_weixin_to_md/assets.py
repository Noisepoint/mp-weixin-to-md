"""可选图片下载与 Markdown 路径映射。"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .fetch import DEFAULT_USER_AGENT
from .parser import Article, ImageRef


ALLOWED_IMAGE_HOSTS = {"mmbiz.qpic.cn", "mmbiz.qlogo.cn", "res.wx.qq.com"}


@dataclass
class AssetResult:
    cover_path: str = ""
    image_paths: dict[int, str] = field(default_factory=dict)


class AssetDownloadError(RuntimeError):
    """资源下载失败。"""


def download_assets(article: Article, output_file: Path, assets_dir: str, timeout: int = 20) -> AssetResult:
    base_dir = output_file.parent if output_file.name else Path.cwd()
    target_dir = (base_dir / assets_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    result = AssetResult()
    if article.cover:
        name = f"cover.{article.cover.ext}"
        _download_image(article.cover, target_dir / name, timeout)
        result.cover_path = _markdown_path(output_file, target_dir / name)

    for index, image in enumerate(article.images, 1):
        name = f"body-{index:02d}.{image.ext}"
        _download_image(image, target_dir / name, timeout)
        result.image_paths[index - 1] = _markdown_path(output_file, target_dir / name)
    return result


def _download_image(image: ImageRef, destination: Path, timeout: int) -> None:
    if not _allowed_image_url(image.url):
        raise AssetDownloadError(f"拒绝下载非微信图片域名：{image.url}")
    request = urllib.request.Request(
        image.url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Referer": "https://mp.weixin.qq.com/",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            raw = response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        raise AssetDownloadError(f"下载失败：{image.url}") from error

    if not content_type.startswith("image/") and len(raw) < 1024:
        raise AssetDownloadError(f"返回内容不像图片：{image.url}")
    destination.write_bytes(raw)


def _allowed_image_url(url: str) -> bool:
    try:
        host = urllib.request.urlparse(url).hostname or ""
    except ValueError:
        return False
    return host in ALLOWED_IMAGE_HOSTS


def _markdown_path(output_file: Path, asset_file: Path) -> str:
    try:
        output_dir = output_file.parent.resolve()
        return os.path.relpath(asset_file.resolve(), output_dir)
    except ValueError:
        return str(asset_file)
