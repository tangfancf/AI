import html
import os
import re


def escape_xml(text):
    """
    转义XML特殊字符
    """
    if not isinstance(text, str):
        text = str(text)
    escaped = html.escape(text)
    escaped = escaped.replace('"', '&quot;')
    return escaped


def unescape_markdown(text):
    """
    去除Markdown中的反斜杠转义字符。
    例如: SCRM\-触达 -> SCRM-触达, v1\.5 -> v1.5
    """
    # 去除反斜杠转义: \X -> X (X为被转义的标点符号)
    return re.sub(r'\\([\\`*_{}\[\]()#+\-.!|~>])', r'\1', text)


def parse_markdown(md_path):
    """
    解析Markdown文件，返回结构化的内容列表。
    每个元素为 dict：
      - type: 'heading' | 'paragraph' | 'table'
      - level: 标题级别 (仅 heading 有)
      - text: 文本内容 (heading / paragraph)
      - rows: 二维列表 (仅 table 有)
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 空行跳过
        if not stripped:
            i += 1
            continue

        # 判断是否为标题 (# 开头)
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if heading_match:
            level = len(heading_match.group(1))
            text = unescape_markdown(heading_match.group(2).strip())
            blocks.append({'type': 'heading', 'level': level, 'text': text})
            i += 1
            continue

        # 判断是否为表格 (含有 | 的行，且下一行是分隔行 |---|)
        if '|' in stripped and i + 1 < len(lines):
            next_stripped = lines[i + 1].strip()
            # 表格分隔行: 类似 |---|---| 或 | --- | --- |
            if re.match(r'^\|?[\s\-:|]+\|[\s\-:|]*$', next_stripped):
                # 这是一个表格，解析所有表格行
                table_rows = []
                # 解析表头
                header_cells = parse_table_row(stripped)
                if header_cells:
                    table_rows.append(header_cells)
                i += 2  # 跳过表头和分隔行

                # 解析表格数据行
                while i < len(lines):
                    row_line = lines[i].strip()
                    if not row_line or '|' not in row_line:
                        break
                    cells = parse_table_row(row_line)
                    if cells:
                        table_rows.append(cells)
                    i += 1

                if table_rows:
                    blocks.append({'type': 'table', 'rows': table_rows})
                continue

        # 普通段落（非空非标题非表格）
        # 收集连续的非空行作为一个段落
        para_lines = []
        while i < len(lines):
            curr = lines[i].strip()
            if not curr:
                break
            # 如果遇到标题或表格，停止
            if re.match(r'^#{1,6}\s+', curr):
                break
            if '|' in curr and i + 1 < len(lines) and re.match(r'^\|?[\s\-:|]+\|[\s\-:|]*$', lines[i + 1].strip()):
                break
            para_lines.append(curr)
            i += 1

        if para_lines:
            text = unescape_markdown(' '.join(para_lines))
            blocks.append({'type': 'paragraph', 'text': text})

    return blocks


def parse_table_row(line):
    """
    解析Markdown表格的一行，返回单元格列表
    """
    # 去除首尾的 |
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]
    cells = [cell.strip() for cell in line.split('|')]
    return cells


def generate_opml_from_markdown(md_path, output_path, opml_title=None):
    """
    从Markdown文件生成XMind兼容的OPML文件。
    支持：标题层级结构、普通段落、表格数据。
    标题按层级嵌套，非标题内容挂在最近的上级标题下。
    """
    # 1. 读取并解析Markdown
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"无法读取文件: {md_path}")

    blocks = parse_markdown(md_path)

    # 2. 确定OPML标题
    if opml_title is not None:
        main_title = opml_title
    else:
        file_name_without_ext = os.path.splitext(os.path.basename(output_path))[0]
        main_title = file_name_without_ext

    # 3. 判断是否需要跳过第一个一级标题
    # XMind 导入 OPML 时会自动用文件名作为中心主题，
    # 所以不需要在 body 里再包一层同名的根 outline 节点。
    # 如果 Markdown 第一个 block 是一级标题，跳过它（XMind 会自动生成）。
    start_index = 0
    if blocks and blocks[0]['type'] == 'heading' and blocks[0]['level'] == 1:
        start_index = 1

    # 4. 用栈结构构建层级化的OPML
    opml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<opml version="2.0">',
        '<head>',
        f'    <title>{escape_xml(main_title)}</title>',
        '</head>',
        '<body>',
    ]

    # 使用栈来管理层级嵌套
    # stack 记录当前打开的 outline 节点的 level
    stack = []  # 存储 heading_level
    base_indent = '    '  # body 下第一层缩进

    def current_indent():
        return base_indent * (len(stack) + 1)

    def close_to_level(target_level):
        """关闭栈中所有 level >= target_level 的节点"""
        while stack and stack[-1] >= target_level:
            stack.pop()
            opml_lines.append(f'{base_indent * (len(stack) + 1)}</outline>')

    for block in blocks[start_index:]:
        if block['type'] == 'heading':
            level = block['level']
            text = block['text']

            # 关闭所有 level >= 当前 heading level 的节点
            close_to_level(level)

            # 打开新的 heading 节点
            indent = current_indent()
            opml_lines.append(f'{indent}<outline text="{escape_xml(text)}">')
            stack.append(level)

        elif block['type'] == 'paragraph':
            indent = current_indent()
            opml_lines.append(f'{indent}<outline text="{escape_xml(block["text"])}" />')

        elif block['type'] == 'table':
            rows = block['rows']
            indent = current_indent()
            child_indent = indent + base_indent

            table_node_text = escape_xml(f"表格 ({len(rows)}行)")
            opml_lines.append(f'{indent}<outline text="{table_node_text}">')

            for row_cells in rows:
                row_content = " | ".join([escape_xml(cell) for cell in row_cells])
                opml_lines.append(f'{child_indent}<outline text="{row_content}" />')

            opml_lines.append(f'{indent}</outline>')

    # 关闭所有剩余的节点
    while stack:
        stack.pop()
        opml_lines.append(f'{base_indent * (len(stack) + 1)}</outline>')

    opml_lines.append('</body>')
    opml_lines.append('</opml>')

    # 4. 写入文件
    opml_content = "\n".join(opml_lines)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(opml_content)

    print(f'OPML文件已生成: {output_path}')
    return True


# 使用示例
if __name__ == "__main__":
    # 请替换为你的实际路径
    md_file = '/Users/mac/Downloads/SCRM-触达业务-v1.5.7.6 人工外呼拦截：他人跟进客户 + 销售黑名单.md'
    opml_file = '/Users/mac/Desktop/SCRM-触达业务-v1.5.7.6 人工外呼拦截：他人跟进客户 + 销售黑名单.opml'

    try:
        success = generate_opml_from_markdown(md_file, opml_file)
        if success:
            print("✅ OPML文件生成成功")
            print("📊 可以尝试导入XMind")
    except FileNotFoundError as e:
        print(f"❌ 找不到Markdown文件: {e}")
    except Exception as e:
        import traceback

        print(f"❌ 生成过程中出错: {str(e)}")
        traceback.print_exc()
