# Groww Weekly Product Review Pulse 📈

An automated fintech intelligence pipeline designed to ingest, clean, cluster, and synthesize customer reviews for the **Groww** platform from the Google Play Store and Apple App Store. The resulting insights are securely pushed to Google Docs (append-only) and Gmail (summary teasers) via a custom Model Context Protocol (MCP) server.

---

## 🚀 Workflow Overview

```
1. Ingest Data ──► 2. Clean & Scrub ──► 3. Embed & Cluster ──► 4. LLM Synthesis ──► 5. MCP Delivery
 (App/Play Feed)      (PII Redaction)       (UMAP + HDBSCAN)    (Verbatim Quotes)   (Docs & Gmail)
```

1. **Ingest Data**: Aggregates reviews dynamically from Apple App Store RSS and parses local Google Play cache files (falling back to a high-fidelity local database).
2. **Clean & Scrub**: Scrubs sensitive PII (emails, phone numbers, Aadhaar, PAN, debit/credit cards, and OTPs) and anonymizes reviewer usernames using MD5 hashing.
3. **Embed & Cluster**: Converts reviews into semantic vectors using Gemini's `text-embedding-004` (falling back to local TF-IDF) and groupings are formed via UMAP dimensionality reduction and HDBSCAN density clustering.
4. **LLM Synthesis**: Ranks clusters based on a rating-weighted priority score:
   $$\text{Score} = \text{Cluster Size} \times (6 - \text{Average Rating})$$
   Surfaces issues to a generative model (`gemini-3.5-flash`) for theme naming and action ideas, and runs an exact-match verification engine to heal and validate user quotes.
5. **MCP Workspace Delivery**: Automatically boots the local Node.js stdio MCP server in the background, checks for outline heading duplicates for idempotency, appends the section to Google Docs, and drafts/sends a teaser email to stakeholders.

---

## 📁 Project Structure

```
├── docs/                     # Architectural specifications and edge cases documentation
├── mcp-server/               # Custom Google Workspace stdio Node.js MCP server
│   ├── auth.js               # Local OAuth 2.0 loopback server (port 8085)
│   ├── index.js              # Docs & Gmail MCP tools registration and execution
│   └── package.json          # Node dependencies
├── pipeline/                 # Core Python pipeline components
│   ├── ingestion/            # App Store RSS & Play Store scraper modules
│   ├── security/             # PII Redacting and author hashing scripts
│   ├── reasoning/            # UMAP/HDBSCAN clustering & LLM synthesis modules
│   ├── delivery/             # JSON-RPC 2.0 subprocess MCP Host client
│   ├── state/                # SQLite idempotency run ledger
│   ├── rendering/            # Markdown & MIME HTML document layout renderers
│   ├── tests/                # Pytest component suites
│   └── cli.py                # Main orchestrator CLI
├── .env                      # Local environment configuration (API keys)
├── .gitignore                # Excludes secrets, credentials, databases, & venv
├── credentials.json          # Google Cloud OAuth Desktop credential file (NOT committed)
├── token.json                # Google API authorization tokens cache (NOT committed)
└── pipeline_state.db         # SQLite run status ledger (NOT committed)
```

---

## 🛠️ Getting Started (Local Setup)

### 1. Prerequisites
- **Python**: Version 3.9+
- **Node.js**: Version 18+

### 2. Install Dependencies
```bash
# Setup Python Virtual Environment
python3 -m venv venv
source venv/bin/activate
pip install -r pipeline/requirements.txt

# Install Node.js MCP Server Dependencies
cd mcp-server
npm install
cd ..
```

### 3. Setup Secrets & Configuration
Create a `.env` file in the root directory:
```env
# Gemini API Key for Embeddings and LLM Theme Synthesis
GEMINI_API_KEY=your_gemini_api_key_here

# Target Google Doc ID (Use 'CREATE' to automatically create a new document)
GOOGLE_DOC_ID=CREATE

# Email recipient for weekly teasers
STAKEHOLDER_EMAIL=stakeholder@example.com
```

Save your Google Cloud OAuth **Desktop application** credentials as **`credentials.json`** in the root of the project.

---

## 🏃 Execution Commands

### 🧪 Run Unit Tests
```bash
PYTHONPATH=. ./venv/bin/pytest
```

### 🔍 Execute a Dry Run (Previews Outputs Locally)
```bash
PYTHONPATH=. ./venv/bin/python pipeline/cli.py --dry-run
```
*Creates a `debug/` folder containing intermediate raw feeds, scrubbed reviews, embedding meta, and clustered matrices.*

### ⚡ Live Run (Auto-Auth & Docs/Gmail Write)
```bash
PYTHONPATH=. ./venv/bin/python pipeline/cli.py
```
*On the first run, copy the printed URL into your browser to authorize access. The login server will automatically save `token.json` for subsequent headless executions.*
