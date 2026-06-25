import unittest
from pathlib import Path

from mp_weixin_to_md.assets import _markdown_path
from mp_weixin_to_md.cli import _resolve_output_path, _safe_markdown_filename
from mp_weixin_to_md.markdown import MarkdownOptions, render_markdown
from mp_weixin_to_md.parser import parse_wechat_html


ROOT = Path(__file__).resolve().parents[1]


class ParserMarkdownTest(unittest.TestCase):
    def setUp(self):
        self.html = (ROOT / "examples" / "minimal.html").read_text(encoding="utf-8")

    def test_parse_basic_article(self):
        article = parse_wechat_html(self.html, source_url="https://mp.weixin.qq.com/s/demo")

        self.assertEqual(article.title, "示例公众号文章")
        self.assertEqual(article.author, "示例作者")
        self.assertEqual(article.published, "2025-12-24 18:40")
        self.assertEqual(len(article.images), 1)
        self.assertIn("第一段正文", article.body)
        self.assertIn("@@IMAGE:0@@", article.body)

    def test_render_standard_markdown(self):
        article = parse_wechat_html(self.html, source_url="https://mp.weixin.qq.com/s/demo")
        markdown = render_markdown(article)

        self.assertIn("# 示例公众号文章", markdown)
        self.assertIn("> 作者：示例作者", markdown)
        self.assertIn("![正文图](https://mmbiz.qpic.cn/sz_mmbiz_png/example/1?wx_fmt=png)", markdown)
        self.assertIn("<span style=\"color:#ff0000\">红色重点</span>", markdown)

    def test_render_obsidian_local_images(self):
        article = parse_wechat_html(self.html)
        markdown = render_markdown(
            article,
            MarkdownOptions(
                format="obsidian",
                cover_path="images/cover.jpg",
                image_paths={0: "images/body-01.png"},
            ),
        )

        self.assertIn("![[images/cover.jpg]]", markdown)
        self.assertIn("![[images/body-01.png]]", markdown)

    def test_url_input_defaults_to_title_markdown(self):
        output_path = _resolve_output_path(
            None,
            "https://mp.weixin.qq.com/s/demo",
            "示例：公众号/文章?",
        )

        self.assertEqual(output_path, Path("示例_公众号_文章.md"))

    def test_html_input_defaults_to_same_stem_markdown(self):
        output_path = _resolve_output_path(None, "article.html", "示例公众号文章")

        self.assertEqual(output_path, Path("article.md"))

    def test_safe_markdown_filename_has_fallback(self):
        self.assertEqual(_safe_markdown_filename(" / "), "article.md")

    def test_gh_user_name_is_not_rendered_as_author(self):
        html = self.html.replace(
            'var nickname = "示例作者".html(false);',
            'var user_name = "gh_94dba26f8ca0";',
        )
        article = parse_wechat_html(html)

        self.assertEqual(article.author, "")

    def test_markdown_path_resolves_tmp_symlink(self):
        output_file = Path("/tmp/mp-weixin-realistic/article.md")
        asset_file = Path("/private/tmp/mp-weixin-realistic/images/body-01.png")

        self.assertEqual(_markdown_path(output_file, asset_file), "images/body-01.png")

    def test_bold_style_prefers_markdown_bold(self):
        html = self.html.replace(
            "<strong>粗体</strong>",
            '<span style="font-weight:700">粗体</span>',
        )
        article = parse_wechat_html(html)
        markdown = render_markdown(article)

        self.assertIn("**粗体**", markdown)
        self.assertNotIn('<span style="font-weight:700">粗体</span>', markdown)

    def test_author_can_be_in_body_footer(self):
        html = self.html.replace(
            'var nickname = "示例作者".html(false);',
            'var user_name = "gh_94dba26f8ca0";',
        ).replace(
            "</div>",
            '<p><span style="color:#b2b2b2">>/ 作者：卡兹克></span></p></div>',
        )
        article = parse_wechat_html(html)

        self.assertEqual(article.author, "卡兹克")


if __name__ == "__main__":
    unittest.main()
