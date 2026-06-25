"""把微信公众号完整 HTML 解析成结构化文章对象。"""

from __future__ import annotations

import datetime as dt
import html
import re
from dataclasses import dataclass, field
from urllib.parse import unquote

from lxml import html as lxml_html


NBSP = "\u00a0"
ZERO_WIDTH = "\u200b"
BLOCK_TAGS = {
    "article",
    "blockquote",
    "div",
    "figcaption",
    "figure",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "ol",
    "p",
    "pre",
    "section",
    "td",
    "tr",
    "table",
    "ul",
}
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
INLINE_TAGS = {"span", "strong", "b", "em", "i", "font", "label", "mark", "u"}


@dataclass
class ImageRef:
    """文章中的一张图片。"""

    url: str
    alt: str = ""
    ext: str = "png"
    role: str = "body"


@dataclass
class Article:
    """微信公众号文章的最小结构。"""

    title: str
    source_url: str = ""
    published: str = ""
    author: str = ""
    cover: ImageRef | None = None
    body: str = ""
    images: list[ImageRef] = field(default_factory=list)


class ParseError(ValueError):
    """HTML 不是可解析的完整微信公众号文章。"""


def parse_wechat_html(source_html: str, source_url: str = "") -> Article:
    title = _extract_meta(source_html, "title").strip()
    author = _extract_author(source_html)
    published = _extract_published(source_html)
    cover_url = _extract_meta(source_html, "cover").strip()

    if not title or "js_content" not in source_html:
        raise ParseError("未提取到标题或 js_content，输入可能不是完整微信公众号 HTML。")

    tree = lxml_html.fromstring(source_html)
    try:
        content = tree.get_element_by_id("js_content")
    except KeyError as error:
        raise ParseError("找不到 #js_content，输入可能不是完整微信公众号 HTML。") from error

    renderer = _BodyRenderer()
    body = renderer.render(content)
    if not author:
        author = _extract_author_from_body(body)
    cover = (
        ImageRef(url=cover_url, alt=title, ext=resource_extension(cover_url, "jpg"), role="cover")
        if cover_url
        else None
    )
    return Article(
        title=title,
        source_url=source_url or _extract_meta(source_html, "source").strip(),
        published=published,
        author=author,
        cover=cover,
        body=body,
        images=renderer.images,
    )


def resource_extension(url: str, default: str = "png") -> str:
    match = re.search(r"wx_fmt=([a-z0-9]+)", url, re.I)
    if match:
        return _normalize_extension(match.group(1))
    match = re.search(r"\.(jpg|jpeg|png|gif|webp)(?:[?#]|$)", url, re.I)
    if match:
        return _normalize_extension(match.group(1))
    return default


def _normalize_extension(value: str) -> str:
    value = value.lower()
    return "jpg" if value == "jpeg" else value


def _extract_meta(source_html: str, key: str) -> str:
    patterns = {
        "title": [
            r'var\s+msg_title\s*=\s*"(.*?)"\.html',
            r'<meta\s+property="og:title"\s+content="(.*?)"',
            r"<title>(.*?)</title>",
        ],
        "author": [
            r'var\s+nickname\s*=\s*"(.*?)"\.html',
            r'var\s+user_name\s*=\s*"(.*?)"',
        ],
        "cover": [
            r'var\s+msg_cdn_url\s*=\s*"(.*?)"',
            r'<meta\s+property="og:image"\s+content="(.*?)"',
            r'<meta\s+name="twitter:image"\s+content="(.*?)"',
        ],
        "source": [
            r'<meta\s+property="og:url"\s+content="(.*?)"',
        ],
    }
    for pattern in patterns[key]:
        match = re.search(pattern, source_html, re.S)
        if match:
            return _clean_text(match.group(1))
    return ""


def _extract_author(source_html: str) -> str:
    nickname = _extract_meta(source_html, "author").strip()
    if nickname.startswith("gh_"):
        return ""
    return nickname


def _extract_author_from_body(body: str) -> str:
    tail = "\n".join(body.splitlines()[-20:])
    clean_tail = re.sub(r"<[^>]+>", "", tail)
    clean_tail = html.unescape(clean_tail)
    match = re.search(r"(?:^|[>/\s])作者[：:]\s*([^\s<，,。|/<>]{1,30})", clean_tail)
    if not match:
        return ""
    author = match.group(1).strip(" >")
    return "" if author.startswith("gh_") else author


def _extract_published(source_html: str) -> str:
    timestamp_match = re.search(r'var\s+ct\s*=\s*"(\d+)"', source_html)
    if timestamp_match:
        timestamp = int(timestamp_match.group(1))
        return dt.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
    text_match = re.search(r'id="publish_time"[^>]*>(.*?)</', source_html, re.S)
    if text_match:
        return _clean_text(text_match.group(1))
    return ""


def _clean_text(value: str) -> str:
    return html.unescape(value).replace("&nbsp;", " ").replace(NBSP, " ").strip()


class _BodyRenderer:
    def __init__(self) -> None:
        self.images: list[ImageRef] = []

    def render(self, element) -> str:
        output: list[str] = []
        self._walk_children(element, output)
        body = "".join(output)
        body = body.replace(NBSP, " ").replace(ZERO_WIDTH, "")
        body = re.sub(r"[ \t]+\n", "\n", body)
        body = re.sub(r"\n{3,}", "\n\n", body)
        return body.strip()

    def _walk_children(self, element, output: list[str]) -> None:
        for child in element:
            if not isinstance(child.tag, str):
                continue
            tag = child.tag.lower()
            if tag == "pre":
                code = child.text_content().replace(NBSP, " ").replace(ZERO_WIDTH, "").strip("\n")
                if code.strip():
                    output.append(f"\n\n```\n{code}\n```\n\n")
            elif tag in HEADING_TAGS:
                text = self._render_inline(child).strip()
                if text:
                    level = min(int(tag[1]), 6)
                    output.append(f"\n\n{'#' * level} {text}\n\n")
            elif tag in {"ul", "ol"}:
                output.append("\n")
                self._render_list(child, output, ordered=tag == "ol")
                output.append("\n")
            elif tag == "blockquote":
                text = self._render_inline(child).strip()
                if text:
                    quoted = "\n".join(f"> {line}" if line else ">" for line in text.splitlines())
                    output.append(f"\n\n{quoted}\n\n")
            elif tag == "hr":
                output.append("\n\n---\n\n")
            elif tag in BLOCK_TAGS and self._has_block_descendant(child):
                self._walk_children(child, output)
            else:
                text = self._render_inline(child).strip()
                if text:
                    output.append(f"\n\n{text}\n\n")

    def _render_inline(self, element, inherited_bold: bool = False) -> str:
        parts: list[str] = []
        if element.text:
            parts.append(element.text)
        for child in element:
            if not isinstance(child.tag, str):
                if child.tail:
                    parts.append(child.tail)
                continue
            tag = child.tag.lower()
            if tag == "br":
                parts.append("\n")
            elif tag == "img":
                marker = self._add_image(child)
                if marker:
                    parts.append(f"\n\n{marker}\n\n")
            elif tag == "a":
                inner = self._render_inline(child, inherited_bold).strip()
                href = html.unescape(child.get("href", "")).strip()
                if href and inner and not href.startswith("javascript"):
                    parts.append(f"[{inner}]({href})")
                else:
                    parts.append(inner)
            elif tag in INLINE_TAGS:
                inner = self._render_inline(child, inherited_bold)
                parts.append(self._wrap_inline(child, inner, inherited_bold))
            elif tag in {"sub", "sup"}:
                parts.append(self._render_inline(child, inherited_bold))
            else:
                parts.append(self._render_inline(child, inherited_bold))
            if child.tail:
                parts.append(child.tail)
        return "".join(parts)

    def _render_list(self, element, output: list[str], ordered: bool, depth: int = 0) -> None:
        number = 1
        for child in element:
            if not isinstance(child.tag, str):
                continue
            tag = child.tag.lower()
            if tag not in {"li", "ul", "ol"}:
                continue
            if tag in {"ul", "ol"}:
                self._render_list(child, output, ordered=tag == "ol", depth=depth + 1)
                continue
            nested = [
                item for item in child
                if isinstance(item.tag, str) and item.tag.lower() in {"ul", "ol"}
            ]
            inline_parts: list[str] = []
            if child.text:
                inline_parts.append(child.text)
            for item in child:
                if isinstance(item.tag, str) and item.tag.lower() in {"ul", "ol"}:
                    continue
                inline_parts.append(self._render_inline(item))
                if item.tail:
                    inline_parts.append(item.tail)
            text = " ".join("".join(inline_parts).strip().split())
            if text:
                marker = f"{number}. " if ordered else "- "
                output.append("  " * depth + marker + text + "\n")
                number += 1
            for nested_list in nested:
                self._render_list(
                    nested_list,
                    output,
                    ordered=nested_list.tag.lower() == "ol",
                    depth=depth + 1,
                )

    def _add_image(self, element) -> str:
        url = (
            element.get("data-src")
            or element.get("data-original")
            or element.get("src")
            or ""
        )
        url = unquote(html.unescape(url.strip()))
        if url.startswith("//"):
            url = "https:" + url
        if not url.startswith(("http://", "https://")):
            return ""
        alt = _clean_text(element.get("alt", ""))
        image = ImageRef(url=url, alt=alt, ext=resource_extension(url))
        self.images.append(image)
        return f"@@IMAGE:{len(self.images) - 1}@@"

    def _wrap_inline(self, element, inner: str, inherited_bold: bool) -> str:
        lead = inner[: len(inner) - len(inner.lstrip())]
        trail = inner[len(inner.rstrip()):]
        core = inner.strip()
        if not core:
            return inner

        tag = element.tag.lower()
        style = _parse_style(element.get("style", ""))
        css = _meaningful_style(style)
        own_bold = tag in {"strong", "b"} or "font-weight:700" in css
        if tag == "u" and "text-decoration:underline" not in css:
            css.append("text-decoration:underline")

        if css == ["font-weight:700"]:
            return f"{lead}**{core}**{trail}" if not inherited_bold else inner
        if css:
            return f'{lead}<span style="{";".join(css)}">{core}</span>{trail}'
        if own_bold and not inherited_bold:
            return f"{lead}**{core}**{trail}"
        if tag in {"em", "i"}:
            return f"{lead}*{core}*{trail}"
        return inner

    def _has_block_descendant(self, element) -> bool:
        return any(
            isinstance(item.tag, str) and item.tag.lower() in BLOCK_TAGS
            for item in element.iterdescendants()
        )


def _parse_style(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in value.split(";"):
        if ":" not in part:
            continue
        key, item = part.split(":", 1)
        result[key.strip().lower()] = item.strip().lower()
    return result


def _meaningful_style(style: dict[str, str]) -> list[str]:
    props: list[str] = []
    color = _normalize_color(style.get("color", ""))
    background = _normalize_color(style.get("background-color", ""))
    decoration = " ".join(
        [style.get("text-decoration", ""), style.get("text-decoration-line", "")]
    )
    if color:
        props.append(f"color:{color}")
    if background:
        props.append(f"background-color:{background}")
    if _is_bold(style):
        props.append("font-weight:700")
    if "underline" in decoration:
        props.append("text-decoration:underline")
    if "line-through" in decoration:
        props.append("text-decoration:line-through")
    return props


def _is_bold(style: dict[str, str]) -> bool:
    weight = style.get("font-weight", "")
    if weight in {"bold", "bolder"}:
        return True
    try:
        return int(weight) >= 600
    except ValueError:
        return False


def _normalize_color(value: str) -> str:
    if not value:
        return ""
    value = value.strip().lower()
    match = re.match(r"rgba?\(([^)]+)\)", value)
    if match:
        parts = [part.strip() for part in match.group(1).split(",")]
        try:
            red, green, blue = (int(float(parts[index])) for index in range(3))
            alpha = float(parts[3]) if len(parts) > 3 else 1
        except (ValueError, IndexError):
            return ""
        if alpha == 0 or (red, green, blue) == (0, 0, 0):
            return ""
        if red >= 250 and green >= 250 and blue >= 250:
            return ""
        return f"#{red:02x}{green:02x}{blue:02x}"
    if value in {"#000", "#000000", "#fff", "#ffffff", "black", "white"}:
        return ""
    if re.fullmatch(r"#[0-9a-f]{3}([0-9a-f]{3})?", value):
        return value
    return {"red": "#ff0000", "blue": "#0000ff"}.get(value, "")
