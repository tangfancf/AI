---
name: Markdown转XMind思维导图
inclusion: manual
---

# Markdown转XMind思维导图 Skill

## 用途
将 Markdown 文件转换为 XMind 兼容的 OPML 文件，支持标题层级嵌套、段落和表格内容，生成后可直接导入 XMind 使用。

## 输入
用户需要提供：
1. **Markdown文件路径**（必填）：.md 文件的绝对路径
2. **输出文件路径**（选填）：生成的 .opml 文件保存路径，默认保存到用户桌面 `/Users/mac/Desktop/`，文件名与源文档相同（扩展名改为 .opml）
3. **OPML标题**（选填）：自定义思维导图中心主题名称，默认使用输出文件名（不含扩展名）

## 输出
生成一个 `.opml` 格式的思维导图文件，可直接导入 XMind。

## 转换规则

### 标题层级处理
- 一级标题（`#`）如果是文档首个 block，自动跳过（XMind 导入时会用文件名作为中心主题）
- 各级标题（`##` ~ `######`）按层级嵌套生成 outline 节点
- 低级标题自动嵌套在最近的上级标题下

### 段落处理
- 非空段落作为最近上级标题的子节点
- 连续非空行合并为一个段落节点

### 表格处理
- 自动识别 Markdown 表格（含 `|` 分隔符和 `---` 分隔行）
- 每个表格生成一个父节点，文本为 `表格 (N行)`
- 表格每行（含表头）作为子节点，单元格用 ` | ` 分隔

### Markdown 清理
- 自动去除反斜杠转义字符（如 `SCRM\-触达` → `SCRM-触达`）
- XML 特殊字符转义（`&`、`<`、`>`、`"`）

## 执行流程

### Step 1: 确认输入参数
1. 确认 Markdown 文件路径存在且可读
2. 确定输出路径（用户指定或默认桌面）
3. 确定 OPML 标题（用户指定或使用文件名）

### Step 2: 执行转换
运行脚本：
```bash
cd /Users/mac/AI/xmind
python xmindfrommarkdown.py
```

或在代码中直接调用：
```python
from xmindfrommarkdown import generate_opml_from_markdown

generate_opml_from_markdown(
    md_path='/path/to/input.md',
    output_path='/Users/mac/Desktop/output.opml',
    opml_title='可选标题'  # 不传则使用文件名
)
```

### Step 3: 输出结果
告知用户：
- OPML 文件保存路径
- 可通过 XMind 的"文件 → 导入 → OPML"功能导入

## 核心脚本路径
#[[file:xmind/xmindfrommarkdown.py]]

## 依赖
- Python 标准库：`html`、`os`、`re`（无需额外安装第三方库）

## 示例交互

用户输入：
```
帮我把这个Markdown文档转成XMind思维导图：
/Users/mac/Downloads/SCRM-触达业务-v1.5.7.md
```

输出：
```
OPML文件已生成: /Users/mac/Desktop/SCRM-触达业务-v1.5.7.opml
✅ 可通过 XMind 的「文件 → 导入 → OPML」功能导入使用
```

## 与 Word 转换的区别
| 特性 | Markdown转换 | Word转换 |
|------|-------------|----------|
| 标题层级 | ✅ 支持多级嵌套 | ❌ 平铺结构 |
| 表格 | ✅ 支持 | ✅ 支持 |
| 外部依赖 | 无 | python-docx |
| 适用场景 | 需求文档、技术文档 | Word格式文档 |

## 注意事项
- 支持 1~6 级标题嵌套
- 文档首个一级标题会被跳过（作为 XMind 中心主题）
- 标题层级关系通过栈结构维护，确保正确嵌套
- 非标题内容（段落、表格）挂载在最近的上级标题节点下
- 如果文档没有标题结构，所有内容将平铺在根层级
