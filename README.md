# Insurance PDS Q&A

A retrieval-augmented generation system for querying and comparing Australian home insurance Product Disclosure Statements.

**Live demo:** [link when deployed]

---

## The problem

Australian home insurance consumers face a genuine information asymmetry problem at purchase time. Insurers publish Product Disclosure Statements that run to 60-80 pages of legal language, and the terminology is not consistent across providers. "Flood", "storm water", "rainwater", and "surface water" are legally distinct terms that determine whether a claim is paid or rejected — and different insurers define them differently. Reading four PDSs side by side to make a coverage decision is not a realistic expectation of a consumer.

The canonical question this system is designed to answer: **"If my house floods during a storm, will I be covered?"** This question is deliberately ambiguous in the way real consumer questions are. It crosses the flood/storm boundary intentionally. A useful answer requires retrieving the relevant definitions from multiple insurers, surfacing the terminological differences, and producing a direct response — not a hedge — with the relevant policy language quoted verbatim.

This system makes those documents interrogable in plain language and comparable across insurers.

---

## What it does

- Answers coverage questions grounded in specific policy language, with source citations to the relevant document and page
- Compares how multiple insurers define a term or handle a scenario
- Routes queries intelligently: comparison questions decompose into per-insurer sub-questions, retrieved independently and synthesised together; out-of-scope queries are handled directly without retrieval
- Signals retrieval uncertainty explicitly when the retrieved context is insufficient to support a confident answer
- Surfaces retrieval metadata — BM25 rank and dense rank per chunk — so the retrieval behaviour is auditable, not a black box

**Corpus:** Home insurance PDS documents from NRMA, Allianz, AAMI, and Suncorp.

---

## Architecture

*[Diagram to be added — LangGraph flow with node labels and conditional edges.]*

The system uses a five-node LangGraph flow with conditional routing. The routing decision happens at the classifier and determines everything downstream.

**Query Classifier** — determines whether a query is single-document factual, cross-insurer comparison, or out-of-scope. Out-of-scope queries short-circuit to a direct response without retrieval. The classifier is evaluated separately on the ground truth dataset; accuracy is reported in the evaluation section.

**Query Decomposer** — for comparison queries only, breaks the question into sub-questions targeting each insurer's document independently. Also identifies which insurers are relevant when a query specifies a subset.

**Parallel Retriever** — executes hybrid retrieval (BM25 + dense, combined with Reciprocal Rank Fusion) for each sub-question concurrently. Single-document factual queries bypass this node and go directly to a single retrieval call. The BM25 rank and dense rank for each retrieved chunk are preserved in the response and surfaced in the UI separately — RRF does not produce a single similarity score, and the frontend reflects that accurately.

**Synthesiser** — generates the final answer from one or more retrieved contexts. For comparison queries, the synthesis prompt is designed to produce a direct comparative judgment with quoted definitions, not a hedged summary of each insurer's position.

**Confidence Signaller** — sits between the synthesiser and the response. Assesses whether the retrieved context is actually sufficient to answer the question. If a query about flood coverage returns storm damage definitions but no flood definition, the system surfaces this gap rather than generating an answer that appears grounded but is not.

---

## Key decisions

*Working notes live in `docs/decisions/` as decisions are made. This section will be completed progressively through the build.*

**Chunking strategy**

*[To be written after Phase 2. Will cover: what the structural audit of the four PDS documents revealed, where naive recursive splitting failed and why, how structure-aware chunking addresses the defined-term splitting problem, and the measured delta between approaches on the ground truth set.]*

The short version: recursive character splitting at 512 tokens consistently split multi-clause defined-term sections across chunk boundaries, producing incomplete retrieval results on definition queries. The chunker was redesigned to treat each defined term as an atomic unit, using section headings and formatting cues from the structural audit to identify boundaries.

**Hybrid retrieval**

Pure semantic retrieval fails on defined-term queries in this domain for a specific reason. A general-purpose embedding model has no reason to distinguish "flood" from "rainwater" — they appear in similar contexts in general language and sit close together in embedding space. In an insurance PDS, they are legally distinct and the distinction determines whether a claim is paid. BM25 catches exact term matches regardless of semantic proximity, which is the right behaviour for a retrieval target that is a legal definition.

The ablation results below show where each retrieval approach succeeds and where it falls short, broken down by query type.

**LangGraph flow design**

The routing behaviour adds something a single retrieval call cannot. A flat retrieval call across the full corpus for a comparison query will over-retrieve from whichever one or two documents have the highest-ranking chunks for that query, leaving other insurers underrepresented in the context window. The parallel retriever, with a sub-question per insurer, ensures each document gets an independent retrieval pass. The classifier allows genuine out-of-scope detection rather than attempting retrieval against questions the corpus cannot answer.

**Confidence signalling**

*[To be written after Phase 3. Will describe the specific failure case that motivated this node, how often it fires on the evaluation set, and whether those firings are correct.]*

---

## Evaluation

*To be completed after Phase 4.*

**Ground truth dataset**

35-40 manually constructed Q&A pairs across three query types: single-document factual, exclusion surfacing, and cross-insurer comparison. Each pair includes the source document, page number, and verbatim relevant text. The comparison query set is deliberately large (15-18 pairs) because that is the query class where the system's core differentiation lives, and a small sample would produce unstable RAGAS estimates for the most important category.

**Classifier accuracy**

| Classifier | Accuracy |
|---|---|
| Single-document factual | — |
| Cross-insurer comparison | — |
| Out-of-scope | — |

**Retrieval ablation**

Three configurations tested against the full ground truth set before committing to the hybrid approach.

| Configuration | Factual faithfulness | Factual answer relevancy | Comparison faithfulness | Comparison answer relevancy |
|---|---|---|---|---|
| Dense-only | — | — | — | — |
| BM25-only | — | — | — | — |
| Hybrid RRF | — | — | — | — |

**Phase 2 baseline (retrieve-then-generate, no LangGraph)**

Measured on single-document factual and exclusion surfacing queries only. Cross-insurer comparison queries are excluded from the Phase 2 baseline because the Phase 2 pipeline does not support this query class — there is no meaningful baseline score to record.

| Metric | Factual | Exclusion surfacing |
|---|---|---|
| Faithfulness | — | — |
| Answer relevancy | — | — |
| Context recall | — | — |

**Iteration**

*[To be written after Phase 4. Will describe the primary failure mode identified from the baseline, what was changed, and the measured delta.]*

**Phase 3 results (LangGraph pipeline)**

For single-document factual and exclusion queries, Phase 3 retrieval is identical to Phase 2 — the difference is routing efficiency, not retrieval quality. For cross-insurer comparison queries, Phase 3 enables a query class the Phase 2 pipeline did not support. These scores are not a comparison to a Phase 2 baseline; they are the Phase 3 baseline for a new capability.

| Metric | Factual | Exclusion surfacing | Comparison |
|---|---|---|---|
| Faithfulness | — | — | — |
| Answer relevancy | — | — | — |
| Context recall | — | — | — |

---

## Error analysis

*To be completed after Phase 4.*

Three failure cases that remain after iteration, traced to their root cause.

**Failure 1 — [query type]**

*[Specific query, scores, root cause — retrieval failure / ranking failure / chunking failure / synthesis failure / classifier failure — and what would fix it.]*

**Failure 2 — [query type]**

*[Same structure.]*

**Failure 3 — [query type]**

*[Same structure.]*

---

## Known limitations and next steps

**Chroma on Azure Blob Storage**

The deployed system syncs the Chroma index directory to Azure Blob Storage at container startup. This introduces startup latency proportional to index size and is appropriate for a single-replica deployment at this corpus size. It would not be the right approach at scale. The natural upgrade path is Pinecone: managed vector storage with namespace-per-insurer support, metadata filtering, and no startup sync overhead. Deferred because the operational overhead of an additional external service is not justified for four documents.

**Exclusion checker**

A natural next node in the LangGraph flow: after retrieving content for a coverage question, proactively query the exclusions section of the same document and surface relevant exclusions the user did not ask about. This requires the system to reason about what the user should know rather than just what they asked — a more sophisticated agentic behaviour than the current flow. Deferred because it adds a node to an already complex graph and needs additional ground truth pairs to evaluate properly.

**Corpus size**

Four documents across one product line is sufficient to demonstrate the architecture and evaluation methodology. The interesting problems in insurance retrieval appear at scale: more insurers, more product lines, documents updated mid-year, and queries that cross product lines. The metadata registry, namespace-per-insurer retrieval, and structure-aware chunker are designed with expansion in mind.

---

## Stack

| Layer | Tool |
|---|---|
| Orchestration | LangGraph + LangChain |
| Embeddings | OpenAI text-embedding-3-small |
| Vector store | Chroma (persisted to Azure Blob Storage) |
| Retrieval | Hybrid BM25 + dense (RRF) |
| LLM | GPT-4o-mini |
| Backend | FastAPI |
| Frontend | Streamlit |
| Observability | LangSmith |
| Evaluation | RAGAS |
| Deployment | Azure Container Apps |

---

## Setup

*To be completed.*

```bash
# Clone the repo
git clone [repo url]
cd [repo name]

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and fill in environment variables
cp .env.example .env

# Build the index
python scripts/build_index.py

# Start the backend
uvicorn app.main:app --reload

# Start the frontend (separate terminal)
streamlit run frontend/app.py
```

**Required environment variables:**

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `LANGCHAIN_API_KEY` | LangSmith API key |
| `LANGCHAIN_TRACING_V2` | Set to `true` |
| `LANGCHAIN_PROJECT` | Your LangSmith project name |
| `AZURE_STORAGE_CONNECTION_STRING` | For Chroma index persistence |

---

## Docs

Working notes live in `docs/`:

- `docs/decisions/` — one file per architectural decision, written as decisions are made
- `docs/corpus/` — structural audit of the four PDS documents, metadata registry
- `docs/evaluation/` — RAGAS outputs, ablation results, failure case analysis
- `docs/progress.md` — running project log
