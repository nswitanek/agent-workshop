# Session: Building Agents in Copilot Studio

This session walks you through creating an AI agent in **Microsoft Copilot Studio** — a low-code/no-code platform for building conversational agents. You'll configure instructions, add knowledge sources, connect to external APIs as tools, explore orchestration modes, set up memory, and configure triggers.

All exercises use the **Copilot Studio web portal** at [copilotstudio.microsoft.com](https://copilotstudio.microsoft.com). No coding is required — the exercises guide you step-by-step through the portal UI.

> **Theme:** You'll build an **Audit Research Assistant** — an agent that helps auditors research standards, look up company filings, and retrieve economic data relevant to financial statement audits.

## Prerequisites

- Access to [Microsoft Copilot Studio](https://copilotstudio.microsoft.com) (trial or licensed)
- A Microsoft 365 or Power Platform environment
- For Exercise 3 (Tools): A free [FRED API key](https://fred.stlouisfed.org/docs/api/api_key.html) — register before the session

## Exercises

| # | Exercise | What You'll Learn |
|---|----------|-------------------|
| 1 | [Instructions](./01_instructions.md) | Create an agent and configure its system instructions |
| 2 | [Knowledge](./02_knowledge.md) | Add public websites as knowledge sources for grounding |
| 3 | [Tools](./03_tools.md) | Connect to REST APIs (SEC EDGAR, FRED) using OpenAPI specs |
| 4 | [Orchestration](./04_orchestration.md) | Understand generative vs. classic orchestration |
| 5 | [Memory](./05_memory.md) | Configure conversation memory and variables |
| 6 | [Triggers](./06_triggers.md) | Set up topic triggers, event triggers, and inactivity prompts |

## Files in This Folder

```
00-copilot-studio/
├── README.md                          # This file
├── 01_instructions.md                 # Exercise 1: Create agent + instructions
├── 02_knowledge.md                    # Exercise 2: Knowledge sources
├── 03_tools.md                        # Exercise 3: REST API tools
├── 04_orchestration.md                # Exercise 4: Orchestration modes
├── 05_memory.md                       # Exercise 5: Memory and variables
├── 06_triggers.md                     # Exercise 6: Triggers
├── openapi/
│   ├── sec-edgar.openapi.json         # OpenAPI 3.0 spec — SEC EDGAR (no auth)
│   └── fred-api.openapi.json          # OpenAPI 3.0 spec — FRED API (API key)
└── data/
    └── sample_prompts.md              # Test prompts for each exercise
```

## Key Documentation

- [Copilot Studio — Get Started](https://learn.microsoft.com/en-us/microsoft-copilot-studio/fundamentals-get-started)
- [Add Knowledge Sources](https://learn.microsoft.com/en-us/microsoft-copilot-studio/knowledge-copilot-studio)
- [Add Tools to an Agent](https://learn.microsoft.com/en-us/microsoft-copilot-studio/advanced-plugin-actions)
- [REST API Tools](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agent-extend-action-rest-api)
- [Generative Orchestration](https://learn.microsoft.com/en-us/microsoft-copilot-studio/advanced-generative-actions)
- [Triggers](https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-triggers)
- [Variables](https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-variables)
