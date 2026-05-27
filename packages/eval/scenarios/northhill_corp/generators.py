import random
from datetime import datetime, timedelta, timezone

from faker import Faker

TEAMS = [
    {
        "name":
        "Platform",
        "weight":
        0.15,
        "titles": [
            "Software Engineer",
            "Senior Software Engineer",
            "Staff Engineer",
            "Backend Engineer",
        ]
    },
    {
        "name":
        "Engineering/SRE",
        "weight":
        0.15,
        "titles": [
            "SRE Engineer",
            "DevOps Engineer",
            "Infrastructure Engineer",
            "Site Reliability Engineer",
        ]
    },
    {
        "name":
        "IT",
        "weight":
        0.10,
        "titles": [
            "IT Support Agent",
            "Systems Administrator",
            "Network Engineer",
            "IT Operations Analyst",
        ]
    },
    {
        "name":
        "People",
        "weight":
        0.08,
        "titles": [
            "HR Coordinator",
            "Recruiter",
            "People Operations Specialist",
            "Benefits Analyst",
        ]
    },
    {
        "name":
        "Finance",
        "weight":
        0.08,
        "titles": [
            "Financial Analyst",
            "Accounts Receivable Specialist",
            "Staff Accountant",
            "FP&A Analyst",
        ]
    },
    {
        "name":
        "Customer Support",
        "weight":
        0.15,
        "titles": [
            "Support Agent",
            "Support Engineer",
            "Technical Support Specialist",
            "Customer Success Associate",
        ]
    },
    {
        "name":
        "Legal/Compliance",
        "weight":
        0.05,
        "titles": [
            "Paralegal",
            "Compliance Analyst",
            "Contract Specialist",
            "Privacy Analyst",
        ]
    },
    {
        "name": "Executive",
        "weight": 0.00,
        "titles": []
    },
    {
        "name":
        "Sales",
        "weight":
        0.10,
        "titles": [
            "Account Executive",
            "Sales Development Rep",
            "Enterprise Sales Manager",
            "Solutions Engineer",
        ]
    },
    {
        "name":
        "Product",
        "weight":
        0.08,
        "titles": [
            "Product Manager",
            "Product Designer",
            "UX Researcher",
            "Technical Writer",
        ]
    },
    {
        "name":
        "Data",
        "weight":
        0.06,
        "titles": [
            "Data Engineer",
            "Data Analyst",
            "Analytics Engineer",
            "Machine Learning Engineer",
        ]
    },
]

_ACTIVE_TEAMS = [t for t in TEAMS if t["weight"] > 0]
_TEAM_WEIGHTS = [t["weight"] for t in _ACTIVE_TEAMS]

NORTHHILL_PRODUCTS = ["platform-api", "auth-service", "analytics"]

CUSTOMER_TIERS = ["enterprise", "business", "starter"]
CUSTOMER_TIER_WEIGHTS = [0.10, 0.30, 0.60]

ARR_RANGES = {
    "enterprise": (200_000, 500_000),
    "business": (50_000, 199_000),
    "starter": (12_000, 49_000),
}

AMBIENT_TEMPLATES = [
    "PR #{pr_num} ready for review — {feature}",
    "standup: yesterday — {task_a}. today — {task_b}. no blockers.",
    "standup: yesterday — {task_a}. today — {task_b}. blocked on {blocker}.",
    "anyone know where the {tool} runbook is?",
    "lunch at {time}?",
    "heads up — {tool} maintenance window tonight 10pm-2am PT",
    "can someone review the {feature} design doc?",
    "just merged {feature} into staging, deploying in 30 min",
    "reminder: team retro at {time} today",
    "fyi {tool} dashboard is showing elevated latency but within SLA",
    "pto heads up — I'll be out {day}",
    "anyone tried the new {tool} release? worth upgrading?",
    "quick question — what's the default timeout for {tool}?",
    "shipping {feature} to canary, will monitor for an hour",
    "docs updated for {feature}, lmk if anything is unclear",
]

_FEATURE_NAMES = [
    "rate limiter",
    "webhook retry logic",
    "session caching",
    "audit log export",
    "role-based access",
    "multi-tenant routing",
    "API pagination",
    "batch import",
    "SSO integration",
    "dashboard filters",
    "alerting rules",
    "CSV export",
    "email notifications",
    "search indexing",
    "dark mode toggle",
]

_TASK_NAMES = [
    "reviewed PRs",
    "fixed flaky test",
    "updated CI config",
    "pair-programmed on auth module",
    "wrote integration tests",
    "triaged support tickets",
    "updated runbook",
    "deployed hotfix",
    "refactored DB queries",
    "added monitoring alerts",
    "drafted RFC for caching",
    "resolved merge conflicts",
    "benchmarked API endpoints",
    "cleaned up stale branches",
    "onboarded new team member",
]

_TOOL_NAMES = [
    "Terraform",
    "Datadog",
    "Sentry",
    "Vault",
    "ArgoCD",
    "Grafana",
    "PagerDuty",
    "Kubernetes",
    "Redis",
    "Postgres",
]

_BLOCKER_NAMES = [
    "CI flakiness",
    "staging env down",
    "waiting on design review",
    "dependency upgrade conflict",
    "access permissions",
]

_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

_TIMES = ["11:30", "12:00", "12:30", "1:00", "2:00", "3:00"]

_SUPPORT_SUBJECTS = [
    ("API rate limiting errors",
     "Receiving HTTP 429 responses intermittently."),
    ("SSO callback timeout",
     "SAML assertion validation timing out after 30s."),
    ("Dashboard loading slowly",
     "Analytics dashboard takes 15+ seconds to load."),
    ("Webhook delivery failures",
     "Outbound webhooks returning 502 for 2 hours."),
    ("Data export incomplete", "CSV export missing last 3 days of records."),
    ("User provisioning stuck", "SCIM sync shows pending for 24+ hours."),
    ("API key rotation issue", "Rotated key still valid after revocation."),
    ("Billing page 500 error", "Subscription management page returns 500."),
    ("Search results stale", "Full-text search index appears 6 hours behind."),
    ("Audit log gaps", "Missing audit entries for 2026-05-13 afternoon."),
]


def generate_employees(seed: int = 42) -> list[dict]:
    """Generate ~90 synthetic employees starting at U300.

    Args:
        seed (int): Random seed for deterministic output.

    Returns:
        list[dict]: Employee dicts with id, handle, name, email, title, team.
    """
    fake = Faker()
    Faker.seed(seed)
    rng = random.Random(seed)

    employees: list[dict] = []
    seen_handles: set[str] = set()

    for i in range(90):
        uid = f"U{300 + i}"
        first = fake.first_name()
        last = fake.last_name()
        name = f"{first} {last}"

        handle = f"{first[0].lower()}{last.lower()}"
        if handle in seen_handles:
            handle = f"{first.lower()}_{last.lower()}"
        seen_handles.add(handle)

        team_info = rng.choices(_ACTIVE_TEAMS, weights=_TEAM_WEIGHTS, k=1)[0]
        title = rng.choice(team_info["titles"])

        employees.append({
            "id": uid,
            "handle": handle,
            "name": name,
            "email": f"{first.lower()}.{last.lower()}@northhill.com",
            "title": title,
            "team": team_info["name"],
        })

    return employees


def generate_customers(
    support_team_handles: list[str],
    seed: int = 42,
) -> list[dict]:
    """Generate ~45 synthetic customer accounts starting at ACCT-2000.

    Args:
        support_team_handles (list[str]): Handles of Customer Support employees
            to assign as CSMs.
        seed (int): Random seed for deterministic output.

    Returns:
        list[dict]: Customer account dicts matching the ACCT-XXXX schema.
    """
    fake = Faker()
    Faker.seed(seed + 100)
    rng = random.Random(seed + 100)

    customers: list[dict] = []
    for i in range(45):
        acct_id = f"ACCT-{2000 + i}"
        tier = rng.choices(CUSTOMER_TIERS, weights=CUSTOMER_TIER_WEIGHTS,
                           k=1)[0]
        lo, hi = ARR_RANGES[tier]
        arr = round(rng.uniform(lo, hi), -2)

        mean_score = 72
        score = max(20, min(100, int(rng.gauss(mean_score, 15))))

        csm_handle = rng.choice(support_team_handles)
        renewal = datetime(2026, 6, 1, tzinfo=timezone.utc) + timedelta(
            days=rng.randint(30, 365))

        n_contacts = rng.randint(1, 3)
        contacts = []
        for _ in range(n_contacts):
            contacts.append({
                "name":
                fake.name(),
                "email":
                fake.company_email(),
                "role":
                rng.choice([
                    "CTO",
                    "VP Engineering",
                    "IT Director",
                    "Head of Product",
                    "Engineering Lead",
                    "Developer",
                ]),
            })

        n_products = rng.randint(1, len(NORTHHILL_PRODUCTS))
        products = rng.sample(NORTHHILL_PRODUCTS, n_products)

        customers.append({
            "account_id": acct_id,
            "company_name": fake.company(),
            "tier": tier,
            "arr": arr,
            "health_score": score,
            "csm": csm_handle,
            "renewal_date": renewal.strftime("%Y-%m-%d"),
            "contacts": contacts,
            "products": products,
        })

    return customers


def generate_support_tickets(
    customers: list[dict],
    support_handles: list[str],
    seed: int = 42,
) -> list[dict]:
    """Generate 8 synthetic customer support tickets starting at CS-2000.

    Args:
        customers (list[dict]): Generated customer accounts
            to reference.
        support_handles (list[str]): Support team employee
            handles for assignees.
        seed (int): Random seed for deterministic output.

    Returns:
        list[dict]: Ticket dicts matching the CS-XXXX schema.
    """
    rng = random.Random(seed + 200)

    statuses = [
        "open", "open", "open", "in_progress", "in_progress", "resolved",
        "resolved", "resolved"
    ]
    tickets: list[dict] = []

    for i in range(8):
        tid = f"CS-{2000 + i}"
        cust = rng.choice(customers)
        subj_tmpl, body_tmpl = _SUPPORT_SUBJECTS[i % len(_SUPPORT_SUBJECTS)]
        subject = f"{subj_tmpl} for {cust['company_name']}"
        day_offset = rng.randint(0, 5)
        created = datetime(2026, 5, 10, 9, 0, tzinfo=timezone.utc) + timedelta(
            days=day_offset, hours=rng.randint(0, 8))
        updated = created + timedelta(hours=rng.randint(1, 48))
        assignee_handle = rng.choice(support_handles)

        tickets.append({
            "ticket_id": tid,
            "subject": subject,
            "body": f"{body_tmpl} Account: {cust['account_id']} "
            f"({cust['company_name']}).",
            "requester": {
                "name": cust["contacts"][0]["name"],
                "email": cust["contacts"][0]["email"],
            },
            "assignee_handle": assignee_handle,
            "queue": "customer-support",
            "status": statuses[i],
            "priority": rng.choice(["P1", "P2", "P3"]),
            "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updated_at": updated.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tags": ["generated", cust["tier"]],
            "related_tickets": [],
            "comments": [],
            "account_id": cust["account_id"],
        })

    return tickets


def generate_ambient_messages(
    all_users: list[dict],
    channels: list[dict],
    seed: int = 42,
) -> dict[str, list[tuple[str, str, str, str]]]:
    """Generate ambient Slack noise messages per channel per day.

    Args:
        all_users (list[dict]): All employees (hand-crafted + generated).
        channels (list[dict]): Channel dicts with 'id' and 'name'.
        seed (int): Random seed for deterministic output.

    Returns:
        dict[str, list[tuple[str, str, str, str]]]: Channel ID to list of
            (date, user_id, ts, text) tuples.
    """
    rng = random.Random(seed + 300)
    dates = [f"2026-05-{d:02d}" for d in range(10, 16)]
    user_ids = [u["id"] for u in all_users]

    result: dict[str, list[tuple[str, str, str, str]]] = {}

    for ch in channels:
        ch_id = ch["id"]
        messages: list[tuple[str, str, str, str]] = []

        for date_str in dates:
            n_msgs = rng.randint(5, 15)
            for msg_i in range(n_msgs):
                uid = rng.choice(user_ids)
                hour = rng.randint(8, 18)
                minute = rng.randint(0, 59)
                second = rng.randint(0, 59)
                base_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(
                    hour=hour,
                    minute=minute,
                    second=second,
                    tzinfo=timezone.utc)
                epoch = int(base_dt.timestamp())
                ts = f"{epoch}.{msg_i:06d}"

                template = rng.choice(AMBIENT_TEMPLATES)
                text = template.format(
                    pr_num=rng.randint(1000, 9999),
                    feature=rng.choice(_FEATURE_NAMES),
                    task_a=rng.choice(_TASK_NAMES),
                    task_b=rng.choice(_TASK_NAMES),
                    blocker=rng.choice(_BLOCKER_NAMES),
                    tool=rng.choice(_TOOL_NAMES),
                    time=rng.choice(_TIMES),
                    day=rng.choice(_DAYS),
                )
                messages.append((date_str, uid, ts, text))

        result[ch_id] = messages

    return result
