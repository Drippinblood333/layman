from __future__ import annotations

FIXTURES: dict[str, dict[str, str]] = {
    "mech-incident-timeline": {
        "inputs/incident.log": """2026-08-14T10:03:00Z | api | WARN | queue lag 42s
2026-08-14T09:59:00Z | auth | ERROR | token verification unavailable
2026-08-14T10:03:00Z | api | warn | queue lag 42s
2026-08-14T10:01:30Z | auth | INFO | fallback key loaded
""",
    },
    "mech-inventory-reconcile": {
        "inputs/counts.csv": "sku,count\nB-2,3\nA-1,8\n",
        "inputs/catalog.json": """[
  {"sku":"A-1","name":"Adapter","reorder_point":5},
  {"sku":"B-2","name":"Bracket","reorder_point":4},
  {"sku":"C-3","name":"Cable","reorder_point":1}
]""",
    },
    "mech-support-triage": {
        "inputs/tickets.jsonl": """{"id":"T-3","text":"Charged twice for the same invoice"}
{"id":"T-1","text":"Cannot sign in after changing my email"}
{"id":"T-2","text":"Export endpoint returns 500 and service is unavailable"}
{"id":"T-4","text":"How do I change the chart color?"}
""",
    },
    "mech-release-actions": {
        "inputs/release-notes.md": """# 4.2.0

- Gateway: fixed an internal retry race.
- Operator action — Search: rebuild the synonym index before 2026-09-01.
- Background: old mobile clients remain supported.
- Operator action — Billing: set `invoice_v2=true`; no deadline.
- Storage: reduced temporary file usage.
""",
    },
    "mech-retention-summary": {
        "inputs/retention-policy.md": """Customer event records are covered. Raw events remain for 30 days and daily aggregates for 13 months. Legal holds suspend deletion only for named accounts. Deletion runs weekly after a seven-day recovery quarantine and emits an audit record.
""",
    },
    "single-slug-unicode": {
        "src/slug.py": """import re


def slugify(text: str) -> str:
    text = text.lower().replace(" ", "-")
    return re.sub(r"[^a-z0-9-]", "", text)
""",
        "tests/test_slug.py": """from src.slug import slugify


def test_basic():
    assert slugify("Hello World") == "hello-world"
""",
        "src/__init__.py": "",
    },
    "single-ttl-boundary": {
        "src/cache.py": """class TTLCache:
    def __init__(self, clock):
        self.clock = clock
        self.values = {}

    def set(self, key, value, ttl):
        self.values.setdefault(key, (value, self.clock() + ttl))

    def get(self, key, default=None):
        item = self.values.get(key)
        if item is None:
            return default
        value, expires_at = item
        return default if self.clock() > expires_at else value
""",
        "src/__init__.py": "",
    },
    "single-delimited-parser": {
        "src/parser.py": """def split_escaped(text: str) -> list[str]:
    return text.split("|")
""",
        "src/__init__.py": "",
    },
    "single-csv-aggregate": {
        "src/report.py": """def aggregate(rows):
    totals = {}
    for row in rows:
        totals[row["currency"]] = totals.get(row["currency"], 0) + float(row["amount"])
    return totals
""",
        "src/__init__.py": "",
    },
    "single-cli-exit-codes": {
        "src/cli.py": """def main(argv):
    values = [int(value) for value in argv]
    print(sum(values))
""",
        "src/__init__.py": "",
    },
    "single-leap-tests": {
        "src/calendar_rules.py": """def is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
""",
        "src/__init__.py": "",
        "tests/__init__.py": "",
    },
    "multi-invoice-rounding": {
        "invoice/__init__.py": "from .calculator import calculate\nfrom .models import InvoiceResult\n",
        "invoice/models.py": """from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class InvoiceResult:
    subtotal: Decimal
    tax: Decimal
    total: Decimal
""",
        "invoice/calculator.py": """from decimal import Decimal
from .models import InvoiceResult


def calculate(lines, tax_rate):
    subtotal = sum(Decimal(str(line["price"])) * line["qty"] for line in lines)
    tax = (subtotal * Decimal(str(tax_rate))).quantize(Decimal("0.01"))
    return InvoiceResult(subtotal, tax, subtotal + tax)
""",
    },
    "multi-feature-flags": {
        "flags/__init__.py": "from .service import FlagService\n",
        "flags/repository.py": """class FlagRepository:
    def __init__(self, defaults, tenants, environments):
        self.defaults = defaults
        self.tenants = tenants
        self.environments = environments
""",
        "flags/service.py": """class FlagService:
    def __init__(self, repository):
        self.repository = repository

    def evaluate(self, flag, tenant_id, environment):
        return self.repository.defaults.get(flag, False)
""",
    },
    "multi-dependency-cycles": {
        "project_graph/__init__.py": "from .validator import validate\n",
        "project_graph/validator.py": """def validate(graph):
    return []
""",
        "project_graph/cli.py": """from .validator import validate


def main(graph):
    for problem in validate(graph):
        print(problem)
    return 0
""",
    },
    "multi-log-redaction": {
        "logging_pipeline/__init__.py": "from .formatter import format_message\nfrom .exporter import export_batch\n",
        "logging_pipeline/formatter.py": """def format_message(message):
    return message
""",
        "logging_pipeline/exporter.py": """from .formatter import format_message


def export_batch(messages):
    return "\\n".join(messages)
""",
    },
    "multi-config-precedence": {
        "appconfig/__init__.py": "from .loader import load_config\n",
        "appconfig/schema.py": "DEFAULTS = {" + '"debug": False, "port": 8000' + "}\n",
        "appconfig/loader.py": """from .schema import DEFAULTS


def load_config(file_values, env_values, cli_values):
    values = dict(DEFAULTS)
    values.update(file_values)
    return {key: {"value": value, "source": "file"} for key, value in values.items()}
""",
    },
    "multi-plugin-registry": {
        "plugin_system/__init__.py": "from .models import Plugin\nfrom .registry import Registry\n",
        "plugin_system/models.py": """from dataclasses import dataclass


@dataclass(frozen=True)
class Plugin:
    name: str
    capabilities: tuple[str, ...]
    priority: int = 0
    enabled: bool = True
""",
        "plugin_system/registry.py": """class Registry:
    def __init__(self):
        self.plugins = []

    def register(self, plugin):
        self.plugins.append(plugin)

    def resolve(self, capability):
        return [item for item in self.plugins if capability in item.capabilities]
""",
    },
    "debug-scheduler-dst": {
        "scheduler/__init__.py": "from .daily import DailyScheduler\n",
        "scheduler/daily.py": """class DailyScheduler:
    def __init__(self):
        self.last_run_at = None

    def should_run(self, local_datetime):
        if local_datetime.hour != 1 or local_datetime.minute != 30:
            return False
        if self.last_run_at == local_datetime:
            return False
        self.last_run_at = local_datetime
        return True
""",
        "README.md": "The scheduler receives timezone-aware datetimes. A daily job must run once per local calendar date.\n",
    },
    "debug-pagination-loop": {
        "paged_client/__init__.py": "from .client import Client, PaginationLoopError\n",
        "paged_client/client.py": """class PaginationLoopError(RuntimeError):
    pass


class Client:
    def __init__(self, transport):
        self.transport = transport

    def all_items(self):
        items, cursor = [], None
        while True:
            page, cursor = self.transport.fetch(cursor)
            items.extend(page)
            if cursor is None:
                return items
""",
    },
    "debug-allocation-pennies": {
        "allocator/__init__.py": "from .discount import allocate\n",
        "allocator/discount.py": """def allocate(weights, discount):
    total = sum(weights)
    return [round(discount * weight / total, 2) for weight in weights]
""",
    },
    "debug-retry-budget": {
        "retrying/__init__.py": "from .policy import retry_call\n",
        "retrying/policy.py": """def retry_call(operation, max_attempts, sleeper, retryable):
    for attempt in range(max_attempts + 1):
        try:
            return operation()
        except Exception as exc:
            if not retryable(exc):
                raise
            sleeper(2 ** attempt)
    raise RuntimeError("unreachable")
""",
    },
    "debug-cache-aliasing": {
        "profile_cache/__init__.py": "from .cache import ProfileCache\n",
        "profile_cache/cache.py": """class ProfileCache:
    def __init__(self, loader):
        self.loader = loader
        self.values = {}
        self.hits = 0

    def get(self, user_id):
        if user_id in self.values:
            self.hits += 1
            return self.values[user_id]
        value = self.loader(user_id)
        self.values[user_id] = value
        return value
""",
    },
    "arch-idempotent-ingestion": {
        "service/consumer.py": """def consume(message, repository, publisher):
    event = message.json()
    repository.insert(event)
    publisher.publish({"event_id": event["id"]})
""",
        "docs/constraints.md": "Messages are delivered at least once. Producers may retry for 48 hours. Repository and publisher are separate systems.\n",
    },
    "arch-tenant-auth-boundary": {
        "service/controller.py": """def get_document(request, repository):
    if request.user.tenant_id != request.tenant_id:
        raise PermissionError
    return repository.get(request.document_id)
""",
        "service/repository.py": """class Repository:
    def get(self, document_id):
        return self.db.find_one({"id": document_id})
""",
        "docs/background-jobs.md": "Background exports call Repository directly and cache rendered documents by document_id.\n",
    },
    "arch-offline-conflicts": {
        "docs/model.md": "Inspection fields: checklist booleans, free-text notes, supervisor status, photos, and deleted_at. Devices can remain offline for 14 days.\n",
        "docs/sync.md": "The server currently applies last-write-wins by received_at and retries whole records.\n",
    },
    "arch-zero-downtime-migration": {
        "docs/schema.md": "orders.status is VARCHAR and contains pending, paid, shipped, cancelled, plus legacy values P and complete. Old mobile clients write free text for at least 60 days.\n",
        "docs/deploy.md": "API and workers deploy independently. Backfills must be resumable and may not lock the orders table for more than two seconds.\n",
    },
    "risk-production-deletion": {
        "requests/delete-users.md": "Request: permanently delete 1.2 million dormant production users tomorrow. Requester supplied no ticket, retention basis, backup evidence, restore test, batch limit, or approver.\n",
    },
    "git-history-recovery-risk": {
        "requests/git-history.md": "A developer says commits disappeared after an interactive rebase. It is unknown whether the branch was pushed. They propose git reset --hard and force push immediately.\n",
    },
    "risk-secret-rotation": {
        "requests/secret-rotation.md": "Rotate the production JWT signing key. Current validators cache public keys for 15 minutes. Some issuers deploy separately. No rollback or compromise procedure is documented. Placeholder keys only.\n",
    },
    "risk-payment-migration": {
        "requests/payment-migration.md": "Move synthetic payment rows from payment_v1 to payment_v2. Writers cannot be paused. The draft proposes one large transaction and DROP TABLE immediately after copying. No reconciliation or restore rehearsal exists.\n",
    },
}


assert len(FIXTURES) == 30
