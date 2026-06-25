"""命令行入口。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .assets import AssetDownloadError, download_assets
from .fetch import FetchError, fetch_html
from .markdown import MarkdownOptions, render_markdown
from .parser import ParseError, parse_wechat_html


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert WeChat Official Account article HTML or URL to Markdown."
    )
    parser.add_argument("input", help="本地完整 HTML 文件，或 mp.weixin.qq.com 文章 URL")
    parser.add_argument(
        "-o",
        "--output",
        help="输出 Markdown 文件；不传时自动使用文章标题生成 .md",
    )
    parser.add_argument(
        "--format",
        choices=["standard", "obsidian"],
        default="standard",
        help="输出格式，默认 standard；obsidian 只影响本地图片引用语法",
    )
    parser.add_argument(
        "--download-assets",
        action="store_true",
        help="下载封面和正文图片，并把 Markdown 图片链接改成本地路径",
    )
    parser.add_argument(
        "--assets-dir",
        default="images",
        help="图片保存目录，默认相对输出文件所在目录的 images/",
    )
    parser.add_argument("--timeout", type=int, default=20, help="URL/图片下载超时时间，单位秒")
    args = parser.parse_args(argv)

    input_value = args.input
    try:
        source_html, source_url = _load_input(input_value, args.timeout)
        article = parse_wechat_html(source_html, source_url=source_url)
        output_file = _resolve_output_path(args.output, input_value, article.title)
        asset_result = None
        if args.download_assets:
            asset_result = download_assets(article, output_file, args.assets_dir, args.timeout)
        options = MarkdownOptions(
            format=args.format,
            cover_path=asset_result.cover_path if asset_result else "",
            image_paths=asset_result.image_paths if asset_result else {},
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(render_markdown(article, options), encoding="utf-8")
    except (OSError, FetchError, ParseError, AssetDownloadError, ValueError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1

    print(f"已写入：{output_file}")
    return 0


def _load_input(input_value: str, timeout: int) -> tuple[str, str]:
    if input_value.startswith(("http://", "https://")):
        return fetch_html(input_value, timeout=timeout), input_value
    html_path = Path(input_value)
    return html_path.read_text(encoding="utf-8"), ""


def _resolve_output_path(output: str | None, input_value: str, title: str) -> Path:
    if output:
        return Path(output)
    if input_value.startswith(("http://", "https://")):
        return Path(_safe_markdown_filename(title))
    return Path(input_value).with_suffix(".md")


def _safe_markdown_filename(title: str) -> str:
    stem = re.sub(r'[\\/:*?"<>|：\r\n\t]', "_", title).strip(" ._")
    stem = re.sub(r"\s+", " ", stem)
    stem = re.sub(r"_+", "_", stem).strip(" ._")
    if not stem:
        stem = "article"
    if len(stem) > 120:
        stem = stem[:120].rstrip(" .")
    return stem + ".md"
