# AI Agent and Workflow Creation Workshop

Hands-on workshop for building AI agents using **Microsoft Foundry** (`azure-ai-projects` SDK) and the **Microsoft Agent Framework** (`agent-framework` SDK), with examples themed around professional services / assurance practice.

## Workshop Agenda

| Time | Session |
|------|---------|
| 1:30 – 3:00 | [Building Agents in Microsoft Foundry](./01-foundry-agents/) |
| 3:00 – 3:15 | Break |
| 3:15 – 4:30 | [Code-First Agents with Microsoft Agent Framework](./02-maf-agents/) |
| Capstone | [Multi-Agent Risk-Based Audit Planning](./03-capstone/) |

## Learning Goals

- Understand the core components of AI agents (instructions, tools, knowledge, memory, orchestration, guardrails)
- Build functional AI agents using both Copilot Studio and Microsoft Foundry
- Gain hands-on experience creating agents that solve real-world scenarios
- Understand when to use different platforms based on requirements and constraints
- Build familiarity with the Microsoft Agent Framework (MAF) for code-first agent development

## Prerequisites

- Python 3.11+
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
   ```bash
   # macOS / Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. **Create a virtual environment and install dependencies with `uv`:**
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install --pre -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
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
01-foundry-agents/     # Session 1: Building Agents in Microsoft Foundry
02-maf-agents/         # Session 2: Code-First Agents with MAF
03-capstone/           # Capstone: Multi-Agent Risk-Based Audit Planning
```

Each folder contains a README with detailed instructions and numbered Python scripts to run in order.
