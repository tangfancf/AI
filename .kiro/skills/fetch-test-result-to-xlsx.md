---
name: 抓取测试执行结果到Excel
inclusion: manual
---

# 抓取测试执行结果到 Excel Skill

## 用途
从指定的测试执行结果页面（如 `https://page.yupaowang.com/apiTest/executeResult/{接口名}/`）抓取测试用例数据，提取"用例描述、测试数据、预期断言、实际响应"四个字段，并输出为格式化的 `.xlsx` 文件。其中"测试数据"和"实际响应"字段会自动转为 JSON 格式。

## 输入
用户需要提供：
1. **页面链接**（必填）：测试执行结果页面的完整 URL，格式如 `https://page.yupaowang.com/apiTest/executeResult/{接口名}/`

## 输出
生成一个 `.xlsx` 格式的文件，保存到用户桌面 `/Users/mac/Desktop/`。

文件命名格式：`{接口名}_测试执行结果.xlsx`

## Excel 字段说明
| 列 | 字段名 | 说明 | 格式要求 |
|----|--------|------|----------|
| A | 用例描述 | 测试用例的描述/标题 | 原始文本 |
| B | 测试数据 | 该用例使用的请求数据 | **转为 JSON 字符串** |
| C | 预期断言 | 该用例的预期结果/断言规则 | 原始文本 |
| D | 实际响应 | 接口实际返回的响应内容 | **转为 JSON 字符串** |

## 执行流程

### Step 1: 抓取页面数据
1. 使用 `web_fetch` 工具以 `rendered` 模式获取用户提供的链接内容（该页面为 JavaScript 渲染的单页应用，需使用 rendered 模式）
2. 如果页面内容不完整，尝试使用 `selective` 模式配合关键词搜索补充数据

### Step 2: 解析测试用例数据
从页面内容中提取每个测试用例的四个字段：
1. **用例描述**（description）：用例的标题或描述信息
2. **测试数据**（data）：用例的请求参数/数据
3. **预期断言**（assert_data）：期望的响应结果断言规则
4. **实际响应**（execution_result）：接口实际返回的完整响应

### Step 3: 数据格式转换
对提取的数据进行格式转换：
1. **测试数据**：如果是 YAML/字典格式，转为标准 JSON 字符串（`json.dumps(data, ensure_ascii=False, indent=2)`）
2. **实际响应**：如果是 YAML/字典格式，转为标准 JSON 字符串（`json.dumps(data, ensure_ascii=False, indent=2)`）
3. **用例描述** 和 **预期断言**：保持原始文本格式

### Step 4: 生成 Excel 文件
使用 Python + openpyxl 生成 xlsx 文件：

```python
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

wb = Workbook()
ws = wb.active
ws.title = "测试执行结果"

# 表头
headers = ["用例描述", "测试数据", "预期断言", "实际响应"]
ws.append(headers)

# 表头样式
header_font = Font(bold=True, color="FFFFFF", size=11)
header_fill = PatternFill(start_color="4A90D9", end_color="4A90D9", fill_type="solid")
thin_border = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)
for col_idx in range(1, len(headers) + 1):
    cell = ws.cell(row=1, column=col_idx)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = thin_border

# 填入数据行
for case in test_cases:
    description = case["description"]
    test_data = json.dumps(case["data"], ensure_ascii=False, indent=2) if isinstance(case["data"], (dict, list)) else str(case["data"])
    assert_data = str(case["assert_data"])
    actual_response = json.dumps(case["execution_result"], ensure_ascii=False, indent=2) if isinstance(case["execution_result"], (dict, list)) else str(case["execution_result"])
    ws.append([description, test_data, assert_data, actual_response])

# 设置列宽
col_widths = [40, 50, 40, 60]
for i, w in enumerate(col_widths, 1):
    ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w

# 设置数据行样式
for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(headers)):
    for cell in row:
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        cell.border = thin_border

# 冻结首行
ws.freeze_panes = "A2"

wb.save(output_path)
```

### Step 5: 输出结果
告知用户文件保存路径和用例总数。

## 数据解析规则

### 页面数据结构
页面中测试用例通常以如下结构呈现：

```yaml
# 每条用例包含以下信息:
description: "用例描述文本"
data:
  field1: value1
  field2: value2
assert_data:
  - equals: [status_code, 200]
  - equals: ["json.code", 0]
execution_result:
  status_code: 200
  json.code: 0
  json.message: "成功"
  json.data: {...}
```

### 转 JSON 规则
1. YAML 字典/列表 → JSON 字符串
2. 空对象 `{}` → `"{}"`
3. null → `"null"`
4. 纯字符串保持不变
5. 确保中文不被转义（`ensure_ascii=False`）
6. 使用缩进格式便于阅读（`indent=2`）

## 示例交互

用户输入：
```
链接：https://page.yupaowang.com/apiTest/executeResult/trade_v1_bankTransaction_pageQuery/
```

输出：
```
已从页面抓取 21 条测试用例数据
文件已保存到：/Users/mac/Desktop/trade_v1_bankTransaction_pageQuery_测试执行结果.xlsx
共导出 21 条用例，其中"测试数据"和"实际响应"已转为 JSON 格式
```

## 注意事项
- 页面使用 JavaScript 渲染，必须使用 `rendered` 模式抓取
- 如果页面数据量大导致截断，需分段抓取或使用 `selective` 模式定位具体内容
- "测试数据"为空对象 `{}` 时，JSON 输出为 `"{}"`
- "实际响应"中可能包含嵌套的 JSON 数据，需完整保留
- 预期断言可能是列表格式（多条断言规则），保持原始文本即可
- 生成的 xlsx 文件支持自动换行，方便查看较长的 JSON 内容
- 需要安装 openpyxl 依赖：`pip install openpyxl`
