---
name: oss-best-practices
description: Research how to do something well in this project by combining your own knowledge with evidence from real, comparable OSS repositories on GitHub. Use when the user asks to "find OSS best practices on X", "trouve les best practices open source sur ce sujet", "comment font les autres projets open source pour Y", or wants a topic studied against reference repos or authoritative engineering sources (Anthropic, OpenAI, Pydantic AI, FastAPI, LangChain, Mistral…) before making a decision.
---

# OSS best practices research

Study a topic against how comparable open-source projects actually do it, then give
the project a concrete, opinionated recommendation. The point is **evidence, not vibes**:
every claim should be backed either by your reasoning or by a real repo you looked at.

## What this project is (so you pick relevant references)

Read `CONSTITUTION.md` (mission, tech stack) and `docs/vocabulary.md` first. Baseline stack:
FastAPI, PostgreSQL (async SQLAlchemy), Alembic, Vue 3 dashboard, Docker on a single VPS.
List the project's distinguishing traits from those documents (domain, data flows, any LLM or
scoring component) and weight references by how many of these traits they share.

## Workflow

1. **Frame the topic.** Restate what's being studied in one sentence and pin it to a
   project decision (e.g. "how to paginate admin lists").
   If the topic is vague, ask one clarifying question, then proceed.

2. **Think first, from your own knowledge.** Before touching GitHub, write down what you
   already know: the common approaches, their trade-offs, and a tentative recommendation.
   This is the baseline the repo evidence will confirm or correct.

3. **Pick references.** Choose 3-6 sources that genuinely match the project on the
   traits above — not just any popular OSS. Reference file:
   - [references/authoritative-sources.md](references/authoritative-sources.md) — vendor
     engineering blogs, official docs, recognized practitioners (show *what the right
     pattern is*). For **pattern/architecture topics** (agents vs workflows, LLM-as-judge,
     evals, structured output, prompting, cost), consult this FIRST — the big players'
     guidance outweighs user repos on these subjects.

   Then add topic-specific ones via `WebSearch`. Prefer sources that *actually solved the
   exact problem* over merely famous ones. A good mix is 2-4 authoritative sources + 2-4
   repos. State why each was chosen (which traits it shares).

4. **Go look — don't guess.** For each reference, get real evidence:
   - `WebSearch` for "<project> <topic>" to find the relevant code/docs/discussions,
   - `WebFetch` the actual source file, README section, docs page, or issue/ADR. Quote or
     cite the specific file/section — a path or URL, not "I believe Haystack does X".
   - If the question is deep or spans several repos, fan out with **subagents** (see below)
     so each repo is investigated in parallel and independently.

5. **Compare and decide.** Synthesize into:
   - a short **comparison** (what each reference does for this topic, in a table when it helps),
   - **convergence** (what most good projects agree on — usually the safe default),
   - **divergence** (where they differ and why — usually driven by a trait the project may or
     may not share),
   - a **recommendation for the project** that respects its constraints (async Python,
     FastAPI, PostgreSQL, Vue 3 dashboard — cf. `CONSTITUTION.md`), with the rejected
     alternatives named.

6. **Cite sources.** End with a `Sources:` list of every repo file / docs page / issue you
   actually used, as markdown links. No uncited claims about what a project does.

## Depth: solo vs. subagents

- **Shallow** (one focused question, 1-3 references): do it inline. Think, fetch a few
  sources, recommend.
- **Deep** (broad topic, comparison across many repos, or "be thorough"): use the `Agent`
  tool to fan out — **one subagent per reference repo** (or per sub-question), each tasked to
  return structured findings (approach, key files/links, trade-offs, applicability to an
  async Python FastAPI codebase). Then you synthesize. This keeps each repo's
  investigation isolated and lets them run in parallel. Give each subagent the project's
  trait list so it judges applicability, and tell it to cite real files/URLs.

  If the user explicitly opted into heavy multi-agent orchestration ("use a workflow",
  "ultracode"), a `Workflow` (pipeline: per-repo investigate -> verify -> synthesize) is the
  scaled-up version of the same shape. Default to plain `Agent` subagents otherwise.

## Guardrails

- **Match the project, not popularity.** A 40k-star framework from another domain is a weaker
  reference than a 2k-star project that solved the exact problem. Exception:
  the vendor guides in `authoritative-sources.md` (Anthropic, OpenAI, Pydantic AI,
  LangChain, Mistral) are admissible even outside the project's domain — they distill
  thousands of production deployments. Cite them for the *pattern*, not the domain.
- **Python-first.** The backend is async Python end-to-end. Discount patterns that only work
  in Go/Rust/TypeScript unless they translate cleanly.
- **Don't invent repo behavior.** If you can't find/verify how a project does something, say
  so rather than guessing. Unverified is fine to mention — just label it.
- **Respect the spec workflow.** If the research is meant to feed a feature, point
  at `docs/specs/` rather than starting to implement.
