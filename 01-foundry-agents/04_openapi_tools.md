# Exercise 4: Adding OpenAPI Tools in the Foundry Portal

In Copilot Studio Exercise 3, you connected your agent to the **SEC EDGAR** and **FRED** APIs by uploading OpenAPI specs. In this exercise, you'll do the **same thing in the Azure AI Foundry portal** — giving your Foundry agent the same API-calling capabilities using the same OpenAPI specification files.

This is the closest 1:1 parallel between the two platforms.

## What You'll Learn

- How to add OpenAPI tools to a Foundry agent in the portal
- How to configure authentication (no-auth and API key) for OpenAPI tools
- How the Foundry agent decides when to invoke tools based on user queries
- How to test tool invocation and multi-tool chaining in the portal
- How to do the same thing programmatically with the `OpenApiTool` SDK class

## Copilot Studio vs. Foundry Portal — Side by Side

| Aspect | Copilot Studio | Foundry Portal |
|--------|---------------|----------------|
| **Add a tool** | Tools → Add a tool → REST API | Agent → Tools → OpenAPI |
| **Spec format** | Upload OpenAPI `.json` | Upload OpenAPI `.json` |
| **Auth (no-auth)** | Select "None" | Select "Anonymous" |
| **Auth (API key)** | Configure key name + location | Use a Foundry connection or provide key |
| **Description** | Written in tool config | Written in tool config |
| **Execution** | Platform calls the API | Platform calls the API |
| **Tool chaining** | Automatic via orchestration | Automatic via orchestration |

> **Key similarity:** In both platforms, you upload the same OpenAPI spec file and the platform handles API execution. You don't write any code to call the API — the agent does it for you.

## Prerequisites

- An agent created in the Azure AI Foundry portal (from [Exercise 0](./00_portal_agent.md))
- A **FRED API key** (free) — register at [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html)
- The OpenAPI spec files from this repository (same ones used in Copilot Studio):
  - [`openapi/sec-edgar.openapi.json`](./openapi/sec-edgar.openapi.json) — company filings and XBRL data
  - [`openapi/sec-edgar-search.openapi.json`](./openapi/sec-edgar-search.openapi.json) — company CIK lookup
  - [`openapi/fred-api.openapi.json`](./openapi/fred-api.openapi.json) — economic indicators

---

## Part A: SEC EDGAR Data API (Anonymous Authentication)

The SEC EDGAR Data API provides free access to company filings and XBRL financial data. No API key is required.

### 1. Open Your Agent

1. Go to [ai.azure.com](https://ai.azure.com) and open your project.
2. Navigate to **Build** → **Agents**.
3. Open an existing agent or create a new one called `AuditResearchAssistant-<your-initials>`.
4. Set the **Instructions** to:

   ```
   You are an Audit Research Assistant at a professional services firm. You have
   access to SEC EDGAR and FRED economic data tools. When a user asks about a
   company's SEC filings or financial data, first search for the company's CIK
   number, then use the EDGAR data tools to retrieve filings and financial facts.
   When asked about economic conditions, use the FRED tools. Always explain what
   data you retrieved and how it relates to audit risk assessment.
   ```

### 2. Add the EDGAR Data API Tool

1. In the agent configuration, find the **Tools** section.
2. Select **Add tool** → **OpenAPI**.
3. Upload the file [`openapi/sec-edgar.openapi.json`](./openapi/sec-edgar.openapi.json).
4. Review the detected endpoints:
   - **getCompanySubmissions** — Get company filing history by CIK
   - **getCompanyFacts** — Get all XBRL financial facts for a company
   - **getCompanyConcept** — Get a specific financial concept over time
   - **getXBRLFrame** — Get cross-company data for a concept and period
5. For **Authentication**, select **Anonymous** (no authentication required).
6. Save the tool configuration.

### 3. Test the EDGAR Data Tool

In the agent's chat panel, try these prompts:

| Prompt | Expected Behavior |
|--------|-------------------|
| `Look up Apple's recent SEC filings` | Calls getCompanySubmissions with CIK 0000320193 |
| `What are the available financial data points for Microsoft?` | Calls getCompanyFacts with CIK 0000789019 |
| `Show me Amazon's revenue over the last 5 years` | Calls getCompanyConcept for Revenues |

> **Note:** The agent may struggle to find CIKs by name alone. That's expected — in Part B you'll add the search tool.

---

## Part B: SEC EDGAR Search API (Company Lookup)

The EDGAR Data API endpoints require a CIK number, but users typically know company names, not CIKs. The EDGAR Search API solves this — it lets the agent search by company name to find the CIK.

### 1. Add the EDGAR Search Tool

1. In the **Tools** section, select **Add tool** → **OpenAPI**.
2. Upload the file [`openapi/sec-edgar-search.openapi.json`](./openapi/sec-edgar-search.openapi.json).
3. Review the single detected endpoint:
   - **searchFilings** — Search EDGAR filings by company name, ticker, or keywords
4. For **Authentication**, select **Anonymous**.
5. Save the tool configuration.

### 2. Test Tool Chaining

With both EDGAR tools connected, the agent can now chain calls — search for a company by name, extract the CIK, then pull financial data:

| Prompt | Expected Tool Chain |
|--------|-------------------|
| `What is the CIK number for Tesla?` | searchFilings → extracts CIK |
| `Look up Nvidia's recent 10-K filings` | searchFilings → getCompanySubmissions |
| `What was Tesla's revenue last year?` | searchFilings (CIK) → getCompanyConcept (Revenue) |
| `What financial data is available for JPMorgan?` | searchFilings (CIK) → getCompanyFacts |

> **Tip:** Notice how tool chaining works identically to Copilot Studio — the agent decides the sequence of API calls based on the user's question and the tool descriptions.

---

## Part C: FRED API (API Key Authentication)

The FRED API requires an API key, which introduces authentication configuration — the same concept as in the Copilot Studio exercise.

### 1. Create a Connection for the FRED API Key

Before adding the tool, set up a connection in your Foundry project so the API key is stored securely:

1. In your project, go to **Management** → **Connected resources**.
2. Select **New connection** → **Custom keys**.
3. Configure the connection:
   - **Name:** `fred-api-connection`
   - **Key name:** `api_key`
   - **Key value:** Your FRED API key
   - **Access:** This project only
4. Save the connection.

> **Why a connection?** In Copilot Studio, the platform prompted the user to enter the API key at runtime. In Foundry, you store it as a **connection** — a managed secret that the platform injects into API calls automatically.

### 2. Add the FRED API Tool

1. In the **Tools** section, select **Add tool** → **OpenAPI**.
2. Upload the file [`openapi/fred-api.openapi.json`](./openapi/fred-api.openapi.json).
3. Review the detected endpoints:
   - **getSeries** — Get metadata for an economic data series
   - **getSeriesObservations** — Get actual data values for a series
   - **searchSeries** — Search for series by keywords
4. For **Authentication**, select **Connection** and choose the `fred-api-connection` you created.
5. Save the tool configuration.

### 3. Test the FRED Tool

| Prompt | Expected Behavior |
|--------|-------------------|
| `What is the current federal funds rate?` | Calls getSeriesObservations for FEDFUNDS |
| `Show me GDP growth over the last 5 years` | Calls getSeriesObservations for GDP |
| `Search for inflation-related economic indicators` | Calls searchSeries |
| `What is the current unemployment rate?` | Calls getSeriesObservations for UNRATE |

---

## Part D: Using All Tools Together

Now that all three OpenAPI tools are connected, test prompts that require the agent to reason across multiple APIs — just like in Copilot Studio Part D:

| Prompt | Expected Tools |
|--------|---------------|
| `I'm assessing going-concern risk for a retail company. What's the current economic outlook?` | FRED (GDP, UNRATE, FEDFUNDS) |
| `Look up Tesla's revenue trend and compare against GDP growth` | EDGAR Search → EDGAR Data + FRED |
| `What were Nvidia's total assets in their latest filing?` | EDGAR Search → EDGAR Data |
| `For an audit of a bank, what interest rate data should I consider?` | FRED (FEDFUNDS, DGS10, MORTGAGE30US) |
| `Pull Apple's net income and compare it against the unemployment rate` | EDGAR Data + FRED |

---

## Part E: Doing It in Code — `OpenApiTool` SDK

Everything you just did in the portal can also be done programmatically using the `OpenApiTool` class. See [`04_openapi_tools.py`](./04_openapi_tools.py) for a working example.

The SDK approach loads the same OpenAPI spec files and passes them to the agent:

```python
from azure.ai.agents.models import OpenApiTool, OpenApiAnonymousAuthDetails

# Load the OpenAPI spec
with open("openapi/sec-edgar.openapi.json") as f:
    edgar_spec = json.load(f)

# Create an OpenAPI tool — the platform handles API execution
edgar_tool = OpenApiTool(
    name="sec_edgar_data",
    description="Access SEC EDGAR company filings and XBRL financial data.",
    spec=edgar_spec,
    auth=OpenApiAnonymousAuthDetails(),
)

# Attach to the agent — no function-call loop needed
agent = client.create_agent(
    model=os.environ["MODEL_DEPLOYMENT_NAME"],
    name="AuditResearchAgent",
    instructions=AGENT_INSTRUCTIONS,
    tools=edgar_tool.definitions,
)
```

> **Key difference from function tools (`04_function_calling.py`):** With `OpenApiTool`, the platform executes the API calls for you — just like Copilot Studio. With function tools, *your* code executes the API calls, giving you more control but requiring more work.

### Comparison: Three Ways to Give an Agent API Access

| Approach | Tool definition | Who calls the API? | Control level |
|----------|-----------------|--------------------|---------------|
| **Copilot Studio** | Upload OpenAPI spec in portal | Platform | Low (portal config) |
| **Foundry Portal** | Upload OpenAPI spec in portal | Platform | Low (portal config) |
| **Foundry SDK — `OpenApiTool`** | Load spec in code | Platform | Medium (code + platform) |
| **Foundry SDK — Function tools** | Define schemas as dicts | Your code | High (full control) |

Run the SDK version:

```bash
cd 01-foundry-agents
python 04_openapi_tools.py
```

---

## Common CIK Numbers for Testing

| Company | CIK |
|---------|-----|
| Apple Inc. | 0000320193 |
| Microsoft Corp. | 0000789019 |
| Amazon.com Inc. | 0001018724 |
| Alphabet Inc. (Google) | 0001652044 |
| Tesla Inc. | 0001318605 |
| JPMorgan Chase & Co. | 0000019617 |

## Common FRED Series IDs for Testing

| Series ID | Description |
|-----------|-------------|
| `GDP` | Gross Domestic Product |
| `FEDFUNDS` | Federal Funds Effective Rate |
| `CPIAUCSL` | Consumer Price Index (All Urban Consumers) |
| `UNRATE` | Unemployment Rate |
| `DGS10` | 10-Year Treasury Constant Maturity Rate |
| `SP500` | S&P 500 Index |
| `MORTGAGE30US` | 30-Year Fixed Rate Mortgage Average |

## Key Takeaways

- **OpenAPI tools in Foundry work just like Copilot Studio** — upload a spec, configure auth, and the platform handles execution
- **The same OpenAPI spec files** work in both platforms — no modifications needed
- **Authentication patterns are equivalent** — no-auth/anonymous, API key via connection, or managed identity
- **Tool chaining is automatic** — both platforms let the agent decide the sequence of API calls
- **The SDK's `OpenApiTool` class** is the code equivalent of adding tools in the portal — the platform still executes the APIs
- **Function tools** (Exercise 4b) give you full control but require you to implement the API calls yourself

## Next Steps

- → [`04_function_calling.md`](./04_function_calling.md) — Learn the function-tool approach (your code calls the APIs) for more control over response shaping and error handling
- → [`05_conversation_state.py`](./05_conversation_state.py) — Working with memory and conversation state
