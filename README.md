# mp-weixin-to-md

输入微信公众号文章链接，输出 Markdown 文件的最小命令行工具。

主线用法只有一句：

```bash
mp-weixin-to-md "https://mp.weixin.qq.com/s/xxxx"
```

命令会自动抓取文章、解析标题和正文，并在当前目录生成：

```text
文章标题.md
```

注意：微信公众号链接抓取受微信验证页和网络环境影响，无法保证 100% 成功。工具会尽力直接处理链接；如果微信返回验证页或空壳页，命令会明确报错。

## 安装

当前仓库不做 PyPI 发布流程。普通用户推荐用 `pipx` 安装，这样安装后可以在任何目录直接运行 `mp-weixin-to-md`。

如果电脑还没有 `pipx`，先复制下面两行到终端运行一次：

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

然后新开一个终端。

再安装本项目：

```bash
git clone https://github.com/Noisepoint/mp-weixin-to-md.git
cd mp-weixin-to-md
pipx install .
```

安装完成后，不需要再进入项目目录。

以后在任何目录都可以直接运行：

```bash
mp-weixin-to-md "https://mp.weixin.qq.com/s/xxxx"
```

不要复制 Markdown 代码块标记。只复制代码块里面的命令，不要复制开头和结尾的三个反引号。

## 用法

### 转换公众号链接

```bash
mp-weixin-to-md "https://mp.weixin.qq.com/s/xxxx"
```

把 `https://mp.weixin.qq.com/s/xxxx` 换成真实公众号文章链接。

命令成功后，会在你当前所在目录生成一个 Markdown 文件：

```text
文章标题.md
```

例如你当前在桌面运行，文件就会生成到桌面。

默认输出标准 Markdown，并自动用文章标题命名。

### 自己指定文件名

普通用户通常不需要这个参数。如果你不想用自动生成的文章标题，可以自己指定输出文件名：

```bash
mp-weixin-to-md "https://mp.weixin.qq.com/s/xxxx" -o article.md
```

这会生成：

```text
article.md
```

### 图片会不会自动下载？

默认**不会下载图片**。

默认生成的 Markdown 里，图片还是微信远程链接：

```md
![图片](https://mmbiz.qpic.cn/xxx)
```

如果你打开 Markdown 时有网络，图片可能可以显示；但图片文件没有保存到本地。

如果你想把图片也下载下来，加 `--download-assets`：

```bash
mp-weixin-to-md "https://mp.weixin.qq.com/s/xxxx" --download-assets
```

这会在当前目录生成：

```text
文章标题.md
images/
  cover.jpg
  body-01.png
  body-02.png
```

Markdown 里的图片会变成本地路径：

```md
![正文图](images/body-01.png)
```

出于安全考虑，资源下载只允许常见微信图片域名，例如 `mmbiz.qpic.cn`。

默认图片目录是 `images/`。如果想换成别的目录，再加 `--assets-dir`：

```bash
mp-weixin-to-md "https://mp.weixin.qq.com/s/xxxx" --download-assets --assets-dir my-images
```

### 可选 Obsidian 输出

默认输出永远是标准 Markdown。Obsidian 只是可选格式：

```bash
mp-weixin-to-md "https://mp.weixin.qq.com/s/xxxx" \
  --download-assets \
  --format obsidian
```

输出示例：

```md
![[images/body-01.png]]
```

`--format obsidian` 只改变本地图片引用语法，不会加入个人 frontmatter、运营复盘字段或账号信息。

### 链接失败时的备用方式

如果微信返回验证页、空壳页或网络失败，可以把完整 HTML 文件交给工具转换：

```bash
mp-weixin-to-md article.html
```

这会在同目录生成 `article.md`。本地 HTML 是备用能力，不是主线入口。

## 当前支持

- 标题、作者、发布时间、原文 URL
- 封面图
- 正文段落、标题、列表、引用、分割线
- 链接、粗体、斜体
- 有意义的行内样式：颜色、背景色、加粗、下划线、删除线
- 代码块
- 正文图片
- 可选本地图片下载
- 可选 Obsidian 图片语法

## 不承诺

- 不承诺所有微信公众号链接都能直接抓取成功。
- 不内置 Cookie，不绕过登录或验证页。
- 不做完整剪藏系统，不绑定任何个人 Obsidian 工作流。
- 不默认加入账号名、作者名、运营复盘 frontmatter。

## 开发者

开发者本地调试可以用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

运行测试：

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

测试是给开发者检查代码有没有坏用的，普通用户不需要运行。
