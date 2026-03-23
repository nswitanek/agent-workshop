# Exercise 4: Adding OpenAPI Tools in the Foundry Portal

In Copilot Studio Exercise 3, you connected your agent to the **SEC EDGAR** and **FRED** APIs by uploading OpenAPI specs. In this exercise, you'll do the **same thing in the Azure AI Foundry portal** — giving your Foundry agent the same API-calling capabilities using the same OpenAPI specification files.

This is the closest 1:1 parallel between the two platforms.

## What You'll Learn

- How to add OpenAPI tools to a Foundry agent in the portal
- How to configure authentication (no-auth and API key) for OpenAPI tools
- How the Foundry agent decides when to invoke tools based on user queries
- How to test tool invocation and multi-tool chaining in the portal
- How to do the same thing programmatically with the `OpenApiTool` SDK class

## Key Concept: What *Is* an OpenAPI Tool?

Understanding the relationship between an OpenAPI spec, its endpoints, and a "tool" is important — the portal interface can make this confusing at first.

### One spec file → One tool → Multiple functions

When you upload an OpenAPI spec to Foundry, you give it a single **tool name** (e.g., `sec_edgar_data`). This might seem limiting because a spec like `sec-edgar.openapi.json` defines *three* endpoints (`getCompanySubmissions`, `getCompanyConcept`, `getXBRLFrame`). The resolution:

- The **tool name** is a logical grouping — it tells the platform "these endpoints belong together."
- Each **`operationId`** in the spec becomes a separate callable function that the agent can invoke independently.
- The agent sees all the `operationId`s, reads their descriptions and parameters, and decides which one(s) to call.

Think of it like this:

| Level | What it is | Example |
|-------|-----------|---------|
| **Tool** | A named bundle — one spec file with one auth config | `sec_edgar_data` |
| **Function** | An individual endpoint the agent can call (= one `operationId`) | `getCompanySubmissions`, `getCompanyConcept`, etc. |

So when the portal asks for a **Name**, you're naming the *tool* (the bundle), not a single endpoint. The platform automatically discovers all `operationId`s inside the spec and registers each one as a function the agent can call.

### Why `operationId` matters

Every path/method in your OpenAPI spec **must** have an `operationId`. This is what the agent uses to decide which endpoint to invoke. The `operationId` becomes the function name the model "sees," so use descriptive names:

- ✅ `getCompanySubmissions` — clear what it does
- ✅ `searchFilings` — action-oriented
- ❌ `endpoint1` — the model can't reason about this

### Our specs at a glance

| Spec file | Tool name (you choose) | operationIds (auto-discovered) |
|-----------|----------------------|-------------------------------|
| `sec-edgar.openapi.json` | `sec_edgar_data` | `getCompanySubmissions`, `getCompanyConcept`, `getXBRLFrame` |
| `sec-edgar-search.openapi.json` | `sec_edgar_search` | `searchFilings` |
| `fred-api.openapi.json` | `fred_economic_data` | `getSeries`, `getSeriesObservations`, `searchSeries`, `getCategory`, `getCategorySeries` |

> **Portal vs. SDK terminology:** In the portal you fill in a "Name" field. In the SDK, this maps to the `name` parameter in `OpenApiFunctionDefinition`. Either way, it's a label for the *tool* — the individual endpoints are identified by their `operationId`s inside the spec.

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

> **⚠️ SEC EDGAR `User-Agent` Requirement:** The SEC blocks automated requests that don't include a descriptive `User-Agent` header (company name + email). The OpenAPI specs in this repo include a `User-Agent` header parameter with a default value (`AgentWorkshop/1.0 (workshop@example.com)`). If you see "Too many requests" or similar errors, this is why — see the [Troubleshooting](#troubleshooting) section at the end of this exercise.

---

## Part A: SEC EDGAR Data API (Anonymous Authentication)

The SEC EDGAR Data API provides free access to company filings and XBRL financial data. No API key is required.

### 1. Open Your Agent

1. Go to [ai.azure.com](https://ai.azure.com) and open your project.
2. In the left sidebar (or top navigation), open the **Agents** section.
3. Open an existing agent or select **Create agent** to make a new one called `AuditResearchAssistant-<your-initials>`.
4. Set the **Instructions** to:

   ```
   You are an Audit Research Assistant at a professional services firm. You have
   access to three tools:

   1. sec_edgar_search — Search SEC EDGAR by company name or ticker to find CIK
      numbers. Use this FIRST when a user asks about a company.
   2. sec_edgar_data — Retrieve SEC filing history and XBRL financial data
      (revenue, assets, net income, etc.) by CIK number.
   3. fred_economic_data — Retrieve economic indicators such as interest rates,
      inflation, GDP, unemployment, and mortgage rates from FRED.

   Workflow:
   - When asked about a company, use sec_edgar_search to find the CIK, then use
     sec_edgar_data to pull filings or financial facts.
   - When asked about economic conditions, use fred_economic_data.
   - Always explain what data you retrieved and how it relates to audit risk
     assessment.
   ```

   > **Why name the tools in the instructions?** The tool names here — `sec_edgar_search`, `sec_edgar_data`, `fred_economic_data` — match the names you'll enter when adding each OpenAPI tool in the steps below. Referencing them explicitly helps the model understand which tool to reach for.

### 2. Add the EDGAR Data API Tool

1. In the agent configuration, find the **Tools** section (or **Action tools** panel).
2. Select **Add tool** → **Browse all tools** → Select a tool **Custom** tab → **OpenAPI tool**.
3. Fill in the fields:
   - **Name:** `sec_edgar_data` — this is the *tool-level* label (it groups all endpoints in the spec under one name)
   - **Description:** `Access SEC EDGAR to retrieve company filing history and XBRL financial data by CIK number.`
4. For **Authentication**, select **Anonymous** (no authentication required).
5. In the **OpenAPI specification** box, paste the contents of [`openapi/sec-edgar.openapi.json`](./openapi/sec-edgar.openapi.json).
   > You can also upload the file if the portal offers a file-upload option.
6. Select **Save** (or **Add** / **Create tool**, depending on your portal version).

The platform parses the spec and registers each `operationId` as a callable function:
   - **getCompanySubmissions** — Get company filing history by CIK
   - **getCompanyConcept** — Get a specific financial concept over time
   - **getXBRLFrame** — Get cross-company data for a concept and period

> **Note:** The `getCompanyFacts` endpoint (which returns *all* XBRL data for a company) is intentionally excluded from this spec. Its responses are 3–5 MB per company, which exceeds the platform's message size limit. Use `getCompanyConcept` instead to retrieve specific financial metrics (e.g., Revenue, Assets, NetIncomeLoss).

> **Don't be confused** by the single "Name" field — you are naming the *tool bundle*, not a single endpoint. The agent will see all four `operationId`s and choose which to call based on the user's question.

### 3. Test the EDGAR Data Tool

In the agent's chat panel, try these prompts:

| Prompt | Expected Behavior |
|--------|-------------------|
| `Look up Apple's recent SEC filings` | Calls getCompanySubmissions with CIK 0000320193 |
| `Show me Microsoft's revenue over the last 5 years` | Calls getCompanyConcept for us-gaap/Revenues with CIK 0000789019 |
| `What was Amazon's net income trend?` | Calls getCompanyConcept for us-gaap/NetIncomeLoss |

> **Note:** The agent may struggle to find CIKs by name alone. That's expected — in Part B you'll add the search tool.

---

## Part B: SEC EDGAR Search API (Company Lookup)

The EDGAR Data API endpoints require a CIK number, but users typically know company names, not CIKs. The EDGAR Search API solves this — it lets the agent search by company name to find the CIK.

### 1. Add the EDGAR Search Tool

1. In the **Tools** section, select **Add tool** → **OpenAPI 3.0 specified tool**.
2. Fill in the fields:
   - **Name:** `sec_edgar_search`
   - **Description:** `Search SEC EDGAR filings by company name or ticker to find CIK numbers.`
3. For **Authentication**, select **Anonymous**.
4. In the **OpenAPI specification** box, paste the contents of [`openapi/sec-edgar-search.openapi.json`](./openapi/sec-edgar-search.openapi.json).
5. Select **Save** (or **Add** / **Create tool**).

This spec has just one `operationId` — **searchFilings** — so the tool and function are essentially 1:1 here.

### 2. Test Tool Chaining

With both EDGAR tools connected, the agent can now chain calls — search for a company by name, extract the CIK, then pull financial data:

| Prompt | Expected Tool Chain |
|--------|-------------------|
| `What is the CIK number for Tesla?` | searchFilings → extracts CIK |
| `Look up Nvidia's recent 10-K filings` | searchFilings → getCompanySubmissions |
| `What was Tesla's revenue last year?` | searchFilings (CIK) → getCompanyConcept (Revenue) |
| `What financial data is available for JPMorgan?` | searchFilings (CIK) → getCompanySubmissions |

> **Tip:** Notice how tool chaining works identically to Copilot Studio — the agent decides the sequence of API calls based on the user's question and the tool descriptions.

---

## Part C: FRED API (API Key Authentication)

The FRED API requires an API key, which introduces authentication configuration — the same concept as in the Copilot Studio exercise.

### 1. Add the FRED API Tool

1. In the **Tools** section, select **Add tool** → **Browse all tools** → Select a tool **Custom** tab → **OpenAPI tool** → **Create**.
2. Fill in the fields:
   - **Name:** `fred_economic_data`
   - **Description:** `Access FRED economic data — interest rates, inflation, GDP, unemployment, and more.`
3. In the **OpenAPI specification** box, paste the contents of [`openapi/fred-api.openapi.json`](./openapi/fred-api.openapi.json).
4. For **Authentication**, select **API key connection**. Then select **Create new connection** and fill in:
   - **Name:** `fred-api-connection`
   - **Authentication type:** API Key
   - **Key:** Your FRED API key
   - **Access:** This project only
5. Save the connection, then select it in the authentication dropdown.
6. Select **Save** (or **Add** / **Create tool**).

> **Connection created inline:** Unlike creating a connection separately under Connected Resources, here you create it directly in the tool configuration flow. The result is the same — A managed secret that the platform injects into API calls automatically. You can also reuse this connection for other tools later.

The platform registers all five `operationId`s as callable functions:
   - **getSeries** — Get metadata for an economic data series
   - **getSeriesObservations** — Get actual data values for a series
   - **searchSeries** — Search for series by keywords
   - **getCategory** — Get category metadata
   - **getCategorySeries** — Get series within a category

### 2. Test the FRED Tool

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
| `What were Nvidia's total assets in their latest filing?` | EDGAR Search → EDGAR Data (getCompanyConcept) |
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

## Troubleshooting

### EDGAR Search 500 / Internal Server Error

The EFTS (EDGAR Full-Text Search) server at `efts.sec.gov` can return intermittent HTTP 500 errors, especially under load. If you see this:

1. **Retry the query.** EFTS 500s are typically transient — wait a few seconds and try again.
2. **Simplify the search.** Use a shorter, quoted company name (e.g., `"Nvidia"` instead of `"Nvidia Corporation"`).
3. **Use the function-tool approach** ([`04_function_calling.py`](./04_function_calling.py)) for more reliable search with retry logic built into your code.

> **Note:** The EFTS `search-index` endpoint always returns up to 100 filing results per query (pagination via `size`/`from` is not supported on this endpoint). The most useful part for CIK lookups is the `entity_filter` aggregation, which lists matching companies with their CIK numbers.

### "Received message exceeds the maximum configured message size"

Some SEC EDGAR endpoints return very large responses. The `getCompanyFacts` endpoint in particular returns **all** XBRL-tagged financial data for a company (3–5 MB for major companies like Microsoft, Apple, or Tesla). This exceeds the Foundry platform's message size limit.

**Fix applied in this repo:** The `getCompanyFacts` endpoint has been removed from the OpenAPI spec. Use `getCompanyConcept` instead — it retrieves a specific financial metric (e.g., Revenue, Assets, NetIncomeLoss) and returns ~5 KB per request. If you need to explore what concepts are available for a company, use the function-tool approach in [`04_function_calling.py`](./04_function_calling.py) where you can truncate or filter the response in your own code.

### "Too many requests" / "Undeclared Automated Tool" errors from SEC EDGAR

The SEC blocks automated requests that don't include a `User-Agent` header identifying the caller. The error page title is *"Your Request Originates from an Undeclared Automated Tool"* but may surface in the agent as "Too many requests" or a generic tool-call failure.

**What happens:** The Foundry platform makes HTTP requests on the agent's behalf when using OpenAPI tools. If the platform doesn't send the `User-Agent` header (or sends a generic one), the SEC returns HTTP 403.

**Fix applied in this repo:** The OpenAPI specs include a `User-Agent` header parameter with a default value of `AgentWorkshop/1.0 (workshop@example.com)`. If the Foundry platform honors this parameter, requests will include the required header automatically.

**If you still see errors:**

1. **Try the function-tool approach instead.** [`04_function_calling.py`](./04_function_calling.py) makes SEC API calls from your own code using the `requests` library, where you control the `User-Agent` header directly. This is the most reliable path.

2. **Rate-limit awareness.** Even with a valid `User-Agent`, the SEC enforces a limit of **10 requests per second** per IP address. In a workshop setting with multiple participants on the same network, you may collectively exceed this limit. Space out your test queries.

3. **Verify the header is reaching SEC.** Test directly:
   ```bash
   # Should return JSON (200 OK):
   curl -H "User-Agent: YourName (your@email.com)" \
     "https://efts.sec.gov/LATEST/search-index?q=%22nvidia%22&forms=10-K&size=2"

   # Should return 403:
   curl "https://efts.sec.gov/LATEST/search-index?q=%22nvidia%22&forms=10-K&size=2"
   ```

### Foundry guardrail blocks the response

If you see *"This interaction was blocked by a safety and security control in this asset's Foundry guardrail"*, this is a project-level content filter, not an API error. This most commonly affects FRED queries but can affect any tool.

**Diagnose the cause:**

1. **Check if it's an auth/connection failure disguised as a guardrail block.** If the FRED API key isn't injected correctly, FRED returns a 400 error, and the platform may route that through the guardrail instead of showing the raw error. Verify your connection:
   - In the portal, go to your project's **Connected resources** and confirm the FRED connection exists
   - Test manually with your API key:
     ```bash
     curl "https://api.stlouisfed.org/fred/series/observations?series_id=UNRATE&file_type=json&api_key=YOUR_KEY_HERE&limit=5"
     ```
   - If this returns data, the key is valid and the issue is in the connection mapping

2. **Check your project's guardrail configuration.** In the Foundry portal:
   - Open your **project settings** → look for **Safety + security**, **Guardrails**, or **Content filtering**
   - Look for filters like **Protected material detection**, **Ungrounded content**, or **Indirect prompt injection** — these can false-positive on legitimate API responses
   - Try setting the content filter to a less restrictive level for testing

3. **Try the SEC EDGAR tools first** to confirm the guardrail isn't blocking all OpenAPI tools. If EDGAR works but FRED doesn't, the issue is likely with the FRED connection/authentication, not the guardrail itself.

4. **Workaround:** Use the function-tool approach ([`04_function_calling.py`](./04_function_calling.py)) where you control the API calls directly and return pre-formatted responses to the agent.

### FRED API returns errors

- Verify your FRED API key is valid and the connection is configured correctly.
- The FRED API key must be passed as a query parameter named `api_key`. The connection you created should map to this.

### Portal UI doesn't match these instructions

The Azure AI Foundry portal evolves frequently. The exact menu labels ("Add tool", "OpenAPI 3.0 specified tool", "Action tools") may differ from what's shown here. Look for the OpenAPI / REST API tool option in your agent's tool configuration area. The core workflow — name the tool, paste the spec, choose auth — remains the same across portal versions.

## Key Takeaways

- **One OpenAPI spec = one tool, many functions.** The tool `name` in the portal (or SDK) is a logical grouping. Each `operationId` in the spec becomes a separate function the agent can call independently.
- **`operationId` is required** on every endpoint — it becomes the function name the model reasons about. Use descriptive names.
- **OpenAPI tools in Foundry work just like Copilot Studio** — provide a spec, configure auth, and the platform handles execution
- **The same OpenAPI spec files** work in both platforms — no modifications needed
- **Authentication patterns are equivalent** — no-auth/anonymous, API key via connection, or managed identity
- **Tool chaining is automatic** — both platforms let the agent decide the sequence of API calls
- **The SDK's `OpenApiTool` class** is the code equivalent of adding tools in the portal — the platform still executes the APIs
- **Function tools** (Exercise 4b) give you full control but require you to implement the API calls yourself

## Next Steps

- → [`04_function_calling.md`](./04_function_calling.md) — Learn the function-tool approach (your code calls the APIs) for more control over response shaping and error handling
- → [`05_conversation_state.py`](./05_conversation_state.py) — Working with memory and conversation state
