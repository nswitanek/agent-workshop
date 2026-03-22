"""
04 — OpenAPI Tools (SEC EDGAR + FRED APIs)

Loads the same OpenAPI spec files used in Copilot Studio and attaches them
to a Foundry agent using the OpenApiTool class. The platform executes the
API calls — no manual function-call loop needed. This is the closest SDK
equivalent to the Copilot Studio OpenAPI connector pattern.

Concepts: OpenApiTool, OpenAPI specs, platform-managed API execution, connections
"""

import json
import os
from pathlib import Path

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    AgentStreamEvent,
    OpenApiAnonymousAuthDetails,
    OpenApiConnectionAuthDetails,
    OpenApiConnectionSecurityScheme,
    OpenApiTool,
)
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = Path(__file__).parent
OUTPUTS_DIR = SCRIPT_DIR / "outputs"
OPENAPI_DIR = SCRIPT_DIR / "openapi"

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
   the EDGAR search tool to find the CIK, then use the other EDGAR tools.
2. When asked about economic conditions, interest rates, or macro data, use
   the FRED tools.
3. Always explain what data you retrieved and how it's relevant to audit
   risk assessment or going-concern analysis.

Be professional, precise, and cite the data sources in your response.
"""


def load_spec(filename: str) -> dict:
    """Load an OpenAPI spec JSON file from the openapi/ directory."""
    spec_path = OPENAPI_DIR / filename
    with open(spec_path, encoding="utf-8") as f:
        return json.load(f)


def main():
    client = AgentsClient(
        endpoint=os.environ["PROJECT_ENDPOINT"],
        credential=AzureCliCredential(),
    )

    # --- Load OpenAPI specs (same files used in Copilot Studio) ---
    edgar_data_spec = load_spec("sec-edgar.openapi.json")
    edgar_search_spec = load_spec("sec-edgar-search.openapi.json")
    fred_spec = load_spec("fred-api.openapi.json")

    # --- SEC EDGAR tools (anonymous auth — no API key needed) ---
    # This is the SDK equivalent of uploading the spec in the portal
    # and selecting "Anonymous" for authentication.
    anon_auth = OpenApiAnonymousAuthDetails()

    edgar_tool = OpenApiTool(
        name="sec_edgar_data",
        description=(
            "Access SEC EDGAR to retrieve company filing history, financial "
            "statements, and XBRL data. Use when users ask about SEC filings, "
            "10-K reports, 10-Q reports, company financial data, revenue, assets, "
            "liabilities, or any publicly filed financial information."
        ),
        spec=edgar_data_spec,
        auth=anon_auth,
    )

    # Add the search API as a second definition on the same tool,
    # or create a separate tool — either approach works.
    edgar_search_tool = OpenApiTool(
        name="sec_edgar_search",
        description=(
            "Search SEC EDGAR filings by company name or ticker to find CIK "
            "numbers. Use this FIRST when a user asks about a company and you "
            "don't already know the CIK. Extract the CIK from results, then "
            "use the SEC EDGAR Data tool with that CIK."
        ),
        spec=edgar_search_spec,
        auth=anon_auth,
    )

    # --- FRED API tool (API key via connection) ---
    # In the portal, you created a "fred-api-connection" connection.
    # In code, you reference that connection ID. The platform injects
    # the API key into requests automatically.
    #
    # If you haven't created a connection, you can fall back to
    # anonymous auth for testing (requests will fail without a key)
    # or set up the connection first per the portal instructions.
    fred_connection_id = os.environ.get("FRED_CONNECTION_ID", "")

    if fred_connection_id:
        fred_auth = OpenApiConnectionAuthDetails(
            security_scheme=OpenApiConnectionSecurityScheme(
                connection_id=fred_connection_id,
            ),
        )
    else:
        # Fallback: anonymous auth (FRED calls will fail without a key,
        # but this lets you test the agent creation flow)
        print(
            "Warning: FRED_CONNECTION_ID not set. FRED API calls may fail.\n"
            "Create a connection in Foundry and add FRED_CONNECTION_ID to .env\n"
            "See 04_openapi_tools.md Part C for instructions.\n"
        )
        fred_auth = OpenApiAnonymousAuthDetails()

    fred_tool = OpenApiTool(
        name="fred_economic_data",
        description=(
            "Access FRED economic data — interest rates (FEDFUNDS, DGS10), "
            "inflation (CPIAUCSL), GDP, unemployment (UNRATE), mortgage rates "
            "(MORTGAGE30US), and thousands of other indicators."
        ),
        spec=fred_spec,
        auth=fred_auth,
    )

    # --- Combine all tool definitions ---
    all_tools = (
        edgar_tool.definitions
        + edgar_search_tool.definitions
        + fred_tool.definitions
    )

    # --- Create the agent ---
    agent = client.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],
        name="AuditResearchAgent-OpenAPI",
        instructions=AGENT_INSTRUCTIONS,
        tools=all_tools,
    )
    print(f"Created agent: {agent.id}")

    # --- Send a test message ---
    thread = client.threads.create()
    client.messages.create(
        thread_id=thread.id,
        role="user",
        content=(
            "I'm assessing going-concern risk for Tesla. Look up their CIK, "
            "pull their most recent revenue data, and then get the current "
            "federal funds rate and GDP growth to give me an overall economic context."
        ),
    )

    # --- Stream the response ---
    # With OpenAPI tools, the platform executes the API calls for us.
    # No manual tool-call loop is needed — the agent handles everything.
    OUTPUTS_DIR.mkdir(exist_ok=True)
    output_file = OUTPUTS_DIR / "04_openapi_tools.md"
    response_chunks: list[str] = []
    tool_calls_seen: list[str] = []

    print("\nStreaming response:")
    with client.runs.stream(thread_id=thread.id, agent_id=agent.id) as stream:
        for event_type, event_data, _ in stream:
            if event_type == AgentStreamEvent.THREAD_RUN_STEP_COMPLETED:
                if event_data.type == "tool_calls":
                    for tool_call in event_data.step_details.tool_calls:
                        tc_dict = tool_call if isinstance(tool_call, dict) else tool_call.as_dict()
                        tc_type = tc_dict.get("type", "unknown")
                        if tc_type == "open_api":
                            api_info = tc_dict.get("open_api", {})
                            name = api_info.get("name", "unknown")
                            log_entry = f"  OpenAPI call: {name}"
                            print(log_entry)
                            tool_calls_seen.append(log_entry)
            elif event_type == AgentStreamEvent.THREAD_MESSAGE_DELTA:
                for part in event_data.delta.content:
                    if hasattr(part, "text") and part.text:
                        text = part.text.value
                        print(text, end="", flush=True)
                        response_chunks.append(text)
    print()

    # --- Save output ---
    response_text = "".join(response_chunks)
    output_parts = ["# OpenAPI Tools Results — SEC EDGAR + FRED\n"]
    if tool_calls_seen:
        output_parts.append(
            "## Tool Calls\n\n```\n" + "\n".join(tool_calls_seen) + "\n```\n"
        )
    output_parts.append(f"## Agent Response\n\n{response_text}\n")
    output_file.write_text("\n".join(output_parts), encoding="utf-8")
    print(f"\nResponse saved to {output_file}")

    # Clean up
    client.delete_agent(agent.id)
    print("Agent deleted.")


if __name__ == "__main__":
    main()
