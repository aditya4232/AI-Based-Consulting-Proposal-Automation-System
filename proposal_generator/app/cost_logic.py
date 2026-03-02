import os
import json
import csv
import tempfile
import time
from uuid import uuid4
from math import ceil


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INDUSTRY COST MULTIPLIERS
# Different industries have varying cost structures due to compliance overhead,
# specialised talent requirements, infrastructure complexity, and risk premiums.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INDUSTRY_COST_MULTIPLIERS: dict[str, dict] = {
    # industry_key: { dev_multiplier, infra_multiplier, contingency_pct, reason }
    "healthcare":       {"dev": 1.35, "infra": 1.25, "contingency": 0.15, "reason": "HIPAA/HITECH compliance, HL7 FHIR integration, audit trails"},
    "finance":          {"dev": 1.40, "infra": 1.30, "contingency": 0.15, "reason": "PCI DSS, SOX compliance, high-availability requirements, regulatory reporting"},
    "fintech":          {"dev": 1.35, "infra": 1.25, "contingency": 0.15, "reason": "Regulatory compliance (RBI/SEBI), real-time transaction processing, security hardening"},
    "insurance":        {"dev": 1.30, "infra": 1.20, "contingency": 0.15, "reason": "Actuarial systems, regulatory compliance (IRDAI), legacy integration"},
    "pharmaceuticals":  {"dev": 1.40, "infra": 1.20, "contingency": 0.15, "reason": "GxP validation, FDA 21 CFR Part 11, data integrity requirements"},
    "ecommerce":        {"dev": 1.10, "infra": 1.30, "contingency": 0.12, "reason": "High traffic handling, payment security, CDN and caching infrastructure"},
    "retail":           {"dev": 1.10, "infra": 1.15, "contingency": 0.10, "reason": "Omnichannel integration, POS systems, inventory management"},
    "education":        {"dev": 1.00, "infra": 1.10, "contingency": 0.10, "reason": "Standard web platform with LMS integration"},
    "manufacturing":    {"dev": 1.25, "infra": 1.20, "contingency": 0.12, "reason": "OT/IT convergence, industrial IoT, MES/ERP integration"},
    "logistics":        {"dev": 1.15, "infra": 1.20, "contingency": 0.12, "reason": "Real-time tracking infrastructure, GPS/IoT integration, route optimization"},
    "real estate":      {"dev": 1.10, "infra": 1.10, "contingency": 0.10, "reason": "Property management, GIS integration, document management"},
    "telecom":          {"dev": 1.30, "infra": 1.35, "contingency": 0.15, "reason": "High-availability OSS/BSS, network integration, massive scale"},
    "energy":           {"dev": 1.25, "infra": 1.25, "contingency": 0.15, "reason": "SCADA integration, grid security, regulatory compliance"},
    "automotive":       {"dev": 1.30, "infra": 1.20, "contingency": 0.12, "reason": "Functional safety (ISO 26262), embedded systems, V2X connectivity"},
    "media":            {"dev": 1.10, "infra": 1.30, "contingency": 0.10, "reason": "CDN-heavy infrastructure, DRM, live streaming scalability"},
    "gaming":           {"dev": 1.20, "infra": 1.35, "contingency": 0.12, "reason": "Low-latency server infrastructure, anti-cheat, real-time multiplayer"},
    "agriculture":      {"dev": 1.05, "infra": 1.10, "contingency": 0.10, "reason": "IoT sensor integration, rural connectivity challenges"},
    "government":       {"dev": 1.20, "infra": 1.15, "contingency": 0.15, "reason": "Security clearances, accessibility compliance, legacy system integration"},
    "hospitality":      {"dev": 1.05, "infra": 1.10, "contingency": 0.10, "reason": "PMS integration, booking engine, multi-property support"},
    "construction":     {"dev": 1.15, "infra": 1.10, "contingency": 0.12, "reason": "BIM integration, field mobility, safety compliance"},
    "legal":            {"dev": 1.20, "infra": 1.10, "contingency": 0.12, "reason": "Document management, e-discovery, confidentiality controls"},
    "hr":               {"dev": 1.00, "infra": 1.05, "contingency": 0.10, "reason": "Standard HRIS platform, employee data privacy"},
    "nonprofit":        {"dev": 0.90, "infra": 1.00, "contingency": 0.10, "reason": "Budget-conscious, standard web platform"},
    "saas":             {"dev": 1.15, "infra": 1.20, "contingency": 0.12, "reason": "Multi-tenancy, SOC 2 compliance, scalable infrastructure"},
    "cloud":            {"dev": 1.15, "infra": 1.25, "contingency": 0.12, "reason": "Cloud-native architecture, FinOps, multi-cloud complexity"},
    "cybersecurity":    {"dev": 1.35, "infra": 1.20, "contingency": 0.15, "reason": "Security tooling integration, SOC setup, compliance frameworks"},
    "travel":           {"dev": 1.10, "infra": 1.20, "contingency": 0.12, "reason": "GDS integration, booking engine, seasonal traffic spikes"},
    "food":             {"dev": 1.05, "infra": 1.15, "contingency": 0.10, "reason": "Delivery logistics, cold chain IoT, food safety compliance"},
    "sports":           {"dev": 1.10, "infra": 1.20, "contingency": 0.10, "reason": "Live event infrastructure, fan engagement, analytics"},
    "blockchain":       {"dev": 1.30, "infra": 1.15, "contingency": 0.15, "reason": "Smart contract auditing, node infrastructure, security reviews"},
    "ai_ml":            {"dev": 1.30, "infra": 1.35, "contingency": 0.15, "reason": "GPU compute, model training infrastructure, MLOps pipelines"},
}

# Alias mapping (same as prompt_builder, kept in sync)
_COST_INDUSTRY_ALIASES: dict[str, str] = {
    "health": "healthcare", "medical": "healthcare", "hospital": "healthcare",
    "pharma": "pharmaceuticals", "pharmaceutical": "pharmaceuticals", "biotech": "pharmaceuticals",
    "banking": "finance", "bank": "finance", "financial": "finance",
    "insurtech": "insurance",
    "payments": "fintech", "lending": "fintech",
    "e-commerce": "ecommerce", "ecom": "ecommerce", "online store": "ecommerce", "marketplace": "ecommerce",
    "fmcg": "retail", "consumer goods": "retail",
    "edtech": "education", "university": "education", "school": "education",
    "factory": "manufacturing", "industrial": "manufacturing",
    "supply chain": "logistics", "shipping": "logistics", "warehousing": "logistics", "transportation": "logistics",
    "realestate": "real estate", "proptech": "real estate", "property": "real estate",
    "telecommunications": "telecom", "telco": "telecom",
    "power": "energy", "utilities": "energy", "oil and gas": "energy", "renewable": "energy", "solar": "energy",
    "auto": "automotive", "electric vehicle": "automotive", "ev": "automotive",
    "entertainment": "media", "streaming": "media", "ott": "media", "publishing": "media",
    "game": "gaming", "esports": "gaming",
    "agri": "agriculture", "farming": "agriculture", "agritech": "agriculture",
    "govtech": "government", "public sector": "government",
    "hotel": "hospitality", "tourism": "hospitality", "restaurant": "hospitality",
    "infrastructure": "construction", "civil engineering": "construction",
    "legaltech": "legal", "law firm": "legal", "law": "legal",
    "human resources": "hr", "hrtech": "hr", "talent": "hr", "recruitment": "hr",
    "ngo": "nonprofit", "social impact": "nonprofit", "charity": "nonprofit",
    "software as a service": "saas", "b2b saas": "saas", "platform": "saas",
    "cloud computing": "cloud", "devops": "cloud",
    "infosec": "cybersecurity", "security": "cybersecurity",
    "traveltech": "travel", "booking": "travel", "aviation": "travel",
    "foodtech": "food", "food delivery": "food",
    "sportstech": "sports", "fitness": "sports",
    "web3": "blockchain", "crypto": "blockchain", "defi": "blockchain",
    "artificial intelligence": "ai_ml", "machine learning": "ai_ml", "ai": "ai_ml", "data science": "ai_ml", "ml": "ai_ml",
    "technology": "saas",
}


def _resolve_cost_industry(raw_industry: str) -> str | None:
    """Fuzzy-match user input to known industry for cost multipliers."""
    key = raw_industry.strip().lower()
    if key in INDUSTRY_COST_MULTIPLIERS:
        return key
    if key in _COST_INDUSTRY_ALIASES:
        return _COST_INDUSTRY_ALIASES[key]
    for alias, canonical in _COST_INDUSTRY_ALIASES.items():
        if alias in key or key in alias:
            return canonical
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INDUSTRY-SPECIFIC TEAM ROLES
# Additional specialised roles needed for certain industries
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_INDUSTRY_EXTRA_ROLES: dict[str, list[dict]] = {
    "healthcare": [{"role": "Health IT / Compliance Specialist", "count": 1, "allocation": "Part-time"}],
    "finance":    [{"role": "Security / Compliance Analyst", "count": 1, "allocation": "Part-time"}],
    "fintech":    [{"role": "Regulatory Compliance Engineer", "count": 1, "allocation": "Part-time"}],
    "insurance":  [{"role": "Business Analyst (Insurance Domain)", "count": 1, "allocation": "Part-time"}],
    "pharmaceuticals": [{"role": "GxP Validation Specialist", "count": 1, "allocation": "Part-time"}],
    "manufacturing": [{"role": "Industrial IoT Engineer", "count": 1, "allocation": "Part-time"}],
    "cybersecurity": [{"role": "Security Engineer / Penetration Tester", "count": 1, "allocation": "Part-time"}],
    "government": [{"role": "Accessibility / Compliance Specialist", "count": 1, "allocation": "Part-time"}],
    "ai_ml":      [{"role": "ML Engineer / Data Scientist", "count": 1, "allocation": "Full-time"}],
    "blockchain": [{"role": "Smart Contract Developer / Auditor", "count": 1, "allocation": "Part-time"}],
    "gaming":     [{"role": "Game Server / Infrastructure Engineer", "count": 1, "allocation": "Full-time"}],
    "energy":     [{"role": "SCADA / OT Integration Specialist", "count": 1, "allocation": "Part-time"}],
    "telecom":    [{"role": "Network Integration Engineer", "count": 1, "allocation": "Part-time"}],
}


def estimate_team_composition(
    duration_months: int,
    expected_users: int,
    tech_stack: list[str],
    industry: str = "",
) -> list[dict]:
    """Return a deterministic team composition estimate.

    Uses heuristic rules based on project size and industry.
    No LLM involved; purely formula-driven so it never hallucinates.
    """
    team = [
        {"role": "Project Manager", "count": 1, "allocation": "Full-time"},
    ]

    # Backend developers: 1 per 3 months, min 1
    backend_count = max(1, ceil(duration_months / 3))
    team.append(
        {"role": "Backend Developer", "count": backend_count, "allocation": "Full-time"}
    )

    # Frontend developers: 1 per 4 months, min 1
    frontend_count = max(1, ceil(duration_months / 4))
    team.append(
        {"role": "Frontend Developer", "count": frontend_count, "allocation": "Full-time"}
    )

    # QA engineer: always at least 1
    qa_count = 1 if duration_months <= 4 else 2
    team.append({"role": "QA Engineer", "count": qa_count, "allocation": "Full-time"})

    # DevOps: 1 for larger projects
    if duration_months >= 4 or expected_users >= 5000:
        team.append({"role": "DevOps Engineer", "count": 1, "allocation": "Part-time"})

    # UI/UX designer for any project with a frontend stack
    frontend_stacks = {
        "react", "vue.js", "vue", "angular", "next.js", "svelte", "flutter",
        "react native", "swift", "kotlin", "ionic",
    }
    has_frontend = any(t.lower() in frontend_stacks for t in tech_stack)
    if has_frontend:
        team.append({"role": "UI/UX Designer", "count": 1, "allocation": "Part-time"})

    # Database admin for large user bases
    if expected_users >= 10000:
        team.append(
            {"role": "Database Administrator", "count": 1, "allocation": "Part-time"}
        )

    # Solution / Technical Architect for complex projects
    if duration_months >= 6 or expected_users >= 50000:
        team.append(
            {"role": "Solution Architect", "count": 1, "allocation": "Part-time"}
        )

    # Business Analyst for longer projects
    if duration_months >= 4:
        team.append(
            {"role": "Business Analyst", "count": 1, "allocation": "Part-time"}
        )

    # Industry-specific extra roles
    resolved = _resolve_cost_industry(industry)
    if resolved and resolved in _INDUSTRY_EXTRA_ROLES:
        team.extend(_INDUSTRY_EXTRA_ROLES[resolved])

    return team


def calculate_cost(
    duration_months: int,
    expected_users: int,
    dev_rate_per_month: float = 150000.0,  # INR per month
    contingency_pct: float = 0.10,
    discount_pct: float = 0.0,
    industry: str = "",
):
    """Return a detailed cost breakdown in INR with industry-aware multipliers.

    - Applies industry-specific cost multipliers for development and infrastructure.
    - Uses tiered per-user infra pricing.
    - Applies industry-appropriate contingency rates.
    - Applies an optional overall discount.
    - All values in Indian Rupees (INR).
    """

    # Look up industry multipliers
    resolved_industry = _resolve_cost_industry(industry)
    multipliers = INDUSTRY_COST_MULTIPLIERS.get(resolved_industry or "", {})
    dev_mult = multipliers.get("dev", 1.0)
    infra_mult = multipliers.get("infra", 1.0)
    industry_contingency = multipliers.get("contingency", contingency_pct)
    cost_reason = multipliers.get("reason", "Standard technology project")

    # Apply industry multiplier to dev rate
    adjusted_dev_rate = float(dev_rate_per_month) * dev_mult
    base_dev_cost = adjusted_dev_rate * duration_months

    # Tiered infra cost per user in INR
    if expected_users <= 1000:
        infra_per_user = 42.0
    elif expected_users <= 10000:
        infra_per_user = 29.0
    else:
        infra_per_user = 17.0

    # Apply industry infra multiplier
    infra_per_user_adjusted = infra_per_user * infra_mult
    infra_cost = expected_users * infra_per_user_adjusted

    # Use industry-specific contingency if higher
    effective_contingency = max(float(contingency_pct), industry_contingency)
    contingency = base_dev_cost * effective_contingency

    subtotal = base_dev_cost + infra_cost + contingency

    discount = subtotal * float(discount_pct)
    total = subtotal - discount

    monthly_average = total / max(1, duration_months)

    return {
        "development_cost": round(base_dev_cost, 2),
        "infrastructure_cost": round(infra_cost, 2),
        "contingency": round(contingency, 2),
        "discount": round(discount, 2),
        "total_estimated_cost": round(total, 2),
        "monthly_average": round(monthly_average, 2),
        "currency": "INR",
        "industry_applied": resolved_industry or "general",
        "cost_adjustment_reason": cost_reason,
        "details": {
            "duration_months": int(duration_months),
            "expected_users": int(expected_users),
            "infra_per_user": round(infra_per_user_adjusted, 2),
            "dev_rate_per_month": round(adjusted_dev_rate, 2),
            "contingency_pct": effective_contingency,
            "discount_pct": float(discount_pct),
            "industry_dev_multiplier": dev_mult,
            "industry_infra_multiplier": infra_mult,
        },
    }


def _resolve_output_dir(provided_dir: str | None) -> str:
    """Resolve a writable output directory.

    Priority: provided_dir -> ENV COST_OUTPUT_DIR -> ./outputs (if writable) -> system temp dir
    """
    env_dir = os.environ.get("COST_OUTPUT_DIR")

    # Base directory that output directories must be under. This prevents path traversal.
    base_root = os.path.abspath(os.environ.get("COST_OUTPUT_BASE", os.getcwd()))

    candidates = [
        provided_dir,
        env_dir,
        os.path.join(os.getcwd(), "outputs"),
        tempfile.gettempdir(),
    ]

    for c in candidates:
        if not c:
            continue
        try:
            candidate_abs = os.path.abspath(c)

            # Ensure candidate is inside allowed base_root
            try:
                common = os.path.commonpath([base_root, candidate_abs])
            except Exception:
                # if paths are on different drives on Windows, skip
                continue

            if common != base_root:
                # candidate is outside allowed base
                continue

            os.makedirs(candidate_abs, exist_ok=True)
            # attempt a tiny write test
            test_path = os.path.join(candidate_abs, ".write_test")
            with open(test_path, "w") as tf:
                tf.write("ok")
            os.remove(test_path)
            return candidate_abs
        except Exception:
            continue

    # As a next attempt, try to create an outputs directory under base_root.
    try:
        fallback_under_base = os.path.join(base_root, "outputs")
        os.makedirs(fallback_under_base, exist_ok=True)
        test_path = os.path.join(fallback_under_base, ".write_test")
        with open(test_path, "w") as tf:
            tf.write("ok")
        os.remove(test_path)
        return os.path.abspath(fallback_under_base)
    except Exception:
        pass

    # final fallback behavior:
    # By default we allow returning the system temp directory as a last resort
    # because some environments may not allow writing under `base_root` (e.g., read-only containers).
    # To opt out of this behavior and enforce strict containment under `base_root`, set
    # the environment variable `COST_ALLOW_SYSTEM_TEMP=0`.
    # default to strict mode (no system temp fallback) unless explicitly allowed
    allow_system_temp = os.environ.get("COST_ALLOW_SYSTEM_TEMP", "0")
    if allow_system_temp and allow_system_temp != "0":
        return os.path.abspath(tempfile.gettempdir())

    # Strict mode: do not fall back outside base_root
    raise RuntimeError(
        "No writable output directory found within allowed base; set COST_ALLOW_SYSTEM_TEMP=1 to permit system temp fallback."
    )


def save_cost_report(
    cost_data: dict, output_dir: str | None = None, prefix: str | None = None
) -> dict:
    """Save `cost_data` as JSON and CSV in `output_dir` and return file paths.

    `output_dir` can be None to let the function resolve a safe writable location.
    """
    resolved_dir = _resolve_output_dir(output_dir)

    # ensure a unique filename prefix by default to avoid overwrites
    if not prefix:
        prefix = f"cost_report_{int(time.time())}_{uuid4().hex[:6]}"

    base_name = f"{prefix}"
    json_path = os.path.join(resolved_dir, f"{base_name}.json")
    csv_path = os.path.join(resolved_dir, f"{base_name}.csv")

    # JSON
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(cost_data, jf, indent=2)

    # CSV (flat key / value pairs for top-level items)
    with open(csv_path, "w", newline="", encoding="utf-8") as cf:
        writer = csv.writer(cf)
        writer.writerow(["key", "value"])

        for k, v in cost_data.items():
            if isinstance(v, dict):
                writer.writerow([k, json.dumps(v)])
            else:
                writer.writerow([k, v])

    return {"json": os.path.abspath(json_path), "csv": os.path.abspath(csv_path)}
