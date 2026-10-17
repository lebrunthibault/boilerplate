# Authoritative sources on LLM engineering patterns

Vendor engineering blogs, official docs and recognized practitioners. For **pattern and
architecture topics** (agents vs workflows, LLM-as-judge, evals, structured output,
prompting, cost), these carry MORE weight than user repos — they distill thousands of
production deployments. Use them alongside real OSS repos found for the topic (repos show *how
it's coded*, these sources show *what the right pattern is*). All URLs verified 2026-06-14.

## Anthropic

Engineering blog index: `https://www.anthropic.com/engineering`

- [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
  — THE foundational text: the 5 workflow patterns (chaining, routing, parallelization,
  orchestrator-workers, evaluator-optimizer) vs agents, and when agents are warranted.
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
  — production multi-agent lessons; the 15× token figure; when parallelism pays.
- [Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
  (2025-09-11) — tool/schema design; directly applicable to designing typed enrichment functions.
- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  (2025-09-29) — what to put in a prompt/context and how to structure it (relevant to EvidenceBundle design).
- [Code execution with MCP: building more efficient agents](https://www.anthropic.com/engineering/code-execution-with-mcp)
  (2025-11-04) — load tools on demand and filter data in code before it hits the model;
  reports ~98% token reduction on a representative workflow (cost/latency lever).
- [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
  (2026-01-09) — designing eval suites, automated vs human grading.
- [Claude cookbook](https://www.anthropic.com/cookbook) (repo:
  [anthropics/claude-cookbooks](https://github.com/anthropics/claude-cookbooks)) — runnable
  notebooks; most relevant: building evals (`misc-building-evals`), agent patterns
  (`agent-patterns-evaluator-optimizer`, `agent-patterns-context-engineering`), tool use,
  RAG, prompt caching.
- Docs (canonical host `platform.claude.com/docs`):
  [prompt engineering overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview) ·
  [prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) ·
  [tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview) ·
  [define success criteria / evals](https://platform.claude.com/docs/en/test-and-evaluate/define-success)

## Pydantic (check here FIRST for implementation topics)

- [Case studies](https://pydantic.dev/case-studies) — production Pydantic AI deployments
  (agentic RAG, agent evaluation platforms, AI security at Sophos).
- [Multi-agent applications](https://pydantic.dev/docs/ai/guides/multi-agent-applications/)
  — the complexity ladder: single agent → delegation → programmatic hand-off → graphs;
  their own advice is plain code first.
- [Graphs](https://pydantic.dev/docs/ai/graph/graph/) — and their caution: "if you're not
  confident a graph-based approach is a good idea, it might be unnecessary".
- [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/) — code-first eval framework
  (datasets, cases, evaluators, LLM judges).
- [Testing agents](https://pydantic.dev/docs/ai/guides/testing/) — TestModel/FunctionModel
  to unit-test LLM code without API calls.
- [Structured output](https://pydantic.dev/docs/ai/core-concepts/output/) — output modes
  (tool/native/prompted), validators, streaming.
- [Articles](https://pydantic.dev/articles) — observability & cost-focused essays (Logfire).

## LangChain

- [langchain-ai/langchain](https://github.com/langchain-ai/langchain) — the ecosystem repo.
- [Workflows vs agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
  — the canonical framing of the deterministic-vs-agentic decision.
- [How to build a custom agent harness](https://www.langchain.com/blog/how-to-build-a-custom-agent-harness)
  — agent = model + harness; middleware for context delivery and tool lifecycle.
- [Fault tolerance in LangGraph](https://www.langchain.com/blog/fault-tolerance-in-langgraph)
  — retry/timeout/error-handler primitives for production LLM pipelines.
- [Introducing Rubrics](https://www.langchain.com/blog/introducing-rubrics-for-deepagents)
  — grader sub-agent reviewing outputs against criteria (LLM-as-judge applied to agents).
- [Model neutrality](https://www.langchain.com/blog/model-neutrality) — multi-provider
  routing, avoiding lock-in.

## OpenAI

- [A practical guide to building agents (PDF)](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)
  — orchestration patterns, model selection, guardrails, from customer deployments.
- [Cookbook](https://developers.openai.com/cookbook) — topics: agents, evals, guardrails,
  optimization.
- [Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
  — designing evals for production model behavior.

## Mistral

- [Structured output](https://docs.mistral.ai/capabilities/structured_output/) — custom
  structured outputs vs JSON mode, provider-specific behavior of our extraction calls.
- [Evaluation cookbook](https://docs.mistral.ai/resources/cookbooks/mistral-evaluation-evaluation)
  — metrics-based, code-based, and LLM-as-judge evaluation with rubric scoring.
- [Prompting best practices](https://docs.mistral.ai/models/best-practices) — system prompt
  design, few-shot, formatting — tuned for the models we actually run.
- [mistralai/cookbook](https://github.com/mistralai/cookbook) — agents, evaluation,
  function calling, prompting notebooks.

## Recognized practitioners (evals & LLM-as-judge especially)

The base techniques in the 2023/2024 posts still hold; the 2025/2026 pieces below reflect
where the field moved (error analysis as the foundation, criteria drift, meta-evaluating the
LLM-judge itself, retrieval/enrichment eval taxonomies). Start with the newer ones.

- Hamel Husain — [LLM Evals: Everything You Need to Know](https://hamel.dev/blog/posts/evals-faq/)
  (2026-01-15) — the current flagship: error analysis as the cornerstone of any eval
  strategy, with LLM-as-judge positioned as one tool among many. Start here. Still canonical:
  [Creating a LLM-as-a-Judge that drives business results](https://hamel.dev/blog/posts/llm-judge/)
  (the 7-step judge framework: domain expert, binary pass/fail + critiques, iterate; kept
  up to date) and [Your AI product needs evals](https://hamel.dev/blog/posts/evals/)
  (the 3-level eval strategy).
- Eugene Yan (now at Anthropic) —
  [An LLM-as-Judge Won't Save The Product—Fixing Your Process Will](https://eugeneyan.com/writing/eval-process/)
  (2025-04-20; eval-driven development, monitoring AI output — supersedes the old "eval
  process" framing),
  [Evaluating Long-Context Question & Answer Systems](https://eugeneyan.com/writing/qa-evals/)
  (2025-06-22; how to build eval datasets + methodology),
  [Product Evals in Three Simple Steps](https://eugeneyan.com/writing/product-evals/)
  (2025-11-23; label data → align LLM-evaluators → run the harness on every change),
  [Evaluating the Effectiveness of LLM-Evaluators](https://eugeneyan.com/writing/llm-evaluators/)
  (meta-eval: how to check the LLM-judge itself), and the older
  [Patterns for building LLM systems](https://eugeneyan.com/writing/llm-patterns/).
- Shreya Shankar (co-teaches the evals course with Hamel) —
  [Who Validates the Validators?](https://arxiv.org/abs/2404.12272) — the **criteria drift**
  result: you need criteria to grade outputs, but grading outputs is what reveals the
  criteria. Eval is an iterative human sensemaking loop, not a fixed target — the theory
  behind the posts above.
- Jason Liu — retrieval/enrichment evals: [There Are Only 6 RAG Evals](https://jxnl.co/writing/2025/05/19/there-are-only-6-rag-evals/)
  (2025-05-19; the Question/Context/Answer diagnostic grid) and
  [Systematically Improving RAG Applications](https://jxnl.co/writing/2025/01/24/systematically-improving-rag-applications/)
  (2025-01-24; the metrics → diagnose → improve loop).
- Lilian Weng — [LLM-powered autonomous agents](https://lilianweng.github.io/posts/2023-06-23-agent/)
  — the reference taxonomy (planning, memory, tool use).
- Chip Huyen — [Common AI engineering pitfalls](https://huyenchip.com/2025/01/16/ai-engineering-pitfalls.html)
  (2025; incl. over-relying on AI-as-judge, premature complexity) and the older
  [Building LLM applications for production](https://huyenchip.com/2023/04/11/llm-engineering.html);
  the bulk of her 2025 material is in the *AI Engineering* book / [aie-book](https://github.com/chiphuyen/aie-book) repo.
- Braintrust — [The six generations of AI agents and how to eval them](https://www.braintrust.dev/blog/six-generations-ai-agents/),
  [Evals are the new PRD](https://www.braintrust.dev/blog/evals-are-the-new-prd/),
  [Golden datasets with human review](https://www.braintrust.dev/blog/human-review-golden-datasets/)
  (production traces → labeled golden dataset).

## How to choose for a given topic

| Topic | Lean on |
|---|---|
| Agents vs workflows / orchestration | Anthropic Building Effective Agents, LangGraph workflows-vs-agents, OpenAI agents guide |
| LLM-as-judge / rubrics | Hamel judge post + evals-FAQ, Eugene Yan llm-evaluators (meta-eval), Mistral evaluation cookbook, Anthropic demystifying-evals, LangChain Rubrics, Braintrust |
| Evals & regression | Hamel evals-FAQ, Pydantic Evals, Eugene Yan eval-process + product-evals, Shreya Shankar (criteria drift), Anthropic define-success, Braintrust golden datasets |
| Retrieval / enrichment evals (DNS/WHOIS/SERP collection) | Jason Liu 6-RAG-evals + systematically-improving-RAG, Eugene Yan qa-evals |
| Structured output / extraction | Pydantic AI output docs, Mistral structured output, Instructor (repo list) |
| Tool / enrichment function design | Anthropic writing-tools-for-agents, advanced tool use docs |
| Prompt & context engineering | Anthropic context-engineering + prompt docs, Mistral best practices, Eugene Yan patterns |
| Cost / latency / caching | Anthropic prompt caching docs + code-execution-with-MCP, multi-agent post (token economics), Pydantic articles |
| Testing LLM code without API calls | Pydantic AI testing docs |
| Production reliability / fault tolerance | LangChain fault-tolerance, Chip Huyen pitfalls |

Note: the Langfuse blog was checked and is not fetchable (404s) — use the Langfuse repo
and its in-repo docs instead.
