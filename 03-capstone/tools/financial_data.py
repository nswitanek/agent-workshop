"""
Financial Data Tool

Provides access to client financial data for the risk assessment agent.
Simulates querying a data source for client financials, prior audit results,
and industry benchmarks.
"""

import json
import os
from typing import Annotated

from agent_framework import tool
from pydantic import Field

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load sample client data
with open(os.path.join(SCRIPT_DIR, "..", "data", "sample_client.json")) as f:
    CLIENT_DATA = json.load(f)


@tool(approval_mode="never_require")
def get_client_financials(
    section: Annotated[
        str,
        Field(description="The data section to retrieve: 'overview', 'financials', 'prior_audit', or 'all'"),
    ],
) -> str:
    """Retrieve financial and client data for Apex Financial Group."""
    if section == "overview":
        return json.dumps(CLIENT_DATA["client"], indent=2)
    elif section == "financials":
        return json.dumps(CLIENT_DATA["financials"], indent=2)
    elif section == "prior_audit":
        return json.dumps(CLIENT_DATA["prior_year_audit"], indent=2)
    elif section == "all":
        return json.dumps(CLIENT_DATA, indent=2)
    else:
        return json.dumps({"error": f"Unknown section: {section}. Use 'overview', 'financials', 'prior_audit', or 'all'."})


@tool(approval_mode="never_require")
def compute_financial_ratios(
    total_revenue: Annotated[float, Field(description="Total revenue")],
    net_income: Annotated[float, Field(description="Net income")],
    total_assets: Annotated[float, Field(description="Total assets")],
    total_liabilities: Annotated[float, Field(description="Total liabilities")],
) -> str:
    """Compute key financial ratios for risk assessment."""
    equity = total_assets - total_liabilities
    ratios = {
        "profit_margin": round(net_income / total_revenue * 100, 2) if total_revenue else 0,
        "return_on_assets": round(net_income / total_assets * 100, 2) if total_assets else 0,
        "return_on_equity": round(net_income / equity * 100, 2) if equity else 0,
        "debt_to_equity": round(total_liabilities / equity, 2) if equity else 0,
        "leverage_ratio": round(total_assets / equity, 2) if equity else 0,
    }
    return json.dumps(ratios, indent=2)
