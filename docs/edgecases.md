# Groww Weekly Product Insights — Edge Cases & Mitigations

This document outlines the potential edge cases, failures, and operational anomalies that may arise during the execution of the **Weekly Product Review Pulse** pipeline (built for the **Groww** platform), along with the corresponding mitigation strategies implemented.

---

## 1. Environment & CLI Execution Edge Cases

| Edge Case | Impact | Mitigation Strategy / Handling |
| :--- | :--- | :--- |
| **Missing `credentials.json` or `.env`** | The pipeline or MCP server crashes due to unauthenticated API requests. | The client and MCP server validate the presence of these files at startup, logging user-friendly setup instructions and terminating cleanly with status code `1` rather than throwing a stack trace. |
| **Malformed ISO Week Input** | Passing an invalid week format like `--week 2026-6-14` or `--week 2026-W99`. | The CLI parser uses strict regex validation to verify the input matches `^20\d{2}-W[0-5]\d$`. Invalid inputs are rejected instantly before scraping or processing. |
| **Argparse Namespace Typo** | Standard command-line parsing of dashed arguments (`--dry-run`) conflicting with Python's variable names. | Implemented explicit mapping in the orchestrator: checking `args.dry_run` instead of `args.dry-run` to prevent attribute access errors. |
| **Force-Run Overrides** | Re-running a week that already has a `COMPLETED` run status in the SQLite ledger. | The CLI checks the `runs` state ledger. If a run exists for the current week, it terminates unless the `--force` flag is specified. |

---

## 2. Data Ingestion & PII Cleaning Edge Cases

| Edge Case | Impact | Mitigation Strategy / Handling |
| :--- | :--- | :--- |
| **Zero Reviews Ingested** | The clustering algorithm crashes due to empty inputs, or an empty document is delivered. | If the ingestion phase returns 0 reviews, the pipeline halts execution gracefully, logs a warning, and marks the state database run status as `COMPLETED` (or skips delivery) with an explanatory metadata note. |
| **Missing App Version / Device Details** | Review fields are missing `app_version` or device type, causing `KeyError` or schema violations. | Normalization layer parses fields with a safe `.get("app_version")` call, falling back to `"Unknown"` when the metadata is absent. |
| **Out-of-Bounds or Non-Numeric Ratings** | Ratings parsed as strings or integers outside the `1-5` range, skewing weighted priority scores. | The normalizer explicitly casts ratings to `int` and clips them to `[1, 5]`. Invalid format values are assigned a fallback rating of `3` to avoid breaking downstream priority calculations. |
| **False-Positive OTP/Account Redaction** | Legitimate non-sensitive numbers (e.g. monetary amounts, transaction numbers) get redacted as PII. | OTP regex is restricted to `4-6` digit patterns only when preceded/succeeded by security keywords (`otp`, `code`, `pin`, `verification`, `verify`). |
| **Empty or Special-Character Usernames** | The author hash generator yields empty strings or crashes on non-ASCII characters. | Author names are stripped and normalized to UTF-8 before hashing. If the resulting text is empty, it defaults to a unique pseudorandom sequence (e.g., `Anonymous_User`). |

---

## 3. Dimensionality Reduction & Clustering Edge Cases

| Edge Case | Impact | Mitigation Strategy / Handling |
| :--- | :--- | :--- |
| **Low Ingested Volume (<20 Reviews)** | UMAP and HDBSCAN fail to compile or throw errors due to insufficient density coordinates. | Dynamic Fallback: If reviews are below a threshold, the pipeline bypasses UMAP and HDBSCAN, falling back directly to standard `KMeans` with $K = \min(5, \text{number of reviews})$ to categorize reviews. |
| **All Outliers / All Reviews In Noise (-1)** | HDBSCAN labels all reviews as noise (label `-1`), resulting in zero clusters. | Dynamic Fallback: If HDBSCAN returns all noise or fails to group, standard `KMeans` is executed as a secondary clustering layer to partition the data into structured themes. |
| **Dominating Super-Cluster (>80% reviews)** | A single large complaint theme (e.g. a widespread app outage) overshadows other valuable insights. | The LLM synthesizer detects super-clusters and utilizes rating splits (e.g., separating 1-2 star critical errors from 3-4 star suggestions) to segment it into finer sub-themes. |
| **Gemini Embedding API Rate-Limits / Outage** | Embedding generation fails, blocking downstream clustering. | Dynamic Fallback: If the `text-embedding-004` API call fails, the pipeline generates a local **TF-IDF Matrix** to serve as fallback coordinate inputs, keeping the system online. |

---

## 4. LLM Synthesis & Quote Validation Edge Cases

| Edge Case | Impact | Mitigation Strategy / Handling |
| :--- | :--- | :--- |
| **LLM Quote Hallucination or Paraphrasing** | The LLM invents or alters user quotes to fit its summary, rendering the review audit trail unreliable. | **Exact-Match Quote Validation Engine**: Every quote extracted by the LLM is checked using case-insensitive substring searching against the raw reviews. If a quote fails to match exactly, the engine uses a word-density/levenshtein-distance search to locate the correct verbatim sentence or falls back to standard short reviews. |
| **Invalid JSON Schema Output from LLM** | LLM output fails to parse, causing pipeline failures. | Enforces Gemini Structured JSON Output by supplying the Pydantic schema structure directly in the API call and setting `response_mime_type: "application/json"`. |
| **Context Length/Token Limit Exceeded** | Large batches of reviews exceed the LLM's input tokens limit. | Truncate long review text strings to a maximum length (e.g., 500 characters) and process embeddings/summaries in batches of 100 before feeding them to the LLM context. |

---

## 5. Output Delivery & Idempotency Edge Cases

| Edge Case | Impact | Mitigation Strategy / Handling |
| :--- | :--- | :--- |
| **Partial Execution (Doc Appended but Email Fails)** | Retrying the pipeline duplicates the document section or sends multiple teaser emails. | **Double-Check Idempotency Strategy**:<br>1. On retry, the MCP server searches the document for the dated heading (e.g., `Groww Review Pulse — Week 2026-W24`). If found, it skips the write and returns the existing link.<br>2. The SQLite deliveries table is checked before sending an email. If the email has already been sent/drafted, that step is skipped. |
| **Simultaneous Cron Runs (Write Collisions)** | Multiple pipeline instances write to the SQLite state database at the same time, locking it. | The state manager uses sqlite3 connection timeouts, handles concurrency via `ON CONFLICT REPLACE` blocks, and immediately closes connections upon write. |
| **MIME Formatting Errors** | Email delivery fails or shows broken HTML characters due to special characters/emojis in reviews. | The email builder formats the message body as base64-encoded UTF-8 inside a `MIMEText` envelope before sending via Gmail API. |

---

## 6. MCP Subprocess Communication Edge Cases

| Edge Case | Impact | Mitigation Strategy / Handling |
| :--- | :--- | :--- |
| **Node.js Command Unavailable** | Spawning the Node.js MCP server subprocess fails. | The client catches the startup exception, logs a warning that Node.js is required to connect to the Google Workspace MCP server, and exits gracefully. |
| **Stdio Communication Lock / Deadlock** | The subprocess hangs, blocking the Python parent process indefinitely. | The MCP client applies standard timeouts on all JSON-RPC 2.0 requests (e.g., 30 seconds). If a request times out, it terminates the subprocess and falls back to a dry-run local reporting mode. |
| **Invalid/No OAuth Token** | Workspace API calls return 401/403, and the automated script hangs on a prompt. | The MCP server detects unauthenticated states and checks if a tty is present. If headless, it rejects the tool call immediately, requesting interactive OAuth initialization. |

