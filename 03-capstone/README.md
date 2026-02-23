# Capstone: Multi-Agent Risk-Based Audit Planning

A multi-agent scenario built on the **Microsoft Agent Framework (MAF)** that demonstrates how specialized AI agents collaborate to produce a **risk-based audit plan** for a new client engagement.

## Scenario

Your firm has been engaged to perform the annual financial statement audit for **Apex Financial Group**, a publicly traded financial services company. The audit planning process involves:

1. **Risk Assessment** — Identify and assess inherent and fraud risks
2. **Controls Evaluation** — Evaluate the design and operating effectiveness of internal controls
3. **Audit Plan Generation** — Produce a risk-based audit plan with procedures mapped to identified risks

## Architecture

```
  ┌──────────────────────────────────────────────────────┐
  │          ConcurrentBuilder (Phase 1)                 │
  │  ┌──────────────────┐  ┌──────────────────────────┐  │
  │  │  Risk Assessor   │  │  Control Evaluator       │  │
  │  │  @tools:         │  │  @tools:                 │  │
  │  │  - financials    │  │  - compliance checker    │  │
  │  │  - ratios        │  │  - regulatory risk       │  │
  │  └──────────────────┘  └──────────────────────────┘  │
  └───────────────┬──────────────────────┬───────────────┘
                  │  risk report         │  controls report
                  └──────────┬───────────┘
                             ▼
                  ┌──────────────────────┐
                  │  Audit Plan Writer   │  ← Phase 2
                  │  (synthesizes both)  │
                  └──────────────────────┘
                             │
                             ▼
                  outputs/audit_plan.md
```

**Flow:**
1. Risk Assessor and Control Evaluator run **concurrently** via `ConcurrentBuilder`
2. Their outputs feed into the Audit Plan Writer **sequentially**
3. `AgentMiddleware` and `FunctionMiddleware` track timing and tool usage throughout

## MAF Concepts Demonstrated

| Concept | Where |
|---------|-------|
| **ConcurrentBuilder** | Phase 1 — parallel agent execution | 
| **@tool decorator** | `tools/financial_data.py`, `tools/compliance_checker.py` |
| **AgentMiddleware** | `PlanningPhaseLogger` — wraps each agent run with timing |
| **FunctionMiddleware** | `ToolCallLogger` — instruments individual tool calls |
| **Agent specialization** | Each agent has focused instructions + tools |
| **Output writing** | Final plan saved to `outputs/audit_plan.md` |

## Files

| File | Purpose |
|------|---------|
| `audit_planner.py` | Main orchestrator with middleware — run this |
| `agents/risk_assessor.py` | Risk assessment agent instructions |
| `agents/control_evaluator.py` | Controls evaluation agent instructions |
| `agents/audit_plan_writer.py` | Audit plan generation agent instructions |
| `tools/financial_data.py` | `@tool`: fetch client financials, compute ratios |
| `tools/compliance_checker.py` | `@tool`: check compliance requirements, assess regulatory risk |
| `data/sample_client.json` | Sample client data for Apex Financial Group |

## Running

```bash
cd 03-capstone
python audit_planner.py
```

Output will be saved to `outputs/audit_plan.md`.
