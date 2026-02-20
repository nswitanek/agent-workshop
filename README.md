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
   git clone <repo-url>
   cd agent-workshop
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your Azure credentials and endpoints
   ```

4. **Authenticate with Azure:**
   ```bash
   az login
   ```

## Repository Structure

```
01-foundry-agents/     # Session 1: Building Agents in Microsoft Foundry
02-maf-agents/         # Session 2: Code-First Agents with MAF
03-capstone/           # Capstone: Multi-Agent Risk-Based Audit Planning
```

Each folder contains a README with detailed instructions and numbered Python scripts to run in order.
