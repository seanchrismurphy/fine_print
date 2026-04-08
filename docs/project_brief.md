# Insurance PDS Q&A System — Project Brief (v2)

## Problem Statement

Australian insurance consumers face two distinct information asymmetry problems. At purchase time, they're handed multiple 60-80 page Product Disclosure Statements written in legal language, with inconsistent terminology across insurers for equivalent concepts. This is not an abstract problem in home insurance: "flood", "storm water", "rainwater", and "surface water" are legally distinct terms that determine whether a claim is paid or rejected, and different insurers define them differently. This system makes those documents interrogable and comparable, so a consumer can ask a plain-language question and get an answer grounded in the actual policy language.

---

## Phase 1 — Corpus Construction (Days 1–4)

**Goal:** Build a structured document corpus across multiple home insurance providers that supports comparison queries.

1. Select 4 Australian insurers offering home insurance. NRMA, Allianz, AAMI, and Suncorp are good targets — all publish PDFs publicly and have meaningful differences in how they define key terms like flood and storm damage.

2. Download PDS documents directly from insurer websites. Do not scrape dynamically; download and version-control the raw PDFs. Record the retrieval date for each.

3. Build a document metadata registry. For each document, record: insurer name, product line (home insurance), document version, date retrieved, and source URL. This becomes the foundation for source citations in the frontend.

4. Audit structural heterogeneity across the four documents. Note: does each use a consolidated defined terms section, are exclusions scattered throughout or consolidated, how are coverage limits presented? This audit directly informs chunking decisions in Phase 2 and becomes content for the README's architecture section.

5. Construct 25–30 ground truth Q&A pairs manually. Distribute across three types:
   - Single-document factual: "What is the flood definition under Allianz home insurance?"
   - Exclusion surfacing: "What events are excluded from storm damage cover under NRMA?"
   - Cross-insurer comparison: "Which of these four insurers provides the broadest definition of storm damage?"
   
   Label each pair with the source document and page number. This is your evaluation dataset.

---

## Phase 2 — Core Retrieval Pipeline (Days 5–10)

**Goal:** Working retrieval pipeline with domain-justified design decisions.

1. Implement PDF parsing with `pdfplumber` or `pymupdf`. These handle insurance PDFs more reliably than LangChain's default loaders and give you control over page metadata. Attach document metadata (insurer name, document version, page number) to every chunk at parse time.

2. Implement chunking with a deliberate strategy. Start with recursive character splitting at 512 tokens with 10% overlap. The rationale: PDS documents contain long defined-terms clauses that should not be split mid-definition. Test this against your ground truth pairs before committing. Document what you tried and why you landed where you did — this belongs in the README.

3. Generate embeddings with OpenAI `text-embedding-3-small` and store in Chroma with persistence to disk. Local Chroma is sufficient for development and deployment.

4. Implement hybrid retrieval: BM25 for keyword matching on defined terms and policy-specific language, dense retrieval for semantic similarity. The domain justification is explicit: pure semantic search will treat "flood" and "rainwater" as near-synonyms because they are semantically close; BM25 catches exact defined-term matches that matter legally. Use `rank_bm25` and combine scores with Reciprocal Rank Fusion.

5. Add a Cohere reranker (free tier is sufficient) or a cross-encoder from `sentence-transformers`. This is optional and should be added last in this phase — the pipeline works without it and it should not block progress to Phase 3.

6. Wire together a basic retrieval chain in LangChain. No agentic routing yet — retrieve-then-generate to validate the pipeline end to end against your ground truth pairs.

---

## Phase 3 — Agentic Layer with LangGraph (Days 11–18)

**Goal:** A stateful, multi-step reasoning flow that justifies the "agentic" label.

Build the LangGraph flow sequentially — get the linear path working before adding parallel branches.

**Node 1 — Query Classifier:** Determines query type from: single-document factual, cross-insurer comparison, or out-of-scope. Out-of-scope queries (e.g. greetings, questions about products not in the corpus) return a direct response without retrieval. This is the routing behaviour that makes the agentic label defensible.

**Node 2 — Query Decomposer (comparison queries only):** Breaks a comparison question into sub-questions, one per insurer. "Which insurer defines flood most broadly?" becomes four parallel sub-questions, each targeting one insurer's document. Build this node second, after the linear path works.

**Node 3 — Parallel Retriever:** Executes retrieval for each sub-question independently. This is where LangGraph's graph structure earns its place — parallel branches executing retrieval concurrently and rejoining before synthesis. Expect this node to take the most debugging time.

**Node 4 — Synthesiser:** Takes retrieved contexts (from one document or multiple) and generates the final answer. For comparison queries, the synthesiser should structure the answer by insurer and include verbatim quoted definitions where they are the key differentiator.

Wire nodes with conditional edges: comparison queries route through decomposition and parallel retrieval; single-document queries go directly to retrieval and synthesis; out-of-scope queries short-circuit.

---

## Phase 4 — Evaluation (Days 15–20, overlapping with Phase 3)

**Goal:** Use RAGAS to measure, iterate, and show a before/after delta.

1. Run RAGAS against your ground truth pairs on the Phase 2 pipeline, before LangGraph. Record baseline metrics: faithfulness, answer relevancy, context precision, context recall.

2. Identify failure modes from the baseline. Comparison queries will likely score lowest — the pipeline was not designed for them. Single-document factual queries on defined terms may also underperform if chunking is splitting definitions.

3. Iterate on one thing based on the results. The most productive candidates are: chunk size or overlap tuning for defined terms, retrieval k, or adding the reranker. Measure the delta before moving on.

4. Re-run after LangGraph is implemented. Show the before/after for comparison queries specifically — this is the clearest evidence that the agentic layer improved retrieval outcomes, not just answer generation.

5. Document at least one failure case honestly. A specific example of where the system still gets it wrong is more credible to a technical hiring manager than a clean dashboard.

---

## Phase 5 — Serving Layer and Observability (Days 19–24)

**Goal:** Clean, deployable interface that surfaces the system's reasoning.

**FastAPI backend:**
- `/query` endpoint accepting a question and optional insurer filter
- Response payload includes: answer, source citations with insurer name and page number, retrieved chunk previews, query type from the LangGraph classifier, LangSmith trace URL

**Streamlit frontend:**
- Chat interface with a sidebar for insurer filtering
- Expandable "Retrieved Sources" panel below each answer showing chunk previews, similarity scores, and document metadata
- A "Trace" link per response that opens LangSmith for that query

**LangSmith:** Instrument every LangGraph node. The trace should be readable enough to walk through live in an interview — showing the classifier's decision, the decomposer's sub-questions, and each retrieval branch independently.

---

## Phase 6 — Deployment and README (Days 23–28)

**Goal:** Live URL and a README that tells the right story.

**Deployment:** Azure Container Apps. Containerise FastAPI and Streamlit separately. Use Azure Key Vault for API keys. Persist the Chroma index to Azure Blob Storage between deployments.

**README structure:**
1. Problem statement — the consumer information asymmetry problem and why home insurance PDS documents are a genuinely hard retrieval domain (flood vs storm terminology as the concrete example)
2. Architecture diagram — one diagram showing the LangGraph flow with node labels and conditional edges
3. Key decisions — one paragraph each on: chunking strategy, hybrid retrieval justification, LangGraph flow design
4. Evaluation results — a table of RAGAS metrics before and after the main iteration, with one paragraph on what changed and why
5. Known limitations and what you'd build next (this is where Pinecone and the exclusion checker live)
6. Setup and local run instructions

Write the key decisions and failure cases as you go, not on day 28. The details are easy to forget after the fact.

---

## Stretch Goals

These are explicitly out of scope for the four-week timeline. Both are worth noting in the README as natural next steps.

**Exclusion Checker node:** After retrieving content for a coverage question, proactively query the exclusions section of the same document and surface relevant exclusions the user did not ask about. This requires the system to reason about what the user should know, not just what they asked — a genuinely more sophisticated agentic behaviour. Deferred because it adds a node to an already complex LangGraph flow and requires additional ground truth pairs to evaluate properly.

**Pinecone vector store:** Replace local Chroma with Pinecone for managed vector storage, metadata filtering, and namespace support per insurer. Deferred because Chroma with Azure Blob Storage persistence is sufficient for the corpus size and the operational overhead of another external service is not justified at this stage.

---

## Stack Summary

| Layer | Tool |
|---|---|
| Orchestration | LangGraph + LangChain |
| Embeddings | OpenAI text-embedding-3-small |
| Vector store | Chroma (persisted to Azure Blob Storage) |
| Retrieval | Hybrid BM25 + dense, optional Cohere rerank |
| LLM | GPT-4o-mini |
| Backend | FastAPI |
| Frontend | Streamlit |
| Observability | LangSmith |
| Evaluation | RAGAS |
| Deployment | Azure Container Apps |

---

## Timeline

| Phase | Days | Week |
|---|---|---|
| Corpus + ground truth | 1–4 | 1 |
| Core retrieval pipeline | 5–10 | 2 |
| LangGraph agentic layer | 11–18 | 2–3 |
| Evaluation + iteration | 15–20 | 3 |
| Serving + observability | 19–24 | 3–4 |
| Deployment + README | 23–28 | 4 |
