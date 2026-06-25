"""微信公众号文章 HTML 的便利用法抓取。

URL 抓取只做 best-effort。微信可能返回验证页、空壳页或受网络环境影响失败；
稳定用法仍然是让用户保存完整 HTML 后再转换。
"""

from __future__ import annotations

import urllib.error
import urllib.request


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
    "MicroMessenger/8.0.49(0x1800312c) NetType/WIFI Language/zh_CN"
)


class FetchError(RuntimeError):
    """URL 抓取失败或返回内容不是完整微信公众号文章。"""


def fetch_html(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Referer": "https://mp.weixin.qq.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        raise FetchError(
            "URL 抓取失败。建议在浏览器中打开文章，保存完整 HTML 后再转换。"
        ) from error

    text = raw.decode("utf-8", errors="replace")
    if "js_content" not in text or "msg_title" not in text:
        raise FetchError(
            "URL 返回内容不像完整微信公众号文章，可能是验证页或空壳页。"
            "请手动保存完整 HTML 后再转换。"
        )
    return text
