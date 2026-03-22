# Exercise 4: Implementing Tools — SEC EDGAR + FRED APIs

In the Copilot Studio session, you connected your Audit Research Assistant to the **SEC EDGAR** and **FRED** REST APIs by uploading OpenAPI specs. In this exercise, you'll build the same capabilities as **function tools** that a Foundry agent invokes via the Azure AI Agents SDK — giving you full code-level control over API calls, response shaping, and the tool-call execution loop.

## What You'll Learn

- How to wrap REST APIs as function tools for a Foundry agent
- How to define tool schemas (the SDK equivalent of OpenAPI specs)
- How the agent decides which tool(s) to call based on the user's query
- How the tool-call loop works (agent requests → you execute → agent continues)
- How to chain multiple tools (search for CIK → pull financials + economic data)

## Copilot Studio vs. Foundry SDK

| Aspect | Copilot Studio | Foundry SDK (`04_function_calling.py`) |
|--------|---------------|---------------------------------------|
| **Tool definition** | Upload an OpenAPI `.json` spec | Define tool schemas as Python dicts |
| **API execution** | Platform calls the API for you | Your code calls the API via `requests` |
| **Authentication** | Configured in the portal UI | Handled in your Python functions (env vars) |
| **Response handling** | Platform passes full API response to model | You shape the response before returning it |
| **Tool chaining** | Agent auto-chains across tools | Same — agent decides the sequence |
| **Customization** | Limited to OpenAPI spec | Full control — filtering, error handling, summarizing |

## Prerequisites

- Complete the [setup steps](../README.md#setup) (`.env` with `PROJECT_ENDPOINT` and `MODEL_DEPLOYMENT_NAME`)
- A **FRED API key** (free) — register at [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html)
- Add `FRED_API_KEY=your_key_here` to your `.env` file
- The `requests` library (already in the environment)

> **Note:** The SEC EDGAR APIs require no authentication — only a descriptive `User-Agent` header, which the code provides.

## The APIs

These are the same three APIs used in Copilot Studio Exercise 3, now wrapped as Python functions:

### SEC EDGAR Search API (`search_edgar_filings`)
- **Base URL:** `https://efts.sec.gov/LATEST/search-index`
- **Purpose:** Search by company name/ticker to find CIK numbers
- **Auth:** None
- **Copilot Studio equivalent:** `sec-edgar-search.openapi.json` → `searchFilings`

### SEC EDGAR Data API (`get_company_submissions`, `get_company_facts`, `get_company_concept`)
- **Base URL:** `https://data.sec.gov`
- **Purpose:** Retrieve filing history, XBRL financial facts, and specific financial concepts
- **Auth:** None (User-Agent header required)
- **Copilot Studio equivalent:** `sec-edgar.openapi.json` → `getCompanySubmissions`, `getCompanyFacts`, `getCompanyConcept`

### FRED API (`get_fred_series`, `get_fred_observations`, `search_fred_series`)
- **Base URL:** `https://api.stlouisfed.org`
- **Purpose:** Economic indicators — GDP, interest rates, inflation, unemployment
- **Auth:** API key (query parameter)
- **Copilot Studio equivalent:** `fred-api.openapi.json` → `getSeries`, `getSeriesObservations`, `searchSeries`

## Code Walkthrough

### Part A: Understanding the Tool Functions

Open `04_function_calling.py` and review the Python functions. Each wraps a REST API call:

```python
def search_edgar_filings(query: str, forms: str = "", size: int = 5) -> str:
    """Search SEC EDGAR filings by company name/ticker."""
    # Calls https://efts.sec.gov/LATEST/search-index
    # Returns entities with CIK numbers + recent filing hits
```

**Key pattern:** Each function accepts typed parameters, calls the API with `requests.get()`, and returns a JSON string. The agent receives this JSON as the tool output and incorporates it into its response.

Compare this to Copilot Studio where the platform auto-generates the API call from the OpenAPI spec — here you have full control over:
- Which fields to extract (response shaping)
- How many results to return
- Error handling and timeouts

### Part B: Understanding the Tool Schemas

The `TOOL_DEFINITIONS` list tells the agent what functions are available, what they do, and what parameters they accept. This is the SDK equivalent of uploading an OpenAPI spec in Copilot Studio:

```python
{
    "type": "function",
    "function": {
        "name": "search_edgar_filings",
        "description": "Search SEC EDGAR filings by company name or ticker...",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Company name, ticker, or keywords"},
                "forms": {"type": "string", "description": "Optional form type filter"},
                "size":  {"type": "integer", "description": "Number of results"},
            },
            "required": ["query"],
        },
    },
}
```

> **Tip:** Good descriptions are critical. The agent uses them to decide *when* to call a tool and *how* to fill in parameters — just like in Copilot Studio where you wrote descriptions for each OpenAPI connector.

### Part C: Understanding the Tool-Call Loop

In Copilot Studio, tool execution is automatic. In the SDK, you implement the loop yourself:

```
1. Agent receives the user message
2. Agent decides to call one or more tools → run.status == "requires_action"
3. Your code executes the functions and submits results
4. Agent uses the results to continue reasoning
5. Repeat until agent has enough data → run.status == "completed"
```

This loop is in the `main()` function. The agent may call multiple tools in sequence (e.g., search for CIK → get company concept → get FRED data) before producing a final response.

### Part D: Running the Example

```bash
cd 01-foundry-agents
python 04_function_calling.py
```

The example asks:
> *"I'm assessing going-concern risk for Tesla. Look up their CIK, pull their most recent revenue data, and then get the current federal funds rate and GDP growth to give me an overall economic context."*

You should see the agent chain multiple tool calls:

| Step | Tool Called | Purpose |
|------|-----------|---------|
| 1 | `search_edgar_filings("Tesla")` | Find Tesla's CIK |
| 2 | `get_company_concept(cik, "us-gaap", "Revenue")` | Get Tesla's revenue history |
| 3 | `get_fred_observations("FEDFUNDS")` | Get current federal funds rate |
| 4 | `get_fred_observations("GDP")` | Get recent GDP data |

The agent's final response will synthesize all of this into a going-concern risk assessment.

## Exercises

### Exercise 1: Try Different Prompts

Run the script with different user messages by editing the `content` string in `main()`. Try these — they mirror the Copilot Studio test prompts:

| Prompt | Expected Tools |
|--------|---------------|
| `What is Microsoft's total revenue trend over the last 3 years?` | `search_edgar_filings` → `get_company_concept` |
| `What's the current unemployment rate and how has it changed?` | `get_fred_observations("UNRATE")` |
| `Look up Nvidia's recent 10-K filings` | `search_edgar_filings("Nvidia", forms="10-K")` |
| `For an audit of a bank, what interest rate data should I consider?` | `search_fred_series` and/or `get_fred_observations` |
| `Pull Apple's net income and compare against GDP growth` | `get_company_concept` + `get_fred_observations` |

### Exercise 2: Add a New Tool

Add the `getXBRLFrame` endpoint as a new function tool. This endpoint retrieves cross-company data for a single XBRL concept and period (e.g., all companies' accounts payable for Q1 2023).

1. Write a `get_xbrl_frame(taxonomy, tag, units, frame)` function that calls:
   ```
   https://data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{units}/{frame}.json
   ```
2. Add the tool schema to `TOOL_DEFINITIONS`
3. Add the function to `FUNCTION_MAP`
4. Test with: *"Compare accounts payable across all companies for Q1 2023"*

### Exercise 3: Add Response Shaping

The current `get_company_facts` function returns a summary of available concepts. Enhance it to:
1. Accept an optional `concept` parameter (e.g., "Revenue")
2. If provided, drill into that specific concept and return the last 5 years of values
3. If omitted, return the summary of available concepts (current behavior)

### Exercise 4: Error Handling

What happens if the agent passes an invalid CIK? Try adding error handling:
1. Catch HTTP errors (404, 429, etc.) and return a user-friendly JSON error
2. Return `{"error": "Company not found for CIK ..."}` instead of crashing
3. The agent should then pivot and try a different approach (e.g., search first)

## Key Takeaways

- **Function tools are the SDK equivalent of OpenAPI connectors** — you define schemas (like specs) and implement the API calls (like the platform's auto-execution)
- **Response shaping is your advantage** — unlike Copilot Studio which passes the full API response, you can filter, summarize, and transform data before the agent sees it
- **The tool-call loop gives you control** — you can add logging, caching, rate limiting, and error recovery
- **Tool descriptions drive agent behavior** — invest in clear descriptions, just like in Copilot Studio
- **Multi-tool chaining works the same way** — the agent reasons about which tools to call and in what order, regardless of platform
