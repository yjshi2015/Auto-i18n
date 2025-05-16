# -*- coding: utf-8 -*-
import os
import sys
import re
import yaml  # pip install PyYAML
import env
import argparse
import asyncio
import shutil
from typing import List, Dict, Any
from openai import AsyncOpenAI
from config import (
    SYSTEM_PROMPTS,
    MODEL_CONFIG,
    MAX_LENGTH,
    MAX_CONCURRENT_FILES,
    SUPPORTED_LANGUAGES,
    DEFAULT_DIR_TO_TRANSLATE,
    DEFAULT_EXCLUDE_LIST,
    DEFAULT_PROCESSED_LIST,
    DIR_TRANSLATED
)

# 设置 OpenAI API Key 和 API Base 参数，通过 env.py 传入
client = AsyncOpenAI(
    api_key=os.environ.get("CHATGPT_API_KEY"),
    base_url=os.environ.get("CHATGPT_API_BASE")
)

# Front Matter 处理规则
front_matter_translation_rules = {
    # 调用 ChatGPT 自动翻译
    "title": lambda value, lang: asyncio.create_task(translate_text(value, lang, "front-matter")),
    "description": lambda value, lang: asyncio.create_task(translate_text(value, lang, "front-matter")),
    
    # 使用固定的替换规则
    "categories": lambda value, lang: front_matter_replace(value, lang),
    "tags": lambda value, lang: front_matter_replace(value, lang),
    
    # 未添加的字段将默认不翻译
}

# 固定字段替换规则。文章中一些固定的字段，不需要每篇都进行翻译，且翻译结果可能不一致，所以直接替换掉。
# todo syj 增加固定替换的内容
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
    }
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
async def translate_text(text, lang, type):
    target_lang = SUPPORTED_LANGUAGES[lang]
    
    # Front Matter 与正文内容使用不同的 prompt 翻译
    completion = await client.chat.completions.create(
        model=MODEL_CONFIG[type],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPTS[type]},
            {"role": "user", "content": f"Translate into {target_lang}:\n\n{text}\n"},
        ],
        stream=False,
        temperature=1.3
    )

    # 获取翻译结果
    output_text = completion.choices[0].message.content
    return output_text

# Front Matter 处理规则
async def translate_front_matter(front_matter, lang):
    translated_front_matter = {}
    for key, value in front_matter.items():
        if key in front_matter_translation_rules:
            processed_value = front_matter_translation_rules[key](value, lang)
            if asyncio.iscoroutine(processed_value) or isinstance(processed_value, asyncio.Task):
                processed_value = await processed_value
        else:
            # 如果在规则列表内，则不做任何翻译或替换操作
            processed_value = value
        translated_front_matter[key] = processed_value
    return translated_front_matter

# 支持的图片文件扩展名
SUPPORTED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg']

# 支持的视频文件扩展名
SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm']

def is_image_file(filename: str) -> bool:
    """检查文件是否为图片文件"""
    return any(filename.lower().endswith(ext) for ext in SUPPORTED_IMAGE_EXTENSIONS)

def is_video_file(filename: str) -> bool:
    """检查文件是否为视频文件"""
    return any(filename.lower().endswith(ext) for ext in SUPPORTED_VIDEO_EXTENSIONS)

def is_media_file(filename: str) -> bool:
    """检查文件是否为媒体文件（图片或视频）"""
    return is_image_file(filename) or is_video_file(filename)

def copy_media_file(input_file: str, output_file: str) -> None:
    """拷贝图片文件到目标目录"""
    # 确保目标目录存在
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 拷贝文件
    shutil.copy2(input_file, output_file)

async def translate_file_async(input_file: str, relative_path: str, lang: str) -> None:
    """异步处理单个文件的翻译"""
    print(f"Translating into {lang}: {relative_path}")
    sys.stdout.flush()

    # 如果是媒体文件（图片或视频），只在目标语言目录下拷贝
    if is_media_file(input_file):
        output_dir = os.path.join(DIR_TRANSLATED[lang], os.path.dirname(relative_path))
        output_file = os.path.join(output_dir, os.path.basename(relative_path))
        copy_media_file(input_file, output_file)
        return

    # 定义输出文件
    if lang in DIR_TRANSLATED:
        output_dir = os.path.join(DIR_TRANSLATED[lang], os.path.dirname(relative_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        # 将输出文件扩展名改为 .txt
        output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(relative_path))[0] + '.txt')

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

    # 使用正则表达式来匹配 Front Matter
    front_matter_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', input_text, re.DOTALL)
    front_matter_text = ""
    if front_matter_match:
        front_matter_text = front_matter_match.group(1)
        # 使用PyYAML加载YAML格式的数据
        front_matter_data = yaml.safe_load(front_matter_text)

        # 按照前文的规则对 Front Matter 进行翻译
        front_matter_data = await translate_front_matter(front_matter_data, lang)

        # 将处理完的数据转换回 YAML
        front_matter_text_processed = yaml.dump(
            front_matter_data, allow_unicode=True, default_style=None, sort_keys=False)

        # 暂时删除未处理的 Front Matter
        input_text = input_text.replace(
            "---\n"+front_matter_text+"\n---\n", "")
    else:
        pass

    # 拆分文章
    paragraphs = input_text.split("\n\n")
    input_text = ""
    output_paragraphs = []
    current_paragraph = ""

    for paragraph in paragraphs:
        if len(current_paragraph) + len(paragraph) + 2 <= MAX_LENGTH:
            # 如果当前段落加上新段落的长度不超过最大长度，就将它们合并
            if current_paragraph:
                current_paragraph += "\n\n"
            current_paragraph += paragraph
        else:
            # 否则翻译当前段落，并将翻译结果添加到输出列表中
            translated_text = await translate_text(current_paragraph, lang, "main-body")
            output_paragraphs.append(translated_text)
            current_paragraph = paragraph

    # 处理最后一个段落
    if current_paragraph:
        if len(current_paragraph) + len(input_text) <= MAX_LENGTH:
            # 如果当前段落加上之前的文本长度不超过最大长度，就将它们合并
            input_text += "\n\n" + current_paragraph
        else:
            # 否则翻译当前段落，并将翻译结果添加到输出列表中
            translated_text = await translate_text(current_paragraph, lang, "main-body")
            output_paragraphs.append(translated_text)

    # 如果还有未翻译的文本，就将它们添加到输出列表中
    if input_text:
        translated_text = await translate_text(input_text, lang, "main-body")
        output_paragraphs.append(translated_text)

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
        
    # 在文件成功翻译完成后，将其添加到 processed_list
    # 先读取已处理的文件列表
    with open(DEFAULT_PROCESSED_LIST, "r", encoding="utf-8") as f:
        processed_list_content = f.read().splitlines()
    
    # 只有当文件不在列表中时才添加
    if relative_path not in processed_list_content:
        print(f"Added into processed_list: {relative_path}")
        with open(DEFAULT_PROCESSED_LIST, "a", encoding="utf-8") as f:
            f.write(f"{relative_path}\n")

async def process_files_async(files_to_translate: List[tuple], target_langs: List[str]) -> None:
    """并发处理多个文件"""
    tasks = []
    for input_file, relative_path in files_to_translate:
        for lang in target_langs:
            tasks.append(translate_file_async(input_file, relative_path, lang))
    
    # 使用信号量限制并发数
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_FILES)
    async def bounded_process(task):
        async with semaphore:
            return await task
    
    await asyncio.gather(*[bounded_process(task) for task in tasks])

async def main_async():
    try:
        # 创建命令行参数解析器
        parser = argparse.ArgumentParser(description='自动翻译 Markdown 文件')
        parser.add_argument('source', help='源语言代码 (例如: zh, en, ja)')
        parser.add_argument('target', nargs='+', help='目标语言代码列表 (例如: ja ko en)')
        parser.add_argument('--dir', default=DEFAULT_DIR_TO_TRANSLATE, help='要翻译的目录路径')
        parser.add_argument('--exclude', nargs='+', default=DEFAULT_EXCLUDE_LIST, help='要排除的文件列表')
        
        # 解析命令行参数
        args = parser.parse_args()
        
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

            # 收集需要翻译的文件
            files_to_translate = []
            for root, dirs, files in os.walk(dir_to_translate):
                # 按文件名称顺序排序
                sorted_files = sorted(files)
                
                for filename in sorted_files:
                    # 获取相对路径
                    relative_path = os.path.relpath(os.path.join(root, filename), dir_to_translate)
                    input_file = os.path.join(root, filename)

                    # 检查是否是以特定前缀开头的文件或目录
                    path_parts = relative_path.split(os.sep)
                    if any(part.startswith(('Course Info', 'Unit Info', 'Lesson Info')) for part in path_parts):
                        # print(f"Pass the file with special prefix: {relative_path}")
                        sys.stdout.flush()
                        continue

                    if filename in exclude_list:  # 不进行翻译
                        print(f"Pass the post in exclude_list: {relative_path}")
                        sys.stdout.flush()
                    elif relative_path in processed_list_content:  # 不进行翻译
                        print(f"Pass the post in processed_list: {relative_path}")
                        sys.stdout.flush()
                    elif filename.endswith(".md") or is_media_file(filename):  # 需要处理的文件
                        files_to_translate.append((input_file, relative_path))

            # print(f"files_to_translate: {files_to_translate}")
            # 并发处理文件
            await process_files_async(files_to_translate, args.target)

            # 所有任务完成的提示
            print("Congratulations! All files processed done.")
            sys.stdout.flush()

        except Exception as e:
            # 捕获异常并输出错误信息
            print(f"An error has occurred: {e}")
            sys.stdout.flush()
            raise SystemExit(1)

    except Exception as e:
        # 捕获异常并输出错误信息
        print(f"An error has occurred: {e}")
        sys.stdout.flush()
        raise SystemExit(1)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()