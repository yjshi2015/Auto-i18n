# Auto-i18n：使用 ChatGPT 的自动多语言翻译工具

Auto-i18n 是一个使用 ChatGPT 自动将 Markdown 文件批量翻译为多语言的工具。它实现了博客文章 i18n(Internationalization) 的全自动化。你仅需将博文推送至 GitHub 仓库，即可借助 GitHub Actions 实现自动转译为多种语言。（目前支持英语、西班牙语、阿拉伯语、日语和韩语）

Auto-i18n 的主要特性：

- **批量多语言翻译**：Auto-i18n 提供了批量翻译的功能，使你能够将一整个路径下的所有 Markdown 文档一次性翻译多语言，极大地提高了多语言化项目的效率。
- **兼容 Front Matter**：Auto-i18n 兼容 Markdown Front Matter 语法，你可以自定义不同字段的翻译或替换规则。
- **固定内容替换**：Auto-i18n 还支持固定内容替换。如果你希望文档中一些重复字段的译文保持不变，这个功能可以帮助你实现文档的一致性。
- **自动化工作流**：你可以使用 GitHub Actions 实现自动化的翻译流程，无需手动干预，翻译工作会自动进行并更新文档，使你能够更专注于内容。
- **灵活的语言配置**：支持任意语言之间的相互翻译，不再局限于中文作为源语言。

## 快速上手

1. 将仓库克隆到本地，把 `env_template.py` 重命名为 `env.py`，并提供你的 ChatGPT API。如果你没有自己的 API，可以到 [GPT_API_free](https://github.com/chatanywhere/GPT_API_free) 申请到一个免费的；也可以借助 [go-chatgpt-api](https://github.com/linweiyuan/go-chatgpt-api) 把网页版 ChatGPT 转 API 使用。
2. 安装必需的模块：`pip install -r requirements.txt` 。
3. 执行命令 `python auto-translater-course.py <source_lang> <target_lang1> [target_lang2 ...]` 运行程序。

### 命令行参数说明

```bash
python auto-translater-course.py <source_lang> <target_lang1> [target_lang2 ...] [--dir DIR] [--exclude FILE1 FILE2 ...]
```

参数说明：
- `source_lang`：源语言代码（例如：zh, en, ja）
- `target_lang1, target_lang2, ...`：目标语言代码列表（例如：ja ko en）
- `--dir`：要翻译的目录路径（可选，默认为 "testdir/to-translate"）
- `--exclude`：要排除的文件列表（可选，默认为 ["index.md", "Contact-and-Subscribe.md", "WeChat.md"]）

支持的语言代码：
- `zh`：中文
- `en`：英语
- `es`：西班牙语
- `ar`：阿拉伯语
- `ja`：日语
- `ko`：韩语

使用示例：
```bash
# 从中文翻译到日语和英语
python auto-translater-course.py zh ja en

# 从英语翻译到中文和日语
python auto-translater-course.py en zh ja

# 从日语翻译到中文和英语，指定目录和排除文件
python auto-translater-course.py ja zh en --dir mydocs --exclude README.md LICENSE.md
```

## 详细描述

程序 `auto-translater-course.py` 的运行逻辑如下：

1. 程序将自动处理指定目录下的所有 Markdown 文件，你可以在 `--exclude` 参数中排除不需要翻译的文件。
2. 处理后的文件名会被记录在自动生成的 `processed_list.txt` 中。下次运行程序时，已处理的文件将不会再次翻译。
3. 如果 Markdown 文件中包含 Front Matter，将按照程序内的规则 `front_matter_translation_rules` 选择以下处理方式：
   1. 自动翻译：由 ChatGPT 翻译。适用于文章标题或文章描述字段。
   2. 固定字段替换：适用于分类或标签字段。例如同一个中文标签名，不希望被翻译成不同的英文标签造成索引错误。
   3. 不做任何处理：如果字段未出现在以上两种规则中，将保留原文，不做任何处理。适用于日期、url 等。

## 翻译质量保证

程序使用 ChatGPT API 进行翻译，并遵循以下原则：
1. 保持 Markdown 格式不变
2. 保持技术术语的准确性
3. 保持代码块中的代码不变，只翻译注释
4. 保持占位符 `[to_be_replace[x]]` 不变
5. 使用自然、专业的语言风格

## GitHub Actions 自动化指南

你可以在自己项目仓库下创建 `.github/workflows/ci.yml`，当检测到 GitHub 仓库更新后，可以使用 GitHub Actions 自动进行翻译处理，并自动 commit 回原仓库。

`ci.yml` 的内容可参考模板：[ci_template.yml](https://github.com/linyuxuanlin/Auto-i18n/blob/main/ci_template.yml)

你需要在仓库的 `Settings` - `Secrets and variables` - `Repository secrets` 中添加两个 secrets：`CHATGPT_API_BASE` 和 `CHATGPT_API_KEY`，并在程序 `auto-translater.py` 中将 `import env` 语句注释掉。

## 错误排除

1. 如果需要验证 ChatGPT API key 的可用性，可以使用程序 [verify-api-key.py](https://github.com/linyuxuanlin/Auto-i18n/blob/main/Archive/verify-api-key.py) 进行测试。如果在国内使用官方 API，需要有本地代理。
2. 如果 Markdown 中的 Front Matter 无法被正常识别，可以使用程序 [detect_front_matter.py](https://github.com/linyuxuanlin/Auto-i18n/blob/main/Archive/detect_front_matter.py) 测试。
3. 在使用 GitHub Actions 遇到问题时，请优先检查路径引用是否正确（例如 `dir_to_translate` `dir_translated_en` `dir_translated_es` `dir_translated_ar` `processed_list`）。

## 待解决的问题

1. 在某些特殊的情况下，可能会出现翻译不准确、或某些字段没有翻译的情况，建议翻译后手动校验再发布文章。
2. （已解决）~~如果 Markdown 中包含 Front Matter，将保留 Front Matter 的原始内容。Front Matter 部分参数翻译的功能正在开发中。~~

## 贡献

欢迎你参与本项目的改进！如果您想要贡献代码、报告问题或提出建议，请查看 [贡献指南](https://github.com/linyuxuanlin/Auto-i18n/blob/main/CONTRIBUTING.md)。

## 版权和许可

本项目采用 [MIT 许可证](https://github.com/linyuxuanlin/Auto-i18n/blob/main/LICENSE)。

## 问题和支持

如果你在使用 Auto-i18n 时遇到任何问题，或者需要技术支持，请随时 [提交问题](https://github.com/linyuxuanlin/Auto-i18n/issues)。

我的博客使用 Auto-i18n 实现了多语言支持，你可以到 [Power's Wiki](https://wiki-power.com) 查看 Demo 效果。

[![](https://wiki-media-1253965369.cos.ap-guangzhou.myqcloud.com/img/202310222223670.png)](https://wiki-power.com)

## 致谢

- 感谢 [chatanywhere/GPT_API_free](https://github.com/chatanywhere/GPT_API_free) 提供的免费 ChatGPT API key。
- 感谢 [linweiyuan/go-chatgpt-api](https://github.com/linweiyuan/go-chatgpt-api) 提供的把网页版 ChatGPT 转 API 的方法。

[![Star History Chart](https://api.star-history.com/svg?repos=linyuxuanlin/Auto-i18n&type=Date)](https://star-history.com/#linyuxuanlin/Auto-i18n&Date)
