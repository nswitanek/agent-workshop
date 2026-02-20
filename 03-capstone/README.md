# Capstone: Multi-Agent Risk-Based Audit Planning

A multi-agent scenario that demonstrates how specialized AI agents collaborate to produce a **risk-based audit plan** for a new client engagement.

## Scenario

Your firm has been engaged to perform the annual financial statement audit for **Apex Financial Group**, a publicly traded financial services company. The audit planning process involves:

1. **Risk Assessment** — Identify and assess inherent and control risks
2. **Controls Evaluation** — Evaluate the design and operating effectiveness of internal controls
3. **Audit Plan Generation** — Produce a risk-based audit plan with procedures mapped to identified risks

## Architecture

```
                    ┌─────────────────────┐
                    │   Audit Planner      │
                    │   (Orchestrator)     │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │    Risk       │  │   Control    │  │  Audit Plan  │
   │   Assessor    │  │  Evaluator   │  │   Writer     │
   │              │  │              │  │              │
   │  Tools:      │  │  Tools:      │  │  Receives:   │
   │  - financial │  │  - compliance│  │  - risk report│
   │    data      │  │    checker   │  │  - controls  │
   │              │  │              │  │    report    │
   └──────────────┘  └──────────────┘  └──────────────┘
```

**Flow:**
1. Risk Assessor and Control Evaluator run **concurrently** (they're independent)
2. Their outputs feed into the Audit Plan Writer **sequentially**
3. The orchestrator coordinates everything and produces the final plan

## Files

| File | Purpose |
|------|---------|
| `audit_planner.py` | Main orchestrator — run this to execute the scenario |
| `agents/risk_assessor.py` | Risk assessment agent definition |
| `agents/control_evaluator.py` | Controls evaluation agent definition |
| `agents/audit_plan_writer.py` | Audit plan generation agent definition |
| `tools/financial_data.py` | Tool: fetch client financial data |
| `tools/compliance_checker.py` | Tool: check regulatory compliance requirements |
| `data/sample_client.json` | Sample client data for Apex Financial Group |

## Running

```bash
cd 03-capstone
python audit_planner.py
```

## Key Concepts Demonstrated

- **Multi-agent orchestration** — concurrent + sequential patterns
- **Custom tools** — domain-specific data retrieval and analysis
- **Agent specialization** — each agent has focused instructions and capabilities
- **Data flow** — outputs from one agent feed into another
- **Professional services context** — real-world audit planning workflow
