from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    category: str
    prompt: str
    source: str = ""
    validator: str = "function"
    hidden: str = ""
    required: tuple[str, ...] = ()
    allowed_files: tuple[str, ...] = ("src/target.py",)
    expected_tier: str = "balanced"
    read_only: bool = False
    extra_files: dict[str, str] = field(default_factory=dict)


def _function_case(case_id: str, category: str, prompt: str, source: str, hidden: str, tier: str) -> BenchmarkCase:
    return BenchmarkCase(case_id, category, prompt, source=source, hidden=hidden, expected_tier=tier)


CASES: list[BenchmarkCase] = [
    _function_case(
        "bugfix-01", "bugfix", "修复 src/target.py 中 clamp 的边界逻辑，只修改必要文件并运行验证。",
        "def clamp(value, low, high):\n    return min(low, max(high, value))\n",
        "from src.target import clamp\nassert clamp(5, 0, 10) == 5\nassert clamp(-2, 0, 10) == 0\nassert clamp(20, 0, 10) == 10\n", "balanced",
    ),
    _function_case(
        "bugfix-02", "bugfix", "修复 src/target.py 的 unique，使其去重时保持首次出现顺序。",
        "def unique(values):\n    return list(set(values))\n",
        "from src.target import unique\nassert unique([3, 1, 3, 2, 1]) == [3, 1, 2]\nassert unique([]) == []\n", "balanced",
    ),
    _function_case(
        "bugfix-03", "bugfix", "修复 src/target.py 的 parse_bool，只接受常见真假字符串，非法值抛出 ValueError。",
        "def parse_bool(value):\n    return bool(value)\n",
        "from src.target import parse_bool\nassert parse_bool('true') is True\nassert parse_bool('YES') is True\nassert parse_bool('0') is False\ntry:\n    parse_bool('maybe')\nexcept ValueError:\n    pass\nelse:\n    raise AssertionError('expected ValueError')\n", "balanced",
    ),
    _function_case(
        "bugfix-04", "bugfix", "修复 src/target.py 的 chunks：正常分块，并在 size 小于1时抛出 ValueError。",
        "def chunks(values, size):\n    return [values[i:i + size] for i in range(0, len(values), size)]\n",
        "from src.target import chunks\nassert chunks([1,2,3,4,5], 2) == [[1,2],[3,4],[5]]\ntry:\n    chunks([1], 0)\nexcept ValueError:\n    pass\nelse:\n    raise AssertionError('expected ValueError')\n", "balanced",
    ),
    _function_case(
        "bugfix-05", "bugfix", "修复 src/target.py 的 word_counts，使统计忽略大小写并跳过空白项。",
        "def word_counts(words):\n    return {word: words.count(word) for word in words}\n",
        "from src.target import word_counts\nassert word_counts(['A','a','', 'B']) == {'a': 2, 'b': 1}\n", "balanced",
    ),
    _function_case(
        "bugfix-06", "bugfix",
        "修复 src/target.py 的 safe_filename：将 / \\ : * ? \" < > | 每个字符替换为下划线；"
        "先去掉首尾空白，如果结果为空则返回 untitled。",
        "def safe_filename(value):\n    return value.replace(' ', '_')\n",
        "from src.target import safe_filename\nassert safe_filename('a/b:c?.txt') == 'a_b_c_.txt'\nassert safe_filename('   ') == 'untitled'\n", "balanced",
    ),
    _function_case(
        "feature-01", "feature", "在 src/target.py 实现 slugify(text)：小写、空白转连字符、移除其他标点并合并连字符。",
        "def slugify(text):\n    raise NotImplementedError\n",
        "from src.target import slugify\nassert slugify('Hello,  New World!') == 'hello-new-world'\nassert slugify('  A---B  ') == 'a-b'\n", "balanced",
    ),
    _function_case(
        "feature-02", "feature", "在 src/target.py 实现 paginate(values, page, size)，页码从1开始，非法页码或大小抛出 ValueError。",
        "def paginate(values, page, size):\n    raise NotImplementedError\n",
        "from src.target import paginate\nassert paginate([1,2,3,4,5], 2, 2) == [3,4]\nassert paginate([1], 2, 2) == []\nfor args in [([1],0,2),([1],1,0)]:\n    try:\n        paginate(*args)\n    except ValueError:\n        pass\n    else:\n        raise AssertionError('expected ValueError')\n", "balanced",
    ),
    _function_case(
        "feature-03", "feature", "在 src/target.py 实现 redact_email(text)，保留邮箱首字符和域名，其余用户名替换为星号。",
        "def redact_email(text):\n    raise NotImplementedError\n",
        "from src.target import redact_email\nassert redact_email('Contact alice@example.com now') == 'Contact a****@example.com now'\nassert redact_email('x@y.io') == 'x@y.io'\n", "balanced",
    ),
    _function_case(
        "feature-04", "feature", "在 src/target.py 实现 group_by(items, key)，按字典字段分组并保持输入顺序。",
        "def group_by(items, key):\n    raise NotImplementedError\n",
        "from src.target import group_by\nitems=[{'team':'a','id':1},{'team':'b','id':2},{'team':'a','id':3}]\nassert group_by(items,'team') == {'a':[items[0],items[2]],'b':[items[1]]}\n", "balanced",
    ),
    _function_case(
        "feature-05", "feature", "在 src/target.py 实现 parse_duration，支持纯秒数以及 10s、5m、2h，非法格式抛出 ValueError。",
        "def parse_duration(value):\n    raise NotImplementedError\n",
        "from src.target import parse_duration\nassert parse_duration('10') == 10\nassert parse_duration('5m') == 300\nassert parse_duration('2h') == 7200\ntry:\n    parse_duration('1d')\nexcept ValueError:\n    pass\nelse:\n    raise AssertionError('expected ValueError')\n", "balanced",
    ),
    _function_case(
        "feature-06", "feature", "在 src/target.py 实现 retry_delays(attempts, base=1)，返回指数退避序列，attempts 小于0时报错。",
        "def retry_delays(attempts, base=1):\n    raise NotImplementedError\n",
        "from src.target import retry_delays\nassert retry_delays(4) == [1,2,4,8]\nassert retry_delays(3, 0.5) == [0.5,1.0,2.0]\ntry:\n    retry_delays(-1)\nexcept ValueError:\n    pass\nelse:\n    raise AssertionError('expected ValueError')\n", "balanced",
    ),
    _function_case(
        "refactor-01", "refactor", "重构 src/target.py，把重复的小计计算提取为 _line_total，保持 invoice_total 行为不变。",
        "def invoice_total(lines):\n    total = 0\n    for line in lines:\n        total += line['price'] * line['qty']\n    tax = 0\n    for line in lines:\n        tax += line['price'] * line['qty'] * 0.1\n    return total + tax\n",
        "from src.target import invoice_total, _line_total\nassert _line_total({'price':3,'qty':2}) == 6\nassert invoice_total([{'price':10,'qty':2}]) == 22\n", "balanced",
    ),
    _function_case(
        "refactor-02", "refactor", "重构 src/target.py，用单一 normalize_name 辅助函数消除两个公开函数中的重复清洗逻辑。",
        "def display_name(value):\n    return ' '.join(value.strip().split()).title()\n\ndef greeting(value):\n    name = ' '.join(value.strip().split()).title()\n    return f'Hello, {name}'\n",
        "from src.target import display_name,greeting,normalize_name\nassert normalize_name('  aLi  ce ') == 'Ali Ce'\nassert display_name(' bob ') == 'Bob'\nassert greeting(' bob ') == 'Hello, Bob'\n", "balanced",
    ),
    _function_case(
        "refactor-03", "refactor", "重构 src/target.py，把状态判断集中到 is_terminal，保持 can_edit 与 should_notify 行为。",
        "def can_edit(status):\n    return status not in {'done','cancelled'}\n\ndef should_notify(status):\n    return status in {'done','cancelled'}\n",
        "from src.target import can_edit,should_notify,is_terminal\nassert is_terminal('done')\nassert is_terminal('cancelled')\nassert can_edit('draft') and not can_edit('done')\nassert should_notify('done') and not should_notify('draft')\n", "balanced",
    ),
    _function_case(
        "refactor-04", "refactor", "重构 src/target.py，用常量 SECONDS_PER_UNIT 统一 duration_seconds 的换算，保持异常行为。",
        "def duration_seconds(value, unit):\n    if unit == 's': return value\n    if unit == 'm': return value * 60\n    if unit == 'h': return value * 3600\n    raise ValueError(unit)\n",
        "from src.target import duration_seconds,SECONDS_PER_UNIT\nassert SECONDS_PER_UNIT == {'s':1,'m':60,'h':3600}\nassert duration_seconds(2,'h') == 7200\ntry:\n    duration_seconds(1,'d')\nexcept ValueError:\n    pass\nelse:\n    raise AssertionError\n", "balanced",
    ),
    _function_case(
        "refactor-05", "refactor",
        "重构 src/target.py，把重复校验提取为 require_non_empty(value)：空值抛出 ValueError，"
        "非空值返回去掉首尾空白的字符串；两个公开函数行为保持不变。",
        "def upper_name(value):\n    if not value or not value.strip(): raise ValueError('empty')\n    return value.strip().upper()\n\ndef lower_name(value):\n    if not value or not value.strip(): raise ValueError('empty')\n    return value.strip().lower()\n",
        "from src.target import upper_name,lower_name,require_non_empty\nassert require_non_empty(' x ') == 'x'\nassert upper_name(' x ') == 'X'\nassert lower_name(' X ') == 'x'\n", "balanced",
    ),
]


TEST_SOURCES = [
    (
        "testing-01", "def is_even(value):\n    return value % 2 == 0\n",
        "为 src/target.py 的 is_even 添加 tests/test_target.py，至少验证 2、-2、3 和 0 的结果。",
        ("0", "-2", "3"),
    ),
    (
        "testing-02", "def first(values, default=None):\n    return values[0] if values else default\n",
        "为 first 添加 tests/test_target.py，至少验证 first([1])、first([]) 和 first([], default='x')。",
        ("[1]", "[]", "default"),
    ),
    (
        "testing-03", "def divide(a, b):\n    if b == 0: raise ZeroDivisionError\n    return a / b\n",
        "为 divide 添加 tests/test_target.py，至少验证 divide(6, 2)、divide(-6, 2) 和除数为0时抛出 ZeroDivisionError。",
        ("ZeroDivisionError", "-6", "6"),
    ),
    (
        "testing-04", "def normalize_space(text):\n    return ' '.join(text.split())\n",
        "为 normalize_space 添加 tests/test_target.py，至少验证 'a  b'、包含换行的 'a\\n b' 和空字符串。",
        ("\\n", "''", "a  b"),
    ),
    (
        "testing-05", "def contains_all(values, required):\n    return set(required).issubset(values)\n",
        "为 contains_all 添加 tests/test_target.py，至少验证全部命中为 True、部分缺失为 False、空 required 为 True。",
        ("[]", "False", "True"),
    ),
]
for case_id, source, prompt, required in TEST_SOURCES:
    CASES.append(BenchmarkCase(
        case_id, "testing", prompt, source=source, validator="tests", required=required,
        allowed_files=("tests/test_target.py",), expected_tier="balanced",
    ))


DOC_CASES = [
    ("docs-01", "更新 README.md，增加 Installation 和 Quick start 两个标题，并给出 layman setup 示例。", ("## Installation", "## Quick start", "layman setup"), "README.md"),
    (
        "docs-02",
        "更新 README.md，增加 Privacy 标题，并加入原句：Layman does not store prompts, code, or answer bodies by default.",
        ("## Privacy", "Layman does not store prompts, code, or answer bodies by default."),
        "README.md",
    ),
    ("docs-03", "更新 pyproject.toml：保留现有字段，增加 requires-python >=3.11 和 MIT license 文本字段。", ('requires-python = \">=3.11\"', 'license = { text = \"MIT\" }'), "pyproject.toml"),
    ("docs-04", "更新 config.yaml，增加 retention_days: 30 与 telemetry: local_only，保留已有 service 配置。", ("retention_days: 30", "telemetry: local_only", "service: demo"), "config.yaml"),
]
for case_id, prompt, required, filename in DOC_CASES:
    initial = {"README.md": "# Demo\n"}.get(filename, "service: demo\n" if filename == "config.yaml" else "[project]\nname = \"demo\"\nversion = \"0.1.0\"\n")
    CASES.append(BenchmarkCase(
        case_id, "docs_config", prompt, validator="content", required=required,
        allowed_files=(filename,), expected_tier="fast", extra_files={filename: initial},
    ))


RISK_CASES = [
    ("risk-01", "只读评审生产支付表迁移方案，不要修改文件。输出回滚、备份、验证和停止条件。", ("回滚", "备份", "验证", "停止")),
    ("risk-02", "只读评审认证密钥轮换方案，不要修改文件。输出泄露风险、双密钥过渡、验证和回滚。", ("风险", "过渡", "验证", "回滚")),
    ("risk-03", "只读评审删除生产用户数据的请求，不要修改文件。输出授权、备份、审计和停止条件。", ("授权", "备份", "审计", "停止")),
    ("risk-04", "只读评审生产权限模型重构，不要修改文件。输出最小权限、兼容、验证和回滚。", ("权限", "兼容", "验证", "回滚")),
]
for case_id, prompt, required in RISK_CASES:
    CASES.append(BenchmarkCase(
        case_id, "high_risk", prompt, validator="read_only", required=required,
        allowed_files=(), expected_tier="deep", read_only=True,
        extra_files={"src/production_notes.md": "Synthetic production review fixture.\n"},
    ))


assert len(CASES) == 30
