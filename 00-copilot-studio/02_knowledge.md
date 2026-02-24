# Exercise 2: Adding Knowledge Sources

In this exercise, you'll add **public website knowledge sources** to your Audit Research Assistant so it can ground its responses in authoritative audit and accounting standards content.

## What You'll Learn

- How to add public websites as knowledge sources in Copilot Studio
- How knowledge grounding improves response accuracy and relevance
- How to test and verify that knowledge sources are being used

## Background

Without knowledge sources, your agent relies solely on the LLM's training data — which may be outdated or lack specifics about audit standards. By adding knowledge sources, the agent can **retrieve and cite current content** from authoritative websites.

Copilot Studio indexes public website content and uses it to ground the agent's responses, similar to retrieval-augmented generation (RAG).

> 📖 **Reference:** [Add knowledge to your agent](https://learn.microsoft.com/en-us/microsoft-copilot-studio/knowledge-copilot-studio)

## Steps

### 1. Open the Knowledge Configuration

1. Go to your **Audit Research Assistant** agent in Copilot Studio.
2. Navigate to the **Knowledge** page (left sidebar), or on the **Overview** page select **Add knowledge** in the Knowledge section.

### 2. Add Knowledge Websites

We'll add four authoritative audit and accounting websites as knowledge sources.

1. Select **Add knowledge** → **Public websites**.
2. Enter each of the following URLs, selecting **Add** after each one:

   | Source | URL |
   |--------|-----|
   | **IAASB Standards** — International Standards on Auditing (ISAs) | `https://www.iaasb.org/standards` |
   | **PCAOB Standards** — US public company auditing standards | `https://pcaobus.org/oversight/standards` |
   | **IFAC Knowledge Gateway** — International accounting & auditing resources | `https://www.ifac.org/knowledge-gateway` |
   | **EY Insights** — Thought leadership on audit, assurance & accounting | `https://www.ey.com/en_us/insights` |

3. Once all four URLs have been added, select **Add to agent**.
4. Wait for indexing to complete (may take a moment).

### 3. Enable or Disable Web Search

In addition to the specific websites you added above, Copilot Studio can also search the **public web** (via Bing) to answer questions that fall outside your configured knowledge sources.

1. Go to **Settings** (gear icon, top right) → **Generative AI**.
2. Look for the **Web content** or **Search public websites** toggle.
3. When **enabled**, the agent can supplement its responses with results from the broader web — useful for general questions, but may return content outside your curated sources.
4. When **disabled**, the agent only uses the specific knowledge sources you've added (and the LLM's training data). This gives you tighter control over what content the agent references.

> **Recommendation for this workshop:** Leave web search **disabled** so you can clearly see when responses are grounded in your configured knowledge sources vs. the LLM's general training data.

### 4. Test Knowledge Grounding

Now test whether the agent uses these knowledge sources to ground its responses.

1. Open the **Test your agent** panel and start a new session.
2. Try these prompts and compare responses to what you saw in Exercise 1 (before knowledge was added):

   | Prompt | What to Look For |
   |--------|-----------------|
   | `What does ISA 315 say about understanding the entity and its environment?` | Should cite specific content from IAASB standards |
   | `What are PCAOB requirements for auditing accounting estimates?` | Should reference PCAOB standards content |
   | `What guidance does IFAC provide on professional skepticism?` | Should pull from IFAC knowledge gateway |
   | `What are the latest trends in audit quality?` | May reference EY Insights content |

3. Look for **citation indicators** — Copilot Studio may show source references in responses.

### 5. Compare With and Without Knowledge

To see the difference knowledge sources make:

1. Ask: `What are the key requirements of ISA 540 Revised for auditing accounting estimates?`
2. Note the response — it should include specific details from the IAASB website.
3. Now go to **Knowledge** and temporarily disable the IAASB source.
4. Ask the same question again — the response will likely be more generic, relying only on the LLM's training data.
5. Re-enable the knowledge source.

## Tips for Knowledge Sources

| Tip | Why |
|-----|-----|
| Use specific URLs, not just top-level domains | More targeted indexing, better relevance |
| Keep the number of sources manageable (4–8) | Too many sources can dilute relevance |
| Choose authoritative sources | Improves accuracy and user trust |
| Test with specific questions | Verify the right content is being retrieved |
| Check that websites allow indexing | Some sites block crawlers — test to confirm |

## Key Takeaways

- Knowledge sources give your agent **access to current, authoritative content** beyond the LLM's training data
- Grounded responses include **specific details and citations** rather than generic answers
- The agent automatically determines **when to search knowledge** vs. respond from general knowledge (with generative orchestration)
- Public websites are the simplest knowledge source — Copilot Studio also supports SharePoint, Dataverse, and uploaded files

## Next Steps

→ [Exercise 3: Adding Tools (REST APIs)](./03_tools.md)
