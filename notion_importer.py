import os
import re
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
ROOT_PAGE_ID = os.getenv("NOTION_ROOT_PAGE_ID")

if not NOTION_TOKEN or not ROOT_PAGE_ID:
    raise ValueError("请确保设置了 NOTION_TOKEN 和 NOTION_ROOT_PAGE_ID 环境变量")

# 验证页面 ID 格式
def validate_page_id(page_id):
    # 移除所有连字符并检查长度
    clean_id = page_id.replace("-", "")
    if len(clean_id) != 32:
        raise ValueError(f"无效的页面 ID 格式: {page_id}")
    return page_id

# 格式化页面 ID
def format_page_id(page_id):
    # 移除所有连字符
    clean_id = page_id.replace("-", "")
    # 添加连字符
    return f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"

try:
    ROOT_PAGE_ID = format_page_id(ROOT_PAGE_ID)
    validate_page_id(ROOT_PAGE_ID)
except ValueError as e:
    print(f"错误: {e}")
    print("请确保 NOTION_ROOT_PAGE_ID 是一个有效的 Notion 页面 ID")
    exit(1)

notion = Client(auth=NOTION_TOKEN)

# 验证集成访问权限
try:
    notion.pages.retrieve(page_id=ROOT_PAGE_ID)
except Exception as e:
    print(f"错误: 无法访问指定的 Notion 页面")
    print("请确保：")
    print("1. 页面 ID 是正确的")
    print("2. 你的集成已经被添加到该页面中")
    print("3. 集成有足够的权限")
    print(f"详细错误: {str(e)}")
    exit(1)

def split_content(content, max_length=2000):
    """将内容分割成不超过最大长度的块"""
    if len(content) <= max_length:
        return [content]
    
    blocks = []
    current_pos = 0
    while current_pos < len(content):
        # 找到合适的分割点（在最大长度限制内）
        end_pos = min(current_pos + max_length, len(content))
        if end_pos < len(content):
            # 尝试在最后一个换行符处分割
            last_newline = content.rfind('\n', current_pos, end_pos)
            if last_newline != -1:
                end_pos = last_newline + 1
        
        blocks.append(content[current_pos:end_pos])
        current_pos = end_pos
    
    return blocks

def create_notion_page(title, parent_id, content=None):
    children = []
    
    if content:
        # 将内容分割成多个块
        content_blocks = split_content(content)
        for block in content_blocks:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": block}
                        }
                    ]
                }
            })
    
    page = notion.pages.create(
        parent={"page_id": parent_id},
        properties={
            "title": [
                {
                    "type": "text",
                    "text": {"content": title}
                }
            ]
        },
        children=children
    )
    return page["id"]

def import_directory_to_notion(path, parent_page_id):
    for entry in os.listdir(path):
        full_path = os.path.join(path, entry)

        if os.path.isdir(full_path):
            sub_page_id = create_notion_page(entry, parent_page_id)
            import_directory_to_notion(full_path, sub_page_id)

        elif entry.endswith(".md"):
            with open(full_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            create_notion_page(entry.replace(".md", ""), parent_page_id, md_content)

if __name__ == "__main__":
    local_folder = "./testdir/docs/en/Private & Shared"  # 修改为你的 Markdown 解压目录路径
    import_directory_to_notion(local_folder, ROOT_PAGE_ID)
    print("✅ 导入完成！")