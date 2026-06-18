---
name: curl-to-test
inclusion: manual
---

# cURL 转接口自动化测试 Skill

## 用途
将 cURL 命令一键转换为完整的接口自动化测试用例，自动生成测试数据文件和测试代码，并可选择执行测试。

## 输入
用户需要提供：
1. **cURL 命令**（必填）：完整的 curl 命令字符串（支持从浏览器开发者工具复制）
2. **自定义接口名称**（选填）：用于文件命名，默认从 URL 路径自动提取
3. **是否执行测试**（选填）：默认执行，可指定仅生成不执行

## 输出
- `testdata/{api_name}.yaml` — 测试数据文件
- `testcases/test_{api_name}.py` — pytest 测试用例文件
- `reports/report_{timestamp}.txt` — 测试报告（执行时）
- `reports/result_{timestamp}.xml` — JUnit XML 结果（执行时）
- 控制台输出测试结果表格

## 执行流程

### Step 1: 解析 cURL 命令
解析 curl 命令，提取以下信息：
- HTTP 方法（GET/POST/PUT/PATCH/DELETE）
- 请求 URL
- 请求头（过滤浏览器自动添加的无关头）
- Cookie
- 请求体（支持 JSON）

支持的 curl 参数：
- `--location` / `-L`：跟随重定向
- `--header` / `-H`：请求头
- `--data` / `--data-raw` / `--data-binary` / `-d`：请求体
- `--request` / `-X`：HTTP 方法
- `--cookie` / `-b`：Cookie
- `--compressed`、`-k`、`--insecure`：忽略

### Step 2: 自动生成测试用例
根据请求信息自动生成多组测试用例：

**正向场景：**
- 正向场景-全参数有效（使用原始参数）
- 正向场景-仅必填字段（保留前3个核心字段）
- 业务变体（修改部分字段为合法但不同的值）

**异常场景：**
- 异常场景-缺少必填字段（逐个移除前 3 个字段）

**类型转换测试：**
- 类型转换测试-传入字符串（对数值字段传入字符串）

**空值测试：**
- 空值测试-请求体为null
- 空值测试-字段为null（将第一个字段设为null）
- 空值测试-空对象（{}）

**边界测试：**
- 边界测试-零值
- 边界测试-负数
- 边界测试-极大值

**复杂类型测试：**
- 复杂类型测试-传入字符串（对列表/字典字段传入字符串）
- 复杂类型测试-非数字字符串

**安全测试用例（仅 POST/PUT/PATCH 且有 JSON body）：**
- 【安全测试】SQL注入-盲注（布尔盲注、时间盲注、报错注入、单引号闭合、注释符截断）
- 【安全测试】水平越权（使用其他用户ID访问）
- 【安全测试】未授权访问-无token或cookie访问
- 【安全测试】XSS攻击（script标签、事件处理器、编码绕过）
- 【安全测试】Header注入-X-Forwarded-For伪造IP
- 【安全测试】Header注入-User-Agent恶意工具检测
- 【安全测试】批量遍历（连续ID访问）
- 【安全测试】参数类型（数组代替字符串、对象代替字符串、布尔值代替字符串）
- 【安全测试】参数边界（超长字符串、特殊字符组合、空字符串）
- UNION 注入（列数探测、信息泄露）
- 命令注入（管道符、反引号、$() 语法）
- 边界值（超长字符串 1024/10000 字符）
- 特殊字符（中文、特殊符号、emoji）

### Step 3: 生成测试文件
1. 生成 YAML 数据文件到 `testdata/` 目录
2. 生成 pytest 测试代码到 `testcases/` 目录
3. 测试代码使用数据驱动方式（`@pytest.mark.parametrize`）
4. 包含响应时间检测用例（≤5s）

### Step 4: 执行测试（可选）
1. 使用 pytest 执行生成的测试文件
2. 生成 txt 报告和 JUnit XML 结果
3. 解析执行结果，输出测试结果表格
4. 表格包含：接口名称、用例标题、请求数据、HTTP状态码、业务code、响应消息、执行结果、返回体

## 使用方法

### 方式一：命令行直接传入 curl
```bash
cd /Users/mac/AI/api-automation
python curl_to_test.py "curl --location 'https://api.example.com/v1/users' --header 'Content-Type: application/json' --data '{\"name\": \"test\"}'"
```

### 方式二：从标准输入读取（适合多行 curl）
```bash
cd /Users/mac/AI/api-automation
python curl_to_test.py --stdin
```

### 方式三：仅生成用例不执行
```bash
cd /Users/mac/AI/api-automation
python curl_to_test.py --no-run "curl ..."
```

### 方式四：自定义接口名称
```bash
cd /Users/mac/AI/api-automation
python curl_to_test.py --name my_api "curl ..."
```

## 项目结构依赖
此脚本位于 `/Users/mac/AI/api-automation/curl_to_test.py`，依赖以下项目结构：

```
api-automation/
├── common/
│   ├── assertions.py    # 断言工具
│   ├── data_loader.py   # 数据加载
│   ├── http_client.py   # HTTP 客户端
│   └── logger.py        # 日志配置
├── config/
│   └── settings.py      # 配置管理
├── testcases/           # 生成的测试代码存放目录
├── testdata/            # 生成的测试数据存放目录
├── reports/             # 测试报告存放目录
├── logs/                # 日志文件目录
├── conftest.py          # pytest fixtures
├── pytest.ini           # pytest 配置
└── curl_to_test.py      # 本脚本
```

## 核心脚本路径
#[[file:api-automation/curl_to_test.py]]

## 注意事项
- curl 命令支持多行（反斜杠续行），脚本会自动处理
- 自动过滤浏览器复制时带入的无关请求头（User-Agent、Accept 等）
- Cookie 会从 Header 中的 Cookie 字段和 `-b` 参数中解析
- 生成的测试用例会覆盖同名文件，注意备份已修改的用例
- 安全测试用例的 expected status_code 默认为 200，实际项目中需根据接口行为调整
- 需要安装依赖：`pip install -r requirements.txt`（包含 pytest、pyyaml、requests 等）
