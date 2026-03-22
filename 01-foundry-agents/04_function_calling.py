"""
04 — Implementing Tools and Function Calling (SEC EDGAR + FRED APIs)

Wraps the same SEC EDGAR and FRED REST APIs used in the Copilot Studio
session as function tools that a Foundry agent can invoke. The agent
decides when to search for a company's CIK, pull SEC filings or financial
facts, and retrieve economic data from FRED — just like the Copilot Studio
agent does via OpenAPI connectors.

Concepts: FunctionTool, real REST API calls, tool-call loop, multi-tool chaining
"""

import json
import os
from pathlib import Path

import requests
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import RequiredFunctionToolCall
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()

OUTPUTS_DIR = Path(__file__).parent / "outputs"

# Common User-Agent header required by SEC EDGAR policy
SEC_HEADERS = {"User-Agent": "AuditWorkshopAgent/1.0 (workshop@example.com)"}

# ---------------------------------------------------------------------------
# SEC EDGAR tools — mirror the Copilot Studio OpenAPI connector
# ---------------------------------------------------------------------------

def search_edgar_filings(query: str, forms: str = "", size: int = 5) -> str:
    """Search SEC EDGAR filings by company name/ticker. Returns matching
    companies with CIK numbers and recent filing hits."""
    params = {"q": query, "size": size}
    if forms:
        params["forms"] = forms
    resp = requests.get(
        "https://efts.sec.gov/LATEST/search-index",
        params=params,
        headers=SEC_HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    # Extract the most useful pieces for the agent
    entities = []
    for bucket in data.get("aggregations", {}).get("entity_filter", {}).get("buckets", []):
        entities.append(bucket.get("key", ""))
    hits = []
    for hit in data.get("hits", {}).get("hits", [])[:5]:
        src = hit.get("_source", {})
        hits.append({
            "company": (src.get("display_names") or [""])[0],
            "form": src.get("form"),
            "file_date": src.get("file_date"),
        })
    return json.dumps({"entities": entities[:10], "filings": hits}, indent=2)


def get_company_submissions(cik: str) -> str:
    """Get filing history for a company by its 10-digit CIK."""
    cik = cik.zfill(10)
    resp = requests.get(
        f"https://data.sec.gov/submissions/CIK{cik}.json",
        headers=SEC_HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    recent = data.get("filings", {}).get("recent", {})
    filings = []
    for i in range(min(10, len(recent.get("form", [])))):
        filings.append({
            "form": recent["form"][i],
            "filingDate": recent["filingDate"][i],
            "accessionNumber": recent["accessionNumber"][i],
        })
    return json.dumps({
        "name": data.get("name"),
        "cik": data.get("cik"),
        "tickers": data.get("tickers"),
        "sic": data.get("sic"),
        "sicDescription": data.get("sicDescription"),
        "recentFilings": filings,
    }, indent=2)


def get_company_facts(cik: str) -> str:
    """Get all XBRL financial facts for a company by CIK."""
    cik = cik.zfill(10)
    resp = requests.get(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
        headers=SEC_HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    # Summarise available concepts so the response stays manageable
    summary = {"entityName": data.get("entityName"), "taxonomies": {}}
    for taxonomy, concepts in data.get("facts", {}).items():
        summary["taxonomies"][taxonomy] = list(concepts.keys())[:30]
    return json.dumps(summary, indent=2)


def get_company_concept(cik: str, taxonomy: str, tag: str) -> str:
    """Get a specific XBRL financial concept for a company over time."""
    cik = cik.zfill(10)
    resp = requests.get(
        f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{tag}.json",
        headers=SEC_HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    # Return the most recent values per unit
    result = {"tag": data.get("tag"), "label": data.get("label"), "entityName": data.get("entityName"), "units": {}}
    for unit, values in data.get("units", {}).items():
        # Keep the last 10 values (most recent filings)
        result["units"][unit] = values[-10:]
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# FRED API tools — mirror the Copilot Studio OpenAPI connector
# ---------------------------------------------------------------------------

def get_fred_series(series_id: str) -> str:
    """Get metadata for a FRED economic data series."""
    api_key = os.environ.get("FRED_API_KEY", "")
    resp = requests.get(
        "https://api.stlouisfed.org/fred/series",
        params={"series_id": series_id, "api_key": api_key, "file_type": "json"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    series_list = data.get("seriess", [])
    if series_list:
        return json.dumps(series_list[0], indent=2)
    return json.dumps({"error": f"No series found for '{series_id}'"})


def get_fred_observations(
    series_id: str,
    observation_start: str = "",
    observation_end: str = "",
    limit: int = 24,
    sort_order: str = "desc",
) -> str:
    """Get data values (observations) for a FRED economic data series."""
    api_key = os.environ.get("FRED_API_KEY", "")
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "limit": limit,
        "sort_order": sort_order,
    }
    if observation_start:
        params["observation_start"] = observation_start
    if observation_end:
        params["observation_end"] = observation_end
    resp = requests.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return json.dumps({"observations": data.get("observations", [])}, indent=2)


def search_fred_series(search_text: str, limit: int = 10) -> str:
    """Search FRED for economic data series matching keywords."""
    api_key = os.environ.get("FRED_API_KEY", "")
    resp = requests.get(
        "https://api.stlouisfed.org/fred/series/search",
        params={
            "search_text": search_text,
            "api_key": api_key,
            "file_type": "json",
            "limit": limit,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    results = []
    for s in data.get("seriess", []):
        results.append({
            "id": s.get("id"),
            "title": s.get("title"),
            "frequency": s.get("frequency"),
            "units": s.get("units"),
            "observation_end": s.get("observation_end"),
        })
    return json.dumps({"results": results}, indent=2)


# ---------------------------------------------------------------------------
# Map function names → implementations
# ---------------------------------------------------------------------------

FUNCTION_MAP = {
    "search_edgar_filings": search_edgar_filings,
    "get_company_submissions": get_company_submissions,
    "get_company_facts": get_company_facts,
    "get_company_concept": get_company_concept,
    "get_fred_series": get_fred_series,
    "get_fred_observations": get_fred_observations,
    "search_fred_series": search_fred_series,
}

# ---------------------------------------------------------------------------
# Tool schemas — these tell the agent what functions are available
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    # --- SEC EDGAR Search ---
    {
        "type": "function",
        "function": {
            "name": "search_edgar_filings",
            "description": (
                "Search SEC EDGAR filings by company name or ticker symbol to find CIK numbers "
                "and recent filings. Use this FIRST when a user asks about a company and you "
                "don't know the CIK. Extract the CIK from the results, then use other EDGAR tools."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Company name, ticker, or keywords to search for."},
                    "forms": {"type": "string", "description": "Optional comma-separated SEC form types to filter (e.g., '10-K,10-Q')."},
                    "size": {"type": "integer", "description": "Number of filing results to return (0-100). Default 5."},
                },
                "required": ["query"],
            },
        },
    },
    # --- SEC EDGAR Submissions ---
    {
        "type": "function",
        "function": {
            "name": "get_company_submissions",
            "description": (
                "Get a company's SEC filing history by CIK (Central Index Key). Returns "
                "company metadata and recent filings. CIK should be a 10-digit zero-padded "
                "number (e.g., '0000320193' for Apple)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cik": {"type": "string", "description": "10-digit CIK number (e.g., '0000320193' for Apple)."},
                },
                "required": ["cik"],
            },
        },
    },
    # --- SEC EDGAR Company Facts ---
    {
        "type": "function",
        "function": {
            "name": "get_company_facts",
            "description": (
                "Get all XBRL financial facts for a company by CIK. Returns available financial "
                "concepts (Revenue, Assets, NetIncomeLoss, etc.) organized by taxonomy. Useful "
                "for discovering what financial data is available before drilling into specifics."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cik": {"type": "string", "description": "10-digit CIK number."},
                },
                "required": ["cik"],
            },
        },
    },
    # --- SEC EDGAR Company Concept ---
    {
        "type": "function",
        "function": {
            "name": "get_company_concept",
            "description": (
                "Get historical values for a specific XBRL financial concept (e.g., Revenue, "
                "Assets, NetIncomeLoss) for a company. Returns values across multiple filing "
                "periods. Common tags: Revenue, Assets, NetIncomeLoss, AccountsPayableCurrent, "
                "StockholdersEquity."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cik": {"type": "string", "description": "10-digit CIK number."},
                    "taxonomy": {"type": "string", "enum": ["us-gaap", "ifrs-full", "dei", "srt"], "description": "XBRL taxonomy (usually 'us-gaap')."},
                    "tag": {"type": "string", "description": "XBRL concept tag name (e.g., 'Revenue', 'Assets', 'NetIncomeLoss')."},
                },
                "required": ["cik", "taxonomy", "tag"],
            },
        },
    },
    # --- FRED Series Metadata ---
    {
        "type": "function",
        "function": {
            "name": "get_fred_series",
            "description": (
                "Get metadata for a FRED economic data series. Common series: GDP, CPIAUCSL "
                "(CPI / inflation), FEDFUNDS (federal funds rate), UNRATE (unemployment), "
                "DGS10 (10-year Treasury), SP500, MORTGAGE30US."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "series_id": {"type": "string", "description": "FRED series ID (e.g., 'GDP', 'FEDFUNDS', 'UNRATE')."},
                },
                "required": ["series_id"],
            },
        },
    },
    # --- FRED Observations ---
    {
        "type": "function",
        "function": {
            "name": "get_fred_observations",
            "description": (
                "Get data values (observations) for a FRED economic series. Returns date-value "
                "pairs. Use observation_start / observation_end to filter the date range."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "series_id": {"type": "string", "description": "FRED series ID."},
                    "observation_start": {"type": "string", "description": "Start date (YYYY-MM-DD). Optional."},
                    "observation_end": {"type": "string", "description": "End date (YYYY-MM-DD). Optional."},
                    "limit": {"type": "integer", "description": "Max observations to return. Default 24."},
                    "sort_order": {"type": "string", "enum": ["asc", "desc"], "description": "Sort order by date. Default 'desc'."},
                },
                "required": ["series_id"],
            },
        },
    },
    # --- FRED Search ---
    {
        "type": "function",
        "function": {
            "name": "search_fred_series",
            "description": (
                "Search FRED for economic data series by keywords. Useful when you don't "
                "know the exact series ID. For example, search 'inflation' to find CPI "
                "series, or 'unemployment' for labor market data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "search_text": {"type": "string", "description": "Keywords to search for."},
                    "limit": {"type": "integer", "description": "Max results. Default 10."},
                },
                "required": ["search_text"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Agent instructions — mirrors the Copilot Studio agent descriptions
# ---------------------------------------------------------------------------

AGENT_INSTRUCTIONS = """\
You are an Audit Research Assistant at a professional services firm. You have
access to two sets of live data tools:

**SEC EDGAR** — Search for companies by name or ticker, look up CIK numbers,
retrieve SEC filing history, and pull XBRL financial data (revenue, assets,
net income, etc.).

**FRED (Federal Reserve Economic Data)** — Retrieve economic indicators such
as interest rates (FEDFUNDS, DGS10), inflation (CPIAUCSL), GDP, unemployment
(UNRATE), and mortgage rates (MORTGAGE30US).

Workflow:
1. When a user asks about a company's filings or financials, first use
   search_edgar_filings to find the CIK, then use the other EDGAR tools.
2. When asked about economic conditions, interest rates, or macro data, use
   the FRED tools.
3. Always explain what data you retrieved and how it's relevant to audit
   risk assessment or going-concern analysis.

Be professional, precise, and cite the data sources in your response.
"""


def main():
    client = AgentsClient(
        endpoint=os.environ["PROJECT_ENDPOINT"],
        credential=AzureCliCredential(),
    )

    # Create agent with EDGAR + FRED function tools
    agent = client.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        name="AuditResearchAgent",
        instructions=AGENT_INSTRUCTIONS,
        tools=TOOL_DEFINITIONS,
    )
    print(f"Created agent: {agent.id}")

    thread = client.threads.create()
    client.messages.create(
        thread_id=thread.id,
        role="user",
        content=(
            "I'm assessing going-concern risk for Tesla. Look up their CIK, pull "
            "their most recent revenue data, and then get the current federal funds "
            "rate and GDP growth to give me an overall economic context."
        ),
    )

    # Run with tool-call handling loop
    run = client.runs.create(thread_id=thread.id, agent_id=agent.id)
    tool_call_log: list[str] = []

    while True:
        run = client.runs.get(thread_id=thread.id, run_id=run.id)

        if run.status == "completed":
            break
        elif run.status == "requires_action":
            tool_outputs = []
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                if isinstance(tool_call, RequiredFunctionToolCall):
                    fn = FUNCTION_MAP.get(tool_call.function.name)
                    if fn:
                        args = json.loads(tool_call.function.arguments)
                        result = fn(**args)
                        log_entry = f"  Tool: {tool_call.function.name}({args})"
                        print(log_entry)
                        tool_call_log.append(log_entry)
                        tool_outputs.append({"tool_call_id": tool_call.id, "output": result})

            client.runs.submit_tool_outputs(
                thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs
            )
        elif run.status in ("failed", "cancelled", "expired"):
            print(f"Run ended with status: {run.status}")
            break

    # Print and save the final response
    response_text = ""
    if run.status == "completed":
        messages = client.messages.list(thread_id=thread.id)
        for msg in messages:
            if msg.role == "assistant":
                response_text = msg.content[0].text.value
                print(f"\nAgent response:\n{response_text}")
                break

    OUTPUTS_DIR.mkdir(exist_ok=True)
    output_file = OUTPUTS_DIR / "04_function_calling.md"
    output_parts = ["# Function Calling Results — SEC EDGAR + FRED\n"]
    if tool_call_log:
        output_parts.append("## Tool Calls\n\n```\n" + "\n".join(tool_call_log) + "\n```\n")
    output_parts.append(f"## Agent Response\n\n{response_text}\n")
    output_file.write_text("\n".join(output_parts), encoding="utf-8")
    print(f"\nResponse saved to {output_file}")

    client.delete_agent(agent.id)
    print("Agent deleted.")


if __name__ == "__main__":
    main()
