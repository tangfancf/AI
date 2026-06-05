---
name: Word文档转XMind思维导图
inclusion: manual
---

# Word文档转XMind思维导图 Skill

## 用途
将 Word 文档（.docx）转换为 XMind 兼容的 OPML 文件，支持段落和表格内容的提取，生成后可直接导入 XMind 使用。

## 输入
用户需要提供：
1. **Word文档路径**（必填）：.docx 文件的绝对路径
2. **输出文件路径**（选填）：生成的 .opml 文件保存路径，默认保存到用户桌面 `/Users/mac/Desktop/`，文件名与源文档相同（扩展名改为 .opml）
3. **OPML标题**（选填）：自定义思维导图中心主题名称，默认使用输出文件名（不含扩展名）

## 输出
生成一个 `.opml` 格式的思维导图文件，可直接导入 XMind。

## 转换规则

### 段落处理
- 文档第一个非空段落被视为主标题，跳过不输出（XMind 导入时会自动用文件名作为中心主题）
- 后续非空段落作为一级节点平铺输出
- 空段落自动忽略

### 表格处理
- 每个表格生成一个父节点，文本为 `表格 (N行)`
- 表格中每一行作为该父节点的子节点
- 行内各单元格用 ` | ` 分隔
- 全空行自动过滤

### XML安全
- 所有文本内容会进行 XML 特殊字符转义（`&`、`<`、`>`、`"`）

## 执行流程

### Step 1: 确认输入参数
1. 确认 Word 文档路径存在且可读
2. 确定输出路径（用户指定或默认桌面）
3. 确定 OPML 标题（用户指定或使用文件名）

### Step 2: 执行转换
运行脚本：
```bash
cd /Users/mac/AI/xmind
python xmindfromdocx.py
```

或在代码中直接调用：
```python
from xmindfromdocx import generate_opml_from_docx

generate_opml_from_docx(
    docx_path='/path/to/input.docx',
    output_path='/Users/mac/Desktop/output.opml',
    opml_title='可选标题'  # 不传则使用文件名
)
```

### Step 3: 输出结果
告知用户：
- OPML 文件保存路径
- 可通过 XMind 的"文件 → 导入 → OPML"功能导入

## 核心脚本路径
#[[file:xmind/xmindfromdocx.py]]

## 依赖
- `python-docx`：解析 Word 文档
- Python 标准库：`html`、`os`

安装依赖：
```bash
pip install python-docx
```

## 示例交互

用户输入：
```
帮我把这个Word文档转成XMind思维导图：
/Users/mac/Downloads/需求文档-v1.0.docx
```

输出：
```
OPML文件已生成: /Users/mac/Desktop/需求文档-v1.0.opml
✅ 可通过 XMind 的「文件 → 导入 → OPML」功能导入使用
```

## 注意事项
- 仅支持 .docx 格式（不支持旧版 .doc）
- 文档按段落和表格的出现顺序提取，不支持标题层级嵌套（平铺结构）
- 如果需要层级嵌套结构，建议先将文档转为 Markdown 格式，再使用 `xmindfrommarkdown.py` 转换
- XMind 导入 OPML 时会自动将 `<title>` 作为中心主题
