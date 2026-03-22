# AI Agent and Workflow Creation Workshop

Hands-on workshop for building AI agents using **Microsoft Foundry** (`azure-ai-projects` SDK) and the **Microsoft Agent Framework** (`agent-framework` SDK), with examples themed around professional services / assurance practice.

## Workshop Agenda (11 AM – 5 PM ET)

### Morning Session (11:00 AM – 12:45 PM ET)

| Time | Session |
|------|---------|
| 11:00 – 11:15 | **Introduction to Agentic AI** |
| | • What makes an agent agentic |
| | • Core agent components and architecture |
| | • Overview of Microsoft's agent platforms |
| 11:15 – 12:45 | [**Hands-on: Agents in Copilot Studio**](./00-copilot-studio/) |
| | • Setting up your first agent and configuring instructions |
| | • Adding knowledge sources and grounding |

### Lunch (12:45 – 1:15 PM ET)

### Afternoon Session (1:15 – 5:00 PM ET)

| Time | Session |
|------|---------|
| 1:15 – 2:15 | [**Hands-on: Agents in Copilot Studio (cont.)**](./00-copilot-studio/) |
| | • Integrating tools (REST APIs, connectors) |
| | • Orchestration, memory, and triggers |
| 2:15 – 2:30 | **Break** |
| 2:30 – 2:45 | [**Agents in Microsoft Foundry — Portal**](./01-foundry-agents/00_portal_agent.md) |
| | • Creating an agent in the Azure AI Foundry portal |
| | • Mapping portal UI to SDK concepts |
| 2:45 – 3:30 | [**Foundry Agents in Code**](./01-foundry-agents/) |
| | • Creating your first Foundry agent with the SDK |
| | • Configuring instructions and system prompts |
| | • Adding knowledge (file search, vector stores) |
| | • Implementing tools and function calling |
| | • Working with memory and conversation state |
| 3:30 – 3:45 | [**Agents with Microsoft Agent Framework**](./02-maf-agents/) |
| | • Introduction to MAF |
| | • Agent orchestration patterns (other topics may be addressed in a future workshop) |
| 3:45 – 4:00 | **Break** |
| 4:00 – 4:45 | **Agents Brainstorm** |
| | • Identifying agents for professional services firm workflows |
| | • Prioritizing by business value and implementation complexity |
| | • Guidance on getting to Version 0 |
| 4:45 – 5:00 | **Wrap-up, Day 2 Preview, and Q&A** |
| | • Comparing approaches: when to use each platform |
| | • Preview of Day 2: Tools, memory, and evaluation |
| | • Open discussion |

---

## Day 2 Agenda (11 AM – 5 PM ET)

### Morning Session (11:00 AM – 12:30 PM ET)

| Time | Session |
|------|---------|
| 11:00 – 11:15 | **Day 1 Recap and Day 2 Overview** |
| | • Review: agents, instructions, knowledge, conversation state |
| | • Day 2 goals: tools, memory, evaluation, iterative improvement |
| 11:15 – 12:00 | [**Foundry Agent Tools**](./01-foundry-agents/04_openapi_tools.md) |
| | • OpenAPI tools in the Foundry portal (mirroring Copilot Studio connectors) |
| | • OpenAPI tools via SDK (`OpenApiTool` class) |
| | • [Function calling with SEC EDGAR + FRED APIs](./01-foundry-agents/04_function_calling.md) |
| | • Comparing approaches: Copilot Studio connectors vs. portal vs. SDK |
| 12:00 – 12:30 | [**Agent Memory**](./01-foundry-agents/05_conversation_state.md) |
| | • Threads and short-term conversation state |
| | • [Long-term memory with the Foundry Memory Service](./01-foundry-agents/06_memory.md) |
| | • Memory stores, scopes, user profiles, and chat summaries |
| | • Comparison: Copilot Studio variables/Dataverse vs. Foundry Memory Service |

### Lunch (12:30 – 1:00 PM ET)

### Afternoon Session (1:00 – 5:00 PM ET)

| Time | Session |
|------|---------|
| 1:00 – 1:30 | **Agent Memory (cont.) — Hands-on** |
| | • Running the memory exercises |
| | • MemorySearchTool vs. direct memory store APIs |
| | • Multi-session memory demo |
| 1:30 – 2:30 | [**Evaluating Foundry Agents**](./01-foundry-agents/07_evaluations.md) |
| | • Why evaluate: moving from "try a few questions" to quantified quality |
| | • Evaluator categories: quality, agentic, safety, NLP |
| | • The synthetic audit evaluation dataset |
| | • Running baseline evaluation (instructions only) |
| | • Adding tools and measuring improvement |
| | • Prompt optimization and measuring improvement |
| 2:30 – 2:45 | **Break** |
| 2:45 – 3:30 | **Evaluations Hands-on + Foundry Portal** |
| | • Navigating the Evaluation dashboard |
| | • Comparing runs side-by-side (baseline → tools → enhanced) |
| | • Per-row drill-down: where did tools help most? |
| | • Prompt optimizer (portal feature walkthrough) |
| 3:30 – 4:15 | **Iterative Improvement Lab** |
| | • Add memory to the eval agent and measure impact |
| | • Custom evaluators for audit-specific quality |
| | • Expand the eval dataset with new scenarios |
| | • Safety evaluators and responsible AI checks |
| 4:15 – 4:30 | **Break** |
| 4:30 – 4:50 | **Wrap-up Discussion** |
| | • Lessons learned: what improved scores and what didn't |
| | • Building an evaluation-driven agent development workflow |
| | • Production readiness: continuous evaluation and monitoring |
| 4:50 – 5:00 | **Q&A and Next Steps** |
| | • Resources for further learning |
| | • Open discussion |

---

## Learning Goals

- Understand the core components of AI agents (instructions, tools, knowledge, memory, orchestration, guardrails)
- Build functional AI agents using both Copilot Studio and Microsoft Foundry
- Gain hands-on experience creating agents that solve real-world scenarios
- Understand when to use different platforms based on requirements and constraints
- Build familiarity with the Microsoft Agent Framework (MAF) for code-first agent development

## Prerequisites

> **First time?** See the full [Environment Setup & Prerequisites](./SETUP.md) checklist for detailed platform access, RBAC roles, and verification steps.

- Python 3.10+
- An Azure subscription with access to Azure AI Foundry
- Azure CLI installed and authenticated (`az login`)
- An Azure OpenAI deployment (e.g., `gpt-4o`)

## Setup

1. **Clone this repository:**
   ```bash
   git clone https://github.com/nswitanek/agent-workshop
   cd agent-workshop
   ```

2. **Install `uv` (if needed):**

   macOS / Linux:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   Windows (PowerShell):
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. **Create a virtual environment and install dependencies:**

   macOS / Linux:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install --pre -r requirements.txt
   ```

   Windows (PowerShell):
   ```powershell
   uv venv
   .venv\Scripts\activate
   uv pip install --pre -r requirements.txt
   ```

4. **Configure environment variables:**

   macOS / Linux:
   ```bash
   cp .env.example .env
   # Edit .env with your Azure credentials and endpoints
   ```

   Windows (PowerShell):
   ```powershell
   copy .env.example .env
   # Edit .env with your Azure credentials and endpoints
   ```

5. **Authenticate with Azure:**
   ```bash
   az login
   ```

## Run Scripts in VS Code

1. Open the `agent-workshop` folder in VS Code.
2. Select the Python interpreter from `.venv`:
   - `Ctrl+Shift+P` → **Python: Select Interpreter** → choose `.venv`.
3. Open the script you want to run (for example, `01-foundry-agents/01_first_agent.py`).
4. Run it using either option:
   - Click **Run Python File** (top-right in the editor), or
   - Use the terminal:
     ```bash
     python 01-foundry-agents/01_first_agent.py
     ```

Run scripts in order within each folder (`01_`, `02_`, `03_`, etc.) as described in each session README.

## Repository Structure

```
00-copilot-studio/         # Session: Building Agents in Copilot Studio
01-foundry-agents/         # Session 1: Building Agents in Microsoft Foundry
02-maf-agents/             # Session 2: Code-First Agents with MAF
03-capstone/               # Capstone: Multi-Agent Risk-Based Audit Planning
```

Each folder contains a README with detailed instructions and numbered Python scripts to run in order.
