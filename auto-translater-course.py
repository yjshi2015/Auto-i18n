# -*- coding: utf-8 -*-
import os
import openai  # pip install openai
import sys
import re
import yaml  # pip install PyYAML
import env
import argparse

# 设置 OpenAI API Key 和 API Base 参数，通过 env.py 传入
client = openai.OpenAI(
    api_key=os.environ.get("CHATGPT_API_KEY"),
    base_url=os.environ.get("CHATGPT_API_BASE")
)

# 设置最大输入字段，超出会拆分输入，防止超出输入字数限制
max_length = 1800

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "ar": "Arabic",
    "ja": "Japanese",
    "ko": "Korean"
}

# 默认配置
DEFAULT_DIR_TO_TRANSLATE = "testdir/to-translate"
DEFAULT_EXCLUDE_LIST = ["index.md", "Contact-and-Subscribe.md", "WeChat.md"]
DEFAULT_PROCESSED_LIST = "processed_list.txt"

# 设置翻译的路径
dir_translated = {
    "en": "testdir/docs/en",
    "es": "testdir/docs/es",
    "ar": "testdir/docs/ar",
    "ja": "testdir/docs/ja",
    "ko": "testdir/docs/ko"
}

# 文章使用英文撰写的提示，避免本身为英文的文章被重复翻译为英文
marker_written_in_en = "\n> This post was originally written in English.\n"
# 即使在已处理的列表中，仍需要重新翻译的标记
marker_force_translate = "\n[translate]\n"

# Front Matter 处理规则
front_matter_translation_rules = {
    # 调用 ChatGPT 自动翻译
    "title": lambda value, lang: translate_text(value, lang,"front-matter"),
    "description": lambda value, lang: translate_text(value, lang,"front-matter"),
    
    # 使用固定的替换规则
    "categories": lambda value, lang: front_matter_replace(value, lang),
    "tags": lambda value, lang: front_matter_replace(value, lang),
    
    # 未添加的字段将默认不翻译
}

# 固定字段替换规则。文章中一些固定的字段，不需要每篇都进行翻译，且翻译结果可能不一致，所以直接替换掉。
replace_rules = [
    {
        # 版权信息手动翻译
        "orginal_text": "> 原文地址：<https://wiki-power.com/>",
        "replaced_text": {
            "en": "> Original: <https://wiki-power.com/>",
            "es": "> Dirección original del artículo: <https://wiki-power.com/>",
            "ar": "> عنوان النص: <https://wiki-power.com/>",
            "ja": "> 原文のアドレス：<https://wiki-power.com/>",
            "ko": "> 원문 주소：<https://wiki-power.com/>"
        }
    },
    {
        # 版权信息手动翻译
        "orginal_text": "> 本篇文章受 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by/4.0/deed.zh) 协议保护，转载请注明出处。",
        "replaced_text": {
            "en": "> This post is protected by [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by/4.0/deed.en) agreement, should be reproduced with attribution.",
            "es": "> Este artículo está protegido por la licencia [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by/4.0/deed.zh). Si desea reproducirlo, por favor indique la fuente.",
            "ar": "> يتم حماية هذا المقال بموجب اتفاقية [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by/4.0/deed.zh)، يُرجى ذكر المصدر عند إعادة النشر.",
            "ja": "> この記事は [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja) ライセンスで保護されています。転載の際は出典を明記してください。",
            "ko": "> 이 글은 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by/4.0/deed.ko) 라이선스로 보호됩니다. 출처를 명시하여 재게시해 주세요."
        }
    },
    {
        # 文章中的站内链接，跳转为当前相同语言的网页
        "orginal_text": "](https://wiki-power.com/",
        "replaced_text": {
            "en": "](https://wiki-power.com/en/",
            "es": "](https://wiki-power.com/es/",
            "ar": "](https://wiki-power.com/ar/",
            "ja": "](https://wiki-power.com/ja/",
            "ko": "](https://wiki-power.com/ko/"
        }
    }
    # {
    #    # 不同语言可使用不同图床
    #    "orginal_text": "![](https://wiki-media-1253965369.cos.ap-guangzhou.myqcloud.com/",
    #    "replaced_en": "![](https://f004.backblazeb2.com/file/wiki-media/",
    #    "replaced_es": "![](https://f004.backblazeb2.com/file/wiki-media/",
    #    "replaced_ar": "![](https://f004.backblazeb2.com/file/wiki-media/",
    # },
]

# Front Matter 固定字段替换规则。
front_matter_replace_rules = [
    {
        "orginal_text": "类别 1",
        "replaced_text": {
            "en": "Categories 1",
            "es": "Categorías 1",
            "ar": "الفئة 1",
            "ja": "カテゴリー 1",
            "ko": "카테고리 1"
        }
    },
    {
        "orginal_text": "类别 2",
        "replaced_text": {
            "en": "Categories 2",
            "es": "Categorías 2",
            "ar": "الفئة 2",
            "ja": "カテゴリー 2",
            "ko": "카테고리 2"
        }
    },
    {
        "orginal_text": "标签 1",
        "replaced_text": {
            "en": "Tags 1",
            "es": "Etiquetas 1",
            "ar": "بطاقة 1",
            "ja": "タグ 1",
            "ko": "태그 1"
        }
    },
    {
        "orginal_text": "标签 2",
        "replaced_text": {
            "en": "Tags 2",
            "es": "Etiquetas 2",
            "ar": "بطاقة 2",
            "ja": "タグ 2",
            "ko": "태그 2"
        }
    },
]

##############################

# 对 Front Matter 使用固定规则替换的函数
def front_matter_replace(value, lang):
    for index in range(len(value)):
        element = value[index]
        # print(f"element[{index}] = {element}")
        for replacement in front_matter_replace_rules:
            if replacement["orginal_text"] in element:
                # 使用 replace 函数逐个替换
                element = element.replace(
                    replacement["orginal_text"], replacement["replaced_text"][lang])
        value[index] = element
        # print(f"element[{index}] = {element}")
    return value

# 定义调用 ChatGPT API 翻译的函数
def translate_text(text, lang, type):
    target_lang = {
        "en": "English",
        "es": "Spanish",
        "ar": "Arabic",
        "ja": "Japanese",  # 添加日语
        "ko": "Korean"     # 添加韩语
    }[lang]
    
    # Front Matter 与正文内容使用不同的 prompt 翻译
    # 翻译 Front Matter。
    if type == "front-matter":
        completion = client.chat.completions.create(
            # todo syj 替换 Model
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional translation engine, please translate the text into a colloquial, professional, elegant and fluent content, without the style of machine translation. You must only translate the text content, never interpret it."},
                {"role": "user", "content": f"Translate into {target_lang}:\n\n{text}\n"},
            ],
        )  
    # 翻译正文
    elif type== "main-body":
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional translation engine, please translate the text into a colloquial, professional, elegant and fluent content, without the style of machine translation. You must maintain the original markdown format. You must not translate the `[to_be_replace[x]]` field.You must only translate the text content, never interpret it."},
                {"role": "user", "content": f"Translate into {target_lang}:\n\n{text}\n"},
            ],
        )

    # 获取翻译结果
    output_text = completion.choices[0].message.content
    return output_text

# Front Matter 处理规则
def translate_front_matter(front_matter, lang):
    translated_front_matter = {}
    for key, value in front_matter.items():
        if key in front_matter_translation_rules:
            processed_value = front_matter_translation_rules[key](value, lang)
        else:
            # 如果在规则列表内，则不做任何翻译或替换操作
            processed_value = value
        translated_front_matter[key] = processed_value
        # print(key, ":", processed_value)
    return translated_front_matter

# 定义文章拆分函数
def split_text(text, max_length):
    # 根据段落拆分文章
    paragraphs = text.split("\n\n")
    output_paragraphs = []
    current_paragraph = ""

    for paragraph in paragraphs:
        if len(current_paragraph) + len(paragraph) + 2 <= max_length:
            # 如果当前段落加上新段落的长度不超过最大长度，就将它们合并
            if current_paragraph:
                current_paragraph += "\n\n"
            current_paragraph += paragraph
        else:
            # 否则将当前段落添加到输出列表中，并重新开始一个新段落
            output_paragraphs.append(current_paragraph)
            current_paragraph = paragraph

    # 将最后一个段落添加到输出列表中
    if current_paragraph:
        output_paragraphs.append(current_paragraph)

    # 将输出段落合并为字符串
    output_text = "\n\n".join(output_paragraphs)

    return output_text

# 定义翻译文件的函数
def translate_file(input_file, relative_path, lang):
    print(f"Translating into {lang}: {relative_path}")
    sys.stdout.flush()

    # 定义输出文件
    if lang in dir_translated:
        output_dir = os.path.join(dir_translated[lang], os.path.dirname(relative_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_file = os.path.join(output_dir, os.path.basename(relative_path))

    # 读取输入文件内容
    with open(input_file, "r", encoding="utf-8") as f:
        input_text = f.read()

    # 创建一个字典来存储占位词和对应的替换文本
    placeholder_dict = {}

    # 使用 for 循环应用替换规则，并将匹配的文本替换为占位词
    for i, rule in enumerate(replace_rules):
        find_text = rule["orginal_text"]
        replace_with = rule["replaced_text"][lang]
        placeholder = f"[to_be_replace[{i + 1}]]"
        input_text = input_text.replace(find_text, placeholder)
        placeholder_dict[placeholder] = replace_with

    # 删除译文中指示强制翻译的 marker
    input_text = input_text.replace(marker_force_translate, "")

    # 删除其他出英文外其他语言译文中的 marker_written_in_en
    if lang != "en":
        input_text = input_text.replace(marker_written_in_en, "")

    # 使用正则表达式来匹配 Front Matter
    front_matter_match = re.search(r'---\n(.*?)\n---', input_text, re.DOTALL)
    if front_matter_match:
        front_matter_text = front_matter_match.group(1)
        # 使用PyYAML加载YAML格式的数据
        front_matter_data = yaml.safe_load(front_matter_text)

        # 按照前文的规则对 Front Matter 进行翻译
        front_matter_data = translate_front_matter(front_matter_data, lang)

        # 将处理完的数据转换回 YAML
        front_matter_text_processed = yaml.dump(
            front_matter_data, allow_unicode=True, default_style=None, sort_keys=False)

        # 暂时删除未处理的 Front Matter
        input_text = input_text.replace(
            "---\n"+front_matter_text+"\n---\n", "")
    else:
        # print("没有找到front matter，不进行处理。")
        pass

    # print(input_text) # debug 用，看看输入的是什么

    # 拆分文章
    paragraphs = input_text.split("\n\n")
    input_text = ""
    output_paragraphs = []
    current_paragraph = ""

    for paragraph in paragraphs:
        if len(current_paragraph) + len(paragraph) + 2 <= max_length:
            # 如果当前段落加上新段落的长度不超过最大长度，就将它们合并
            if current_paragraph:
                current_paragraph += "\n\n"
            current_paragraph += paragraph
        else:
            # 否则翻译当前段落，并将翻译结果添加到输出列表中
            output_paragraphs.append(translate_text(current_paragraph, lang, "main-body"))
            current_paragraph = paragraph

    # 处理最后一个段落
    if current_paragraph:
        if len(current_paragraph) + len(input_text) <= max_length:
            # 如果当前段落加上之前的文本长度不超过最大长度，就将它们合并
            input_text += "\n\n" + current_paragraph
        else:
            # 否则翻译当前段落，并将翻译结果添加到输出列表中
            output_paragraphs.append(translate_text(current_paragraph, lang,"main-body"))

    # 如果还有未翻译的文本，就将它们添加到输出列表中
    if input_text:
        output_paragraphs.append(translate_text(input_text, lang,"main-body"))

    # 将输出段落合并为字符串
    output_text = "\n\n".join(output_paragraphs)

    if front_matter_match:
        # 加入 Front Matter
        output_text = "---\n" + front_matter_text_processed + "---\n\n" + output_text

    # 最后，将占位词替换为对应的替换文本
    for placeholder, replacement in placeholder_dict.items():
        output_text = output_text.replace(placeholder, replacement)

    # 写入输出文件
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output_text)

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='自动翻译 Markdown 文件')
    parser.add_argument('source', help='源语言代码 (例如: zh)')
    parser.add_argument('target', nargs='+', help='目标语言代码列表 (例如: ja ko en)')
    parser.add_argument('--dir', default=DEFAULT_DIR_TO_TRANSLATE, help='要翻译的目录路径')
    parser.add_argument('--exclude', nargs='+', default=DEFAULT_EXCLUDE_LIST, help='要排除的文件列表')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 验证源语言
    if args.source not in ["zh"]:
        print(f"错误：不支持的源语言 '{args.source}'")
        sys.exit(1)
    
    # 验证目标语言
    invalid_langs = [lang for lang in args.target if lang not in SUPPORTED_LANGUAGES]
    if invalid_langs:
        print(f"错误：不支持的目标语言 {invalid_langs}")
        print(f"支持的目标语言: {', '.join(SUPPORTED_LANGUAGES.keys())}")
        sys.exit(1)
    
    # 设置工作目录和排除列表
    dir_to_translate = args.dir
    exclude_list = args.exclude
    processed_list = DEFAULT_PROCESSED_LIST
    
    try:
        # 创建一个外部列表文件，存放已处理的 Markdown 文件名列表
        if not os.path.exists(processed_list):
            with open(processed_list, "w", encoding="utf-8") as f:
                print("processed_list created")
                sys.stdout.flush()

        # 读取已处理的文件列表
        with open(processed_list, "r", encoding="utf-8") as f:
            processed_list_content = f.read().splitlines()

        # 使用 os.walk 递归遍历目录
        for root, dirs, files in os.walk(dir_to_translate):
            # 按文件名称顺序排序
            sorted_files = sorted(files)
            
            for filename in sorted_files:
                if filename.endswith(".md"):
                    # 获取相对路径
                    relative_path = os.path.relpath(os.path.join(root, filename), dir_to_translate)
                    input_file = os.path.join(root, filename)
                    # print("relative_path: ", relative_path)
                    # print("input_file: ", input_file)

                    # 读取 Markdown 文件的内容
                    with open(input_file, "r", encoding="utf-8") as f:
                        md_content = f.read()

                    if marker_force_translate in md_content:  # 如果有强制翻译的标识，则执行这部分的代码
                        if marker_written_in_en in md_content:  # 翻译为除英文之外的语言
                            print("Pass the en-en translation: ", relative_path)
                            sys.stdout.flush()
                            for lang in args.target:
                                if lang != "en":
                                    translate_file(input_file, relative_path, lang)
                        else:  # 翻译为所有语言
                            for lang in args.target:
                                translate_file(input_file, relative_path, lang)
                    elif filename in exclude_list:  # 不进行翻译
                        print(f"Pass the post in exclude_list: {relative_path}")
                        sys.stdout.flush()
                    elif relative_path in processed_list_content:  # 不进行翻译
                        print(f"Pass the post in processed_list: {relative_path}")
                        sys.stdout.flush()
                    elif marker_written_in_en in md_content:  # 翻译为除英文之外的语言
                        print(f"Pass the en-en translation: {relative_path}")
                        sys.stdout.flush()
                        for lang in args.target:
                            if lang != "en":
                                translate_file(input_file, relative_path, lang)
                    else:  # 翻译为所有语言
                        for lang in args.target:
                            translate_file(input_file, relative_path, lang)

                    # 将处理完成的文件名加到列表，下次跳过不处理
                    if relative_path not in processed_list_content:
                        print(f"Added into processed_list: {relative_path}")
                        with open(processed_list, "a", encoding="utf-8") as f:
                            f.write(f"{relative_path}\n")

                    # 强制将缓冲区中的数据刷新到终端中，使用 GitHub Action 时方便实时查看过程
                    sys.stdout.flush()

        # 所有任务完成的提示
        print("Congratulations! All files processed done.")
        sys.stdout.flush()

    except Exception as e:
        # 捕获异常并输出错误信息
        print(f"An error has occurred: {e}")
        sys.stdout.flush()
        raise SystemExit(1)

if __name__ == "__main__":
    main()