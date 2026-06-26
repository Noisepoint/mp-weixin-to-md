import unittest
from pathlib import Path

from mp_weixin_to_md.assets import _markdown_path
from mp_weixin_to_md.cli import _resolve_output_path, _safe_markdown_filename
from mp_weixin_to_md.markdown import MarkdownOptions, render_markdown
from mp_weixin_to_md.parser import parse_wechat_html


ROOT = Path(__file__).resolve().parents[1]


class ParserMarkdownTest(unittest.TestCase):
    def setUp(self):
        self.html = (ROOT / "tests" / "fixtures" / "minimal.html").read_text(encoding="utf-8")

    def html_with_body(self, body: str) -> str:
        return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script>
    var msg_title = "示例公众号文章".html(false);
    var nickname = "示例作者".html(false);
  </script>
</head>
<body>
  <div id="js_content">
    {body}
  </div>
</body>
</html>
"""

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
        self.assertIn("> 公众号：示例作者", markdown)
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

    def test_account_can_be_extracted_from_js_name(self):
        html = self.html.replace(
            'var nickname = "示例作者".html(false);',
            'var user_name = "gh_94dba26f8ca0";',
        ).replace(
            '<body>',
            '<body><span id="js_name">数字生命卡兹克</span>',
        )
        article = parse_wechat_html(html)

        self.assertEqual(article.author, "数字生命卡兹克")

    def test_body_footer_is_not_used_as_account(self):
        html = self.html.replace(
            'var nickname = "示例作者".html(false);',
            'var user_name = "gh_94dba26f8ca0";',
        ).replace(
            "</div>",
            '<p><span style="color:#b2b2b2">>/ 作者：卡兹克</span></p></div>',
        )
        article = parse_wechat_html(html)

        self.assertEqual(article.author, "")

    def test_ordered_list_respects_start_attribute(self):
        article = parse_wechat_html(self.html_with_body("""
<ol>
  <li>第一项</li>
  <li>第二项</li>
</ol>
<ol start="3">
  <li>第三项</li>
  <li>第四项</li>
</ol>
"""))

        self.assertIn("1. 第一项", article.body)
        self.assertIn("2. 第二项", article.body)
        self.assertIn("3. 第三项", article.body)
        self.assertIn("4. 第四项", article.body)

    def test_nested_pre_prefers_visible_inner_code_and_keeps_explanation(self):
        article = parse_wechat_html(self.html_with_body("""
<pre>
  <pre><code>npm create vite@latest
cd demo</code></pre>
  <pre style="display:none"><code>npm create vite@latest
cd demo</code></pre>
  <p>然后输入 droid 并继续。</p>
</pre>
"""))

        self.assertIn("```\nnpm create vite@latest\ncd demo\n```", article.body)
        self.assertIn("然后输入 droid 并继续。", article.body)
        code_block = article.body.split("```")[1]
        self.assertNotIn("然后输入 droid", code_block)

    def test_placeholder_url_stays_plain_text(self):
        article = parse_wechat_html(self.html_with_body("""
<p>配置地址：https://[your-project-id].supabase.co</p>
"""))

        self.assertIn("https://[your-project-id].supabase.co", article.body)
        self.assertNotIn("[https://[your-project-id].supabase.co]", article.body)


if __name__ == "__main__":
    unittest.main()
