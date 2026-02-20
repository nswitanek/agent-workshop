"""
Compliance Checker Tool

Checks regulatory compliance requirements and maps them to audit procedures.
Simulates querying a compliance database for applicable regulations.
"""

import json
from typing import Annotated

from agent_framework import tool
from pydantic import Field

COMPLIANCE_REQUIREMENTS = {
    "SOX 404": {
        "description": "Sarbanes-Oxley Section 404 — Management assessment of internal controls",
        "applicable_to": "Public companies",
        "key_requirements": [
            "Management must assess effectiveness of ICFR annually",
            "External auditor must attest to and report on management's assessment",
            "Material weaknesses must be disclosed",
            "Significant deficiencies reported to audit committee",
        ],
        "audit_procedures": [
            "Evaluate design of key controls over significant accounts",
            "Test operating effectiveness through walkthroughs and sampling",
            "Evaluate IT general controls (access, change management, operations)",
            "Assess entity-level controls and tone at the top",
        ],
    },
    "Basel III": {
        "description": "International banking regulation — capital adequacy and liquidity",
        "applicable_to": "Banking and financial institutions",
        "key_requirements": [
            "Minimum capital ratios (CET1, Tier 1, Total Capital)",
            "Liquidity Coverage Ratio (LCR)",
            "Net Stable Funding Ratio (NSFR)",
            "Leverage ratio requirements",
        ],
        "audit_procedures": [
            "Verify capital ratio calculations",
            "Test risk-weighted asset computations",
            "Review liquidity stress testing models",
            "Assess compliance with regulatory reporting requirements",
        ],
    },
    "ASC 326": {
        "description": "Current Expected Credit Losses (CECL) — accounting for credit losses",
        "applicable_to": "Entities holding financial assets at amortized cost",
        "key_requirements": [
            "Estimate expected credit losses over the life of financial assets",
            "Consider historical loss experience, current conditions, and forecasts",
            "Apply to loans, held-to-maturity securities, and trade receivables",
        ],
        "audit_procedures": [
            "Evaluate management's CECL methodology and model",
            "Test completeness and accuracy of data inputs",
            "Assess reasonableness of economic forecasts used",
            "Perform independent estimate or sensitivity analysis",
            "Review qualitative adjustment factors",
        ],
    },
    "ASC 820": {
        "description": "Fair Value Measurement — framework for measuring fair value",
        "applicable_to": "Entities with assets/liabilities measured at fair value",
        "key_requirements": [
            "Three-level fair value hierarchy (Level 1, 2, 3)",
            "Level 3 requires significant unobservable inputs",
            "Disclosure of valuation techniques and inputs",
        ],
        "audit_procedures": [
            "Evaluate appropriateness of valuation methods",
            "Test Level 1 and 2 valuations against market data",
            "For Level 3: assess models, test inputs, perform independent valuations",
            "Review transfers between hierarchy levels",
        ],
    },
}


@tool(approval_mode="never_require")
def check_compliance_requirements(
    framework: Annotated[
        str,
        Field(description="The regulatory framework to check: 'SOX 404', 'Basel III', 'ASC 326', 'ASC 820', or 'all'"),
    ],
) -> str:
    """Look up compliance requirements and recommended audit procedures for a regulatory framework."""
    if framework.lower() == "all":
        return json.dumps(COMPLIANCE_REQUIREMENTS, indent=2)

    req = COMPLIANCE_REQUIREMENTS.get(framework)
    if req:
        return json.dumps({framework: req}, indent=2)
    return json.dumps({
        "error": f"Unknown framework: {framework}",
        "available": list(COMPLIANCE_REQUIREMENTS.keys()),
    })


@tool(approval_mode="never_require")
def assess_regulatory_risk(
    frameworks: Annotated[list[str], Field(description="List of applicable regulatory frameworks")],
    has_prior_deficiencies: Annotated[bool, Field(description="Whether prior year had deficiencies")],
    recent_system_changes: Annotated[bool, Field(description="Whether significant IT changes occurred")],
) -> str:
    """Assess overall regulatory risk level based on applicable frameworks and client factors."""
    risk_score = 0

    # More frameworks = more compliance complexity
    risk_score += len(frameworks) * 10

    # Prior deficiencies increase risk
    if has_prior_deficiencies:
        risk_score += 20

    # System changes increase risk
    if recent_system_changes:
        risk_score += 15

    # High-risk frameworks
    high_risk_frameworks = {"SOX 404", "Basel III"}
    for fw in frameworks:
        if fw in high_risk_frameworks:
            risk_score += 10

    if risk_score >= 60:
        level = "High"
    elif risk_score >= 35:
        level = "Medium"
    else:
        level = "Low"

    return json.dumps({
        "regulatory_risk_level": level,
        "risk_score": risk_score,
        "factors": {
            "framework_count": len(frameworks),
            "has_prior_deficiencies": has_prior_deficiencies,
            "recent_system_changes": recent_system_changes,
            "high_risk_frameworks_applicable": [f for f in frameworks if f in high_risk_frameworks],
        },
    }, indent=2)
