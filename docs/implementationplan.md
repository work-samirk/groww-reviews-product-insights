# Groww Weekly Product Insights — Implementation Plan

This document details the chronological phases of implementation for building the **Weekly Product Review Pulse** automation pipeline for the **Groww** platform.

---

## Chronological Implementation Phases

```
┌────────────────────────────────────────────────────────┐
│ Phase 1: Environment & Directory Setup                 │
│ - Virtual environment setup                            │
│ - Dependency management (requirements.txt)             │
│ - Directory layouts initialization                     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Phase 2: Custom Google Workspace MCP Server            │
│ - Node.js project init & Auth library integration      │
│ - Google Docs append tool with outline-based guard     │
│ - Gmail draft/sender tools                             │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Phase 3: Data Ingestion & Security                     │
│ - Play Store scraper & mock fallback database          │
│ - App Store RSS direct reader                          │
│ - Regex-based & author-hashing PII scrubber            │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Phase 4: Reasoning Core & Quote Validation             │
│ - Gemini API embeddings, UMAP & HDBSCAN clustering     │
│ - LLM theme synthesis with rating-weighted scoring     │
│ - Exact-match quote verification logic                 │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Phase 5: State Ledger, CLI & MCP Bridge Client         │
│ - Relational SQLite schema (runs & deliveries)         │
│ - CLI parameters & dry-run switches                    │
│ - JSON-RPC 2.0 stdio subprocess client                 │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Phase 6: Verification & Validation                     │
│ - Component level unit tests                           │
│ - Dry-run execution & E2E writes                       │
│ - Idempotency enforcement check                        │
└────────────────────────────────────────────────────────┘
```

---

## Detailed Phase Requirements

### Phase 1: Environment & Directory Setup
* **Dependencies**: Configure Python packages (`pandas`, `numpy`, `scikit-learn`, `umap-learn`, `hdbscan`, `google-generativeai`, `requests`, `pytest`, `python-dotenv`) in `requirements.txt`.
* **Directories**: Set up `/pipeline/` for Python modules and `/mcp-server/` for Node.js modules.

### Phase 2: Custom Google Workspace MCP Server
* **Authentication**: Integrate Google APIs Client in Node.js. Setup `auth.js` to coordinate OAuth 2.0 flow (saving keys in `token.json` after the first browser redirect on port 8085).
* **Docs Tool**: Create `append_weekly_report` which verifies if the target week heading exists (idempotency check) and appends the report block.
* **Gmail Tool**: Create `send_stakeholder_teaser` which creates MIME emails and dispatches them via standard I/O transport.

### Phase 3: Data Ingestion & Security
* **App Store Ingestor**: Connects to the public iTunes feed to extract the last 12 weeks of reviews for App ID `1402264636`.
* **Play Store Ingestor**: Gathers Play Store reviews for package `com.groww.app` with a high-fidelity local fallback database of realistic reviews for testing.
* **PII Scrubber**: Scrubs emails, phone numbers, Aadhaar, PAN, card numbers, and OTPs. Consistently hashes author names (e.g., `User_a4c1`).

### Phase 4: Reasoning Core & Quote Validation
* **Embeddings**: Generates review embeddings using Gemini's `text-embedding-004` (with TF-IDF fallback).
* **Clustering**: Projects dimensions with UMAP and clusters with HDBSCAN.
* **Theme Ranking**: Ranks clusters using the rating-weighted priority scoring formula:
  $$\text{Score} = \text{Cluster Size} \times (6 - \text{Average Rating})$$
* **Quote Validation**: Cross-references LLM quotes against raw review text, auto-correcting slight paraphrases or falling back to raw reviews to prevent hallucination.

### Phase 5: State Ledger, CLI & MCP Bridge Client
* **Relational DB**: Configures SQLite database tracking `runs` and `deliveries` tables.
* **CLI Engine**: Sets up parameters (`--week`, `--force`, `--dry-run`, `--doc-id`, `--email-to`).
* **MCP Client**: Spawns Node.js server subprocess, connects stdin/stdout, and communicates via JSON-RPC 2.0.

### Phase 6: Verification & Validation
* **Pytest Suite**: Evaluates PII scrubbing and quote validation logic.
* **Dry-Run Mode**: Verifies entire pipeline locally, printing preview outputs to terminal without writing to external APIs.
* **Manual E2E Runs**: Verifies document writes and email dispatches with real credentials, checking idempotency on re-run.
