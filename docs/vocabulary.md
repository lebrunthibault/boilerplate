# Vocabulary

The project's domain terms — one name per concept, used the same everywhere (code, docs, specs,
frontend, comments). A mini-dictionary; we extend it as we go. Ban invented or vague names: name
things by their responsibility.

Format : `- **term** (terme français, si différent) — definition, then where it lives in the code.`

## Socle

- **admin** — A dashboard account (`admin` table): logs in with email + password. Not an end user
  of the product. Never "user" in the code for this concept.
- **session** — A server-side admin session (`admin_session`): opaque cookie token, only its
  sha256 is stored. Dies on logout, idle timeout, absolute lifetime or account deactivation.
- **step-up** — Re-checking the admin's password before a destructive act, even with a valid
  session (`verify_step_up`). Failures share the login rate-limit bucket.
- **auth event** (événement d'authentification) — One row of the authentication journal
  (`admin_auth_event`): login success/failure/blocked, logout, sessions revoked, step-up.
- **notification** — One inbox row for one admin (`admin_notification`), fanned out at write time
  to every active admin except the actor. Points at a generic **target** (`target_type` +
  `target_id`).
- **llm task** (tâche LLM) — One kind of LLM call (`LlmTask`): name, system prompt, output type,
  model tier. Its `name` is the journal key. Lives in `api.infra.llm`.
- **llm call** (appel LLM) — One run of a task (`run_llm`), success or failure, journaled in
  `llm_call` with its input, output, tokens and cost; the system prompt is stored once in
  `llm_prompt` and referenced by sha256.
- **retention** (conservation) — How long a family of personal data is kept
  (`app/config.py::Retention`), enforced by the daily purge (`app/retention.py`).

## Métier

- *(à compléter)*
