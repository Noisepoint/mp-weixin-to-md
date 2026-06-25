"""把文章对象渲染为标准 Markdown 或 Obsidian Markdown。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .parser import Article


@dataclass
class MarkdownOptions:
    """Markdown 输出选项。"""

    format: str = "standard"
    image_paths: dict[int, str] = field(default_factory=dict)
    cover_path: str = ""


def render_markdown(article: Article, options: MarkdownOptions | None = None) -> str:
    options = options or MarkdownOptions()
    if options.format not in {"standard", "obsidian"}:
        raise ValueError("format 只能是 standard 或 obsidian。")

    lines: list[str] = [f"# {article.title}", ""]
    info_lines = _source_lines(article)
    if info_lines:
        lines.extend(info_lines)
        lines.append("")

    cover = _render_cover(article, options)
    if cover:
        lines.extend([cover, ""])

    body = _replace_image_markers(article, article.body, options)
    if body:
        lines.append(body)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines).strip() + "\n")


def _source_lines(article: Article) -> list[str]:
    lines: list[str] = []
    if article.author:
        lines.append(f"> 作者：{article.author}")
    if article.published:
        lines.append(f"> 发布：{article.published}")
    if article.source_url:
        lines.append(f"> 原文：[微信公众号]({article.source_url})")
    return lines


def _render_cover(article: Article, options: MarkdownOptions) -> str:
    if not article.cover:
        return ""
    target = options.cover_path or article.cover.url
    if not target:
        return ""
    return _image(article.cover.alt or article.title, target, options.format)


def _replace_image_markers(article: Article, body: str, options: MarkdownOptions) -> str:
    def replace(match: re.Match[str]) -> str:
        index = int(match.group(1))
        image_ref = article.images[index]
        target = options.image_paths.get(index, image_ref.url)
        return _image(image_ref.alt, target, options.format)

    return re.sub(r"@@IMAGE:(\d+)@@", replace, body)


def _image(alt: str, target: str, output_format: str) -> str:
    alt = alt.replace("\n", " ").strip()
    if output_format == "obsidian" and not target.startswith(("http://", "https://")):
        return f"![[{target}]]"
    return f"![{alt}]({target})"
