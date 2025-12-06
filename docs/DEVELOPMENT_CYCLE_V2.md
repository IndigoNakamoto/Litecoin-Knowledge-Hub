Here is the optimized **Development Cycle Playbook** tailored specifically for an **AI-Augmented Human** (you) using **Gemini** for reasoning and **Cursor** for implementation, running on **Apple Silicon M4** hardware.

-----

# Development Cycle: The AI-Augmented Workflow

**Version:** 2.0 (M4 Hardware Optimized)
**Status:** Active Standard

## 1\. The Core Philosophy

We do not write code until the logic is proven. We utilize our hardware advantage (M4 Neural Engine) to eliminate API dependencies. We use **Gemini** to think and **Cursor** to build.

### The "Hardware Advantage" Rule

  * **Infrastructure:** Apple Silicon M4 Server (24GB Unified Memory).
  * **Implication:** **NEVER use external APIs for embeddings or processing that can be done locally.**
  * **Standard:** Production uses SOTA local models (e.g., `BAAI/bge-m3` or `nomic-embed-text`) running on the Neural Engine. Zero latency, zero cost, zero rate limits.

-----

## 2\. The Tool Assignment

| Tool | Role | The "Prompt" Strategy |
| :--- | :--- | :--- |
| **Human (You)** | **The Director** | Define *What* and *Why*. Approve the *How*. |
| **Gemini (Pro/Flash)** | **The Architect** | Use for: High-level reasoning, writing detailed specs (`docs/features/`), architecture review, and complex debugging analysis. |
| **Cursor (IDE)** | **The Builder** | Use for: Writing code, refactoring, file management, and running tests. It "owns" the codebase context. |
| **Docker** | **The Reality** | If it doesn't pass in Docker, it doesn't exist. |

-----

## 3\. The Feature Development Loop (8 Steps)

### Phase 1: Definition & Architecture (Gemini)

**1. The Spec (Human + Gemini)**

  * **Action:** Create `docs/features/FEATURE_NAME.md`.
  * **Workflow:** Paste your raw idea into Gemini. Ask it to "Draft a Feature Specification including edge cases, security risks, and acceptance criteria."
  * **Output:** A Markdown file defining *exactly* what success looks like.

**2. The Architecture Check (Gemini)**

  * **Action:** Ask Gemini: *"Review this new feature doc against my `techStack.md` and `projectRoadmap.md`. Identify potential conflicts, schema changes, or performance bottlenecks."*
  * **Result:** A list of blockers to fix *before* coding starts.

### Phase 2: Implementation (Cursor)

**3. The Plan (Cursor)**

  * **Action:** Open Cursor (Cmd+L or Composer).
  * **Prompt:** *"@docs/features/FEATURE\_NAME.md @codebase Read the feature spec. Create a step-by-step checklist to implement this. Do not write code yet."*
  * **Result:** A checklist in `currentTask.md`.

**4. The Build (Cursor)**

  * **Action:** Iterate through the checklist using Cursor Composer (Cmd+I).
  * **Rule:** Implement one logical chunk at a time.
  * **Prompt:** *"Implement step 1. Ensure strictly typed Python/TypeScript. Add comments explaining complex logic."*

### Phase 3: Verification (Docker)

**5. The Test (Cursor + Docker)**

  * **Action:** **Do not trust the IDE execution.** Run tests in the container.
  * **Command:** `docker compose -f docker-compose.dev.yml run --rm backend pytest tests/ -vv`
  * **Standard:** **100% Pass Rate.** If one test fails, the feature is not done.

**6. The "M4 Check" (Performance)**

  * **Action:** Verify that heavy operations (Embeddings/RAG) are hitting the local Neural Engine/GPU, not external APIs.
  * **Check:** Latency should be \<50ms for embeddings.

### Phase 4: Security & Ship

**7. The Red Team (Human + Gemini)**

  * **Action:** Paste the critical code blocks (Auth/Payment/RateLimits) into Gemini.
  * **Prompt:** *"Act as a security researcher. Find exploits in this code regarding race conditions, injection, or abuse."*
  * **Fix:** Apply fixes immediately via Cursor.

**8. Deployment**

  * **Action:** Merge to `main`.
  * **Verify:** Check `docker-compose.prod.yml` config matches the tested environment.

-----

## 4\. Coding Standards (Cursor Rules)

Add these to your `.cursorrules` or system prompt:

1.  **Atomic Operations:** "When touching Redis or Rate Limits, ALWAYS use Lua scripts to prevent race conditions."
2.  **No API Embeddings:** "If the code requests an embedding, it MUST use the `LocalEmbeddingProcessor` class. Do not import Google/OpenAI embedding libraries."
3.  **Error Silence:** "Never return internal stack traces or database IDs to the frontend API responses."
4.  **Typed Code:** "Strict typing only. No `any` in TypeScript. Type hints required in Python."

-----

## 5\. Directory Structure Standard

```text
root/
├── docs/
│   ├── features/          # The Source of Truth (Specs)
│   ├── architecture/      # Decision Records
│   └── security/          # Threat Models
├── backend/
│   ├── app/core/          # Business Logic
│   └── tests/             # Pytest Suite
├── .env.docker.prod       # Production Config (Force EMBEDDING_MODEL=local)
└── docker-compose.prod.yml
```

-----

## 6\. Emergency Protocols

  * **Test Failure:** Stop. Do not push. Fix the test or update the spec if the requirement changed.
  * **Performance Regression:** If RAG latency \> 1s, check if the system accidentally reverted to CPU-only processing or API calls.
  * **Cost Spike:** If LLM costs jump, verify Caching layer (Redis) is active.