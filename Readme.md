# 🛡️ OSINT Misinformation Agent

An AI-powered fake news & misinformation detection system that uses **real-time web search** and **LLMs** to fact-check claims — with a **semantic vector cache (CAG)** to avoid redundant lookups.

Built to detect war-related misinformation, geopolitical false claims, and other viral fake news circulating in real time.

---

## 🧠 How It Works

```
User Query (Claim to verify)
        │
        ▼
┌──────────────────────┐
│  CAG Semantic Cache  │ ──── HIT ────► Return cached verdict instantly (< 2s, $0)
│  (Qdrant cag_cache)  │
└──────────────────────┘
        │ MISS
        ▼
┌──────────────────────┐
│  Tavily Web Search   │  Real-time OSINT from trusted news sources
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│   GPT-4o-mini LLM    │  Fact-check evidence → structured JSON verdict
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│  Cache Result in     │  Store embedding in Qdrant for future semantic hits
│  Qdrant (CAG)        │
└──────────────────────┘
        │
        ▼
     Verdict
```

### Verdict Format
```json
{
  "verdict": "FALSE",
  "confidence_score": "90%",
  "explanation": "Brief 2-3 sentence explanation...",
  "top_sources": ["https://reuters.com/...", "https://bbc.com/..."]
}
```

**Verdict options:** `TRUE` | `FALSE` | `MISLEADING` | `UNVERIFIED`

---

## ✅ Completed Components

| Module | File | Description |
|--------|------|-------------|
| **Config Loader** | `src/config.py` | Loads `param.yaml` + `models.yaml` + `.env` |
| **LLM Provider** | `src/infrastructure/llm/llm_provider.py` | GPT-4o-mini via LangChain, returns structured JSON |
| **Embeddings** | `src/infrastructure/llm/embeddings.py` | OpenAI `text-embedding-3-small` (1536d) |
| **Qdrant Manager** | `src/infrastructure/db/qdrant_manager.py` | Qdrant Cloud connection, collection management |
| **Web Search Tool** | `src/agents/tools/web_search_tool.py` | Tavily AI-powered real-time search |
| **Agent Prompt** | `src/agents/prompts/agent_prompts.py` | OSINT fact-checker system prompt |
| **CAG Cache** | `src/services/chat_service/cag_cache.py` | Semantic vector cache (KNN-1 cosine similarity) |
| **CAG Service** | `src/services/chat_service/cag_service.py` | Orchestrates full pipeline |

---

## 🗂️ Project Structure

```
src/
├── config.py                          # YAML + env config loader
├── logger.py                          # Logging setup
├── agents/
│   ├── prompts/
│   │   └── agent_prompts.py           # LangChain fact-check prompt
│   └── tools/
│       └── web_search_tool.py         # Tavily web search
├── infrastructure/
│   ├── db/
│   │   └── qdrant_manager.py          # Qdrant Cloud client
│   └── llm/
│       ├── embeddings.py              # OpenAI embeddings
│       └── llm_provider.py            # GPT-4o-mini chain
└── services/
    └── chat_service/
        ├── cag_cache.py               # Semantic CAG cache
        └── cag_service.py             # Main pipeline orchestrator

config/
├── param.yaml                         # Runtime parameters (thresholds, TTL, etc.)
└── models.yaml                        # Model name registry (OpenAI, Anthropic, etc.)
```

---

## ⚙️ Setup

### 1. Clone & Install
```bash
git clone https://github.com/your-repo/osint-misinformation-agent.git
cd osint-misinformation-agent
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file in the project root:
```env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
QDRANT_URL=https://xxxxx.us-east.aws.cloud.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
```

### 3. Run
```bash
python src/services/chat_service/cag_service.py
```

---

## 🔧 Configuration

Edit `config/param.yaml` to tune behavior:

```yaml
cag:
  similarity_threshold: 0.90   # Min cosine similarity for cache hit (0.90–0.95)
  cache_ttl: 86400             # Cache TTL in seconds (24h). 0 = no expiry

embedding:
  tier: small                  # "small" = 1536d, uses text-embedding-3-small
  embedding_dim: 1536

qdrant:
  collection_name: osint_misinformation_agent
```

Edit `config/models.yaml` to switch LLM providers (OpenAI, Anthropic, Google, Groq).

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | OpenAI GPT-4o-mini (via LangChain) |
| Embeddings | OpenAI text-embedding-3-small |
| Vector DB | Qdrant Cloud |
| Web Search | Tavily AI |
| Framework | LangChain + FastAPI |
| Cache | CAG — Semantic vector cache on Qdrant |

---

## 🚧 Roadmap

- [ ] FastAPI REST API endpoint (`POST /verify`)
- [ ] Multi-claim batch verification
- [ ] Telegram / WhatsApp bot integration
- [ ] Support for Sinhala language claims
- [ ] Dashboard UI for verdicts
