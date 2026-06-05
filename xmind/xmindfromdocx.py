import docx
import html
import os
from docx.document import Document as _Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph


def escape_xml(text):
    """
    转义XML特殊字符
    """
    if not isinstance(text, str):
        text = str(text)
    # html.escape 处理 &, <, >
    escaped = html.escape(text)
    # 额外处理双引号，防止破坏 XML 属性结构
    escaped = escaped.replace('"', '&quot;')
    return escaped


def extract_table_data(table):
    """
    从 docx Table 对象中提取数据，返回二维列表
    """
    table_data = []
    for row in table.rows:
        row_data = []
        for cell in row.cells:
            # 去除首尾空白
            cell_text = cell.text.strip()
            row_data.append(cell_text)
        # 只有当行内不全为空时才添加该行，避免空行干扰
        if any(row_data):
            table_data.append(row_data)
    return table_data


def iter_block_items(parent):
    """
    按文档顺序 yield 段落和表格对象
    """
    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    else:
        raise ValueError("something's not right")

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def generate_opml_from_docx(docx_path, output_path, opml_title=None):
    """
    从Word文档生成XMind兼容的OPML文件
    支持按顺序提取：普通段落 + 表格数据
    """
    # 1. 读取Word文档
    try:
        doc = docx.Document(docx_path)
    except Exception as e:
        raise FileNotFoundError(f"无法读取文档: {e}")

    # 2. 确定OPML标题和主主题文本
    if opml_title is not None:
        main_title = opml_title
    else:
        file_name_without_ext = os.path.splitext(os.path.basename(output_path))[0]
        main_title = file_name_without_ext

    # 3. 构建OPML基础结构
    # XMind 导入 OPML 时会自动用文件名/title 作为中心主题，
    # 所以不需要在 body 里再包一层同名的根 outline 节点。
    opml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<opml version="2.0">',
        '<head>',
        f'    <title>{escape_xml(main_title)}</title>',
        '</head>',
        '<body>',
    ]

    # 4. 按顺序遍历文档内容 (段落和表格)
    # 跳过文档第一个非空段落（通常是标题，XMind 会自动生成）
    first_para_skipped = False

    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            para_text = block.text.strip()
            if not para_text:
                continue

            # 跳过文档第一个非空段落作为主标题
            if not first_para_skipped:
                first_para_skipped = True
                continue

            safe_text = escape_xml(para_text)
            opml_lines.append(f'    <outline text="{safe_text}" />')

        elif isinstance(block, Table):
            table_data = extract_table_data(block)
            if not table_data:
                continue

            # 为每个表格创建一个父节点
            table_node_text = escape_xml(f"表格 ({len(table_data)}行)")
            opml_lines.append(f'    <outline text="{table_node_text}">')

            # 将表格的每一行作为一个子节点
            for row_idx, row_cells in enumerate(table_data):
                row_content = " | ".join([escape_xml(cell) for cell in row_cells])
                opml_lines.append(f'        <outline text="{row_content}" />')

            opml_lines.append('    </outline>')

    # 5. 闭合标签
    opml_lines.append('</body>')
    opml_lines.append('</opml>')

    # 6. 写入文件
    opml_content = "\n".join(opml_lines)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(opml_content)

    print(f'OPML文件已生成: {output_path}')
    return True


# 使用示例
if __name__ == "__main__":
    # 请替换为你的实际路径
    docx_file = '/Users/mac/Downloads/后端、admin-SCRM-v1.4.9 公海掉落规则适用成员和调度计划成员支持按组织设置.docx'
    opml_file = '/Users/mac/Desktop/后端、admin-SCRM-v1.4.9 公海掉落规则适用成员和调度计划成员支持按组织设置.opml'

    try:
        success = generate_opml_from_docx(docx_file, opml_file)
        if success:
            print("✅ OPML文件生成成功")
            print("📊 可以尝试导入XMind")
    except FileNotFoundError:
        print("❌ 找不到Word文档，请检查路径")
    except Exception as e:
        import traceback

        print(f"❌ 生成过程中出错: {str(e)}")
        traceback.print_exc()
