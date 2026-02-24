# Exercise 3: Adding Tools — REST API Connections

In this exercise, you'll connect your Audit Research Assistant to two public REST APIs using OpenAPI specifications, giving it the ability to **look up real SEC filings** and **retrieve live economic data**.

## What You'll Learn

- How to add REST API tools to a Copilot Studio agent using OpenAPI specs
- How to configure API authentication (no-auth and API key)
- How the agent decides when to invoke tools based on user queries

## Background

Tools extend what your agent can *do* — instead of only answering from knowledge and training data, tools let the agent **call external APIs** to retrieve real-time data and perform actions.

Copilot Studio supports REST API tools via **OpenAPI specifications** — you upload a spec file that describes the API's endpoints, and the agent learns how to call them.

> 📖 **Reference:** [Add REST API tools](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agent-extend-action-rest-api)

## Prerequisites

- A **FRED API key** (free) — register at [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html)
- The OpenAPI spec files from this repository:
  - [`openapi/sec-edgar.openapi.json`](./openapi/sec-edgar.openapi.json)
  - [`openapi/fred-api.openapi.json`](./openapi/fred-api.openapi.json)

## Part A: SEC EDGAR API (No Authentication)

The SEC EDGAR API provides free access to company filings and XBRL financial data. No API key is required.

### 1. Add the EDGAR API Tool

1. Go to your **Audit Research Assistant** agent in Copilot Studio.
2. Navigate to the **Tools** page → select **Add a tool**.
3. Select **New tool** → **REST API**.
4. Upload the file [`openapi/sec-edgar.openapi.json`](./openapi/sec-edgar.openapi.json) from this repository.
5. Review the detected endpoints:
   - **getCompanySubmissions** — Get company filing history by CIK
   - **getCompanyFacts** — Get all XBRL financial facts for a company
   - **getCompanyConcept** — Get a specific financial concept over time
   - **getXBRLFrame** — Get cross-company data for a concept and period
6. Select **Next**.

### 2. Configure Description

Update the description to help the agent know when to use this tool:

> Access SEC EDGAR to retrieve company filing history, financial statements, and XBRL data. Use this tool when users ask about SEC filings, 10-K reports, 10-Q reports, company financial data, revenue, assets, liabilities, or any publicly filed financial information. The tool uses CIK (Central Index Key) numbers — common CIKs include Apple (0000320193), Microsoft (0000789019), Amazon (0001018724), Google/Alphabet (0001652044).

Select **Next**.

### 3. Configure Authentication

1. For authentication, select **None** — the SEC EDGAR API is free and requires no authentication.
2. Select **Next**.

### 4. Select Endpoints

1. Review the available operations and select all four endpoints.
2. Select **Next** → **Create**.
3. Select **Add and configure** to add the tool to your agent.

### 5. Test the EDGAR Tool

Open the test panel and try these prompts:

| Prompt | Expected Behavior |
|--------|-------------------|
| `Look up Apple's recent SEC filings` | Calls getCompanySubmissions with CIK 0000320193 |
| `What is Microsoft's total revenue from their latest filing?` | Calls getCompanyFacts or getCompanyConcept |
| `Show me Amazon's net income over the last 5 years` | Calls getCompanyConcept for NetIncomeLoss |
| `Compare accounts payable across all companies for Q1 2023` | Calls getXBRLFrame |

> **Note:** The agent may ask you for the CIK number if it doesn't know it. You can update the tool description with additional CIK mappings or instruct the agent in its system instructions to look up CIKs.

---

## Part B: FRED API (API Key Authentication)

The FRED API from the Federal Reserve Bank of St. Louis provides economic data — interest rates, inflation, GDP, unemployment, and thousands of other indicators.

### 1. Add the FRED API Tool

1. Navigate to the **Tools** page → select **Add a tool**.
2. Select **New tool** → **REST API**.
3. Upload the file [`openapi/fred-api.openapi.json`](./openapi/fred-api.openapi.json) from this repository.
4. Review the detected endpoints:
   - **getSeries** — Get metadata for an economic data series
   - **getSeriesObservations** — Get actual data values for a series
   - **searchSeries** — Search for series by keywords
   - **getCategory** / **getCategorySeries** — Browse data by category
5. Select **Next**.

### 2. Configure Description

Update the description:

> Access the Federal Reserve Economic Data (FRED) API to retrieve economic indicators and financial data. Use this tool when users ask about interest rates (FEDFUNDS, DGS10), inflation (CPIAUCSL), GDP, unemployment rate (UNRATE), mortgage rates (MORTGAGE30US), S&P 500 (SP500), or any macroeconomic data relevant to audit risk assessment and going-concern analysis.

Select **Next**.

### 3. Configure Authentication

1. For authentication, select **API key**.
2. Configure the API key parameters:
   - **Parameter label:** `FRED API Key`
   - **Parameter name:** `api_key`
   - **Parameter location:** `Query`
3. Select **Next**.

> **Note:** At runtime, the agent will prompt users to enter their FRED API key the first time it needs to call the API.

### 4. Select Endpoints and Create

1. Select all five endpoints.
2. Select **Next** → **Create**.
3. Select **Add and configure** to add the tool to your agent.

### 5. Test the FRED API Tool

Open the test panel and try these prompts:

| Prompt | Expected Behavior |
|--------|-------------------|
| `What is the current federal funds rate?` | Calls getSeriesObservations for FEDFUNDS |
| `Show me GDP growth over the last 5 years` | Calls getSeriesObservations for GDP |
| `Search for inflation-related economic indicators` | Calls searchSeries |
| `What is the current 10-year Treasury rate?` | Calls getSeriesObservations for DGS10 |
| `What are the latest unemployment figures?` | Calls getSeriesObservations for UNRATE |

When prompted for authentication, enter your FRED API key.

---

## Part C: Using Both Tools Together

Now that both tools are connected, test prompts that require the agent to **reason about which tool to use** — or use both:

| Prompt | Expected Tool(s) |
|--------|-------------------|
| `I'm assessing going-concern risk for a retail company. What's the current economic outlook?` | FRED (GDP, unemployment, consumer sentiment) |
| `Look up Apple's latest 10-K and tell me their revenue trend` | EDGAR (companyfacts or companyconcept) |
| `For an audit of a bank, what interest rate data should I consider?` | FRED (FEDFUNDS, DGS10, MORTGAGE30US) |
| `Pull Apple's revenue data and compare it against GDP growth` | Both EDGAR and FRED |

## Key Takeaways

- **OpenAPI specs** are the bridge between your agent and external APIs — invest in clear descriptions
- **Tool descriptions** are critical — the agent uses them to decide *when* to call a tool
- **Authentication** can be per-user (API key prompt) or maker-provided (shared credentials)
- The agent **automatically decides** which tool to call based on the user's question (with generative orchestration)
- Copilot Studio auto-converts OpenAPI 3.0 specs to Swagger 2.0 internally

## Common CIK Numbers for Testing

| Company | CIK |
|---------|-----|
| Apple Inc. | 0000320193 |
| Microsoft Corp. | 0000789019 |
| Amazon.com Inc. | 0001018724 |
| Alphabet Inc. (Google) | 0001652044 |
| JPMorgan Chase & Co. | 0000019617 |
| Goldman Sachs Group | 0000886982 |

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
| `INDPRO` | Industrial Production Index |

## Next Steps

→ [Exercise 4: Understanding Orchestration](./04_orchestration.md)
