# 接口自动化测试框架

基于 Python + Pytest + Requests 的可复用接口自动化测试框架。

## 项目结构

```
api-automation/
├── config/                  # 配置管理
│   ├── config.yaml         # 环境配置 (多环境支持)
│   └── settings.py         # 配置读取模块
├── common/                  # 公共模块
│   ├── http_client.py      # HTTP 客户端封装
│   ├── assertions.py       # 断言工具 (链式调用)
│   ├── data_loader.py      # 测试数据加载器
│   ├── logger.py           # 日志配置
│   └── utils.py            # 通用工具函数
├── testdata/                # 测试数据 (YAML/JSON)
│   ├── login.yaml          # 登录测试数据
│   └── user_crud.yaml      # 用户 CRUD 测试数据
├── testcases/               # 测试用例
│   ├── test_login.py       # 登录接口测试
│   ├── test_user_crud.py   # 用户 CRUD 测试
│   └── test_example_data_driven.py  # 数据驱动模板
├── logs/                    # 测试日志 (自动生成)
├── conftest.py             # Pytest 全局 fixtures
├── pytest.ini              # Pytest 配置
├── requirements.txt        # 依赖包
└── README.md               # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
cd api-automation
pip install -r requirements.txt
```

### 2. 配置环境

编辑 `config/config.yaml`，设置目标环境的 base_url 和认证信息。

### 3. 运行测试

```bash
# 运行所有测试
pytest

# 运行指定测试文件
pytest testcases/test_login.py

# 运行指定标记的测试
pytest -m smoke

# 生成 HTML 报告
pytest --html=report.html --self-contained-html

# 生成 Allure 报告
pytest --alluredir=allure-results
allure serve allure-results
```

## 核心特性

### 多环境切换

在 `config.yaml` 中配置多个环境，通过 `env.active` 切换：

```yaml
env:
  active: dev  # 切换为 test / prod
```

### 数据驱动

在 `testdata/` 目录编写 YAML 数据文件：

```yaml
test_cases:
  - case_id: "TC001"
    title: "正常场景"
    input:
      field1: "value1"
    expected:
      status_code: 200
      code: 0
```

### 链式断言

```python
from common.assertions import assert_response

assert_response(response) \
    .status_code(200) \
    .json_field("$.code", 0) \
    .json_field_exists("$.data.token") \
    .json_field_not_empty("$.data.list") \
    .json_list_length("$.data.list", min_len=1) \
    .response_time(3000)
```

### 变量传递

使用 `${variable}` 占位符在测试数据中引用动态值：

```python
from common.utils import replace_placeholders

context = {"user_id": 123, "token": "abc"}
data = {"id": "${user_id}"}
result = replace_placeholders(data, context)
# {"id": 123}
```

## 添加新接口测试

1. **创建测试数据**: `testdata/your_api.yaml`
2. **创建测试文件**: `testcases/test_your_api.py`
3. **编写用例**: 参考 `test_example_data_driven.py` 模板
4. **运行验证**: `pytest testcases/test_your_api.py -v`

## 报告

- **HTML 报告**: `pytest --html=report.html`
- **Allure 报告**: `pytest --alluredir=allure-results && allure serve allure-results`
- **日志文件**: 自动保存在 `logs/` 目录
