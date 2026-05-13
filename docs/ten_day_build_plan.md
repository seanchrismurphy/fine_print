# 10-Day Build Plan
 
---
 
## Day 1 — Environment setup and document ingestion
 
- Set up Python virtual environment and install core dependencies: `langchain`, `pdfplumber`, `chromadb`, `openai`, `rank_bm25`, `python-dotenv`
- Spend two hours reading all four PDFs — not a full audit, just enough to locate the flood, storm, rainwater, and surface water definitions in each document and note the page numbers
- Implement PDF parser using pdfplumber, attaching metadata (insurer name, document version, page number) to every parsed page
- Test the parser on one document and inspect the raw output — check that page numbers are accurate and metadata is attached correctly
- Commit working parser with a test script that prints parsed pages from a single document
---
 
## Day 2 — Chunking, embeddings, and vector store
 
- Implement a recursive character splitter as the baseline chunker (512 tokens, ~50 token overlap) and run it against all four documents
- Manually inspect the output chunks for the flood and storm definitions specifically — note whether any definitions are being split mid-clause
- If obvious splits are visible, implement a structure-aware adjustment (treat heading-delimited sections as chunk boundaries) and compare output
- Generate embeddings for all chunks using `text-embedding-3-small` via the OpenAI API
- Set up Chroma with persistence to disk, load all embedded chunks with metadata, verify insurer filter works via a metadata query
- Build the BM25 index using `rank_bm25` across the same chunk set
- Write a basic RRF function and run a few manual retrieval queries, inspecting the top-5 returned chunks
---
 
## Day 3 — End-to-end RAG pipeline
 
- Write a prompt template for answer generation that instructs the model to cite insurer name and page number inline and to quote relevant policy language verbatim
- Wire retrieval and generation into a single pipeline function: query in, answer + sources out
- Run the canonical query ("If my house floods during a storm, will I be covered?") end to end and read the output critically
- Add insurer filter parameter to the retrieval function so single-insurer queries only retrieve from that document's namespace
- Implement a simple per-insurer retrieval path for comparison queries: loop over all four insurer namespaces, retrieve top-2 chunks from each, concatenate before generation
- Test five to ten queries manually across both factual and comparison types, note obvious failures
---
 
## Day 4 — Query classifier and confidence signaller
 
- Implement a query classifier as a single LLM call with a structured output prompt: classify incoming query as single-document factual, cross-insurer comparison, or out-of-scope
- Wire the classifier into the pipeline — out-of-scope queries return a direct response without retrieval, others route to the appropriate retrieval path
- Implement the confidence signaller: a prompt that receives the retrieved chunks and the query and returns a structured verdict (sufficient/insufficient) plus a plain-language description of what is missing if insufficient
- Wire the confidence signaller between retrieval and generation — insufficient verdict short-circuits generation and returns the gap description to the user
- Run the full pipeline end to end across all three query types and verify routing is correct
- Manually probe the confidence signaller with a query about a term you know is absent from one insurer's document — confirm it fires correctly
---
 
## Day 5 — Ground truth dataset
 
- Re-read the relevant sections of all four documents with the ground truth pairs as the goal — this is the close reading, not the day 1 skim
- Write 8-10 single-document factual pairs: one clear question per insurer targeting a specific defined term, with the verbatim answer text and page number recorded
- Write 5-7 exclusion surfacing pairs: questions about what is explicitly not covered, drawn from the exclusions sections you identified
- Write 7-10 cross-insurer comparison pairs: questions requiring synthesis across multiple documents, with notes on which insurer's definition is broadest/narrowest and why
- Format all pairs in RAGAS-compatible structure: `question`, `ground_truth`, `answer` (leave blank for now), `contexts` (leave blank for now)
- Save to `docs/evaluation/ground_truth.json`
---
 
## Day 6 — RAGAS baseline evaluation
 
- Install RAGAS and configure it against your OpenAI API key
- Run the full pipeline against all ground truth pairs to generate `answer` and `contexts` fields
- Run RAGAS evaluation: faithfulness, answer relevancy, context recall
- Print and read the per-query scores — identify the five lowest-scoring pairs and read the actual retrieved chunks and generated answers for each
- Categorise each failure: retrieval failure (wrong chunks returned), chunking failure (right section but incomplete chunk), synthesis failure (right context, wrong answer), confidence signaller miss (should have flagged insufficient but didn't)
- Write up failure notes in `docs/evaluation/baseline.md`
---
 
## Day 7 — Iteration
 
- Based on day 6 failure categorisation, pick the single highest-leverage fix — most likely either chunk size/boundary adjustment for definition splits, or retrieval k tuning
- Implement the fix, re-run RAGAS, record the before/after delta in `docs/evaluation/`
- Revisit any confidence signaller misses from day 6 and adjust the prompt if needed
- Write a one-paragraph entry in `docs/decisions/` for each significant change made: what the failure was, what was changed, what the delta was
- Do a final manual test pass of the canonical query and two or three others — confirm the system is behaving correctly end to end
---
 
## Day 8 — FastAPI backend
 
- Set up FastAPI project structure with a `/query` endpoint accepting question and optional insurer filter
- Define Pydantic request and response models — response includes answer, source citations (insurer + page), retrieved chunk previews, BM25 rank, dense rank per chunk, confidence verdict, query type
- Wire the full pipeline (classifier → retrieval → confidence signaller → generation) into the endpoint handler
- Add basic error handling: malformed requests, OpenAI API failures, empty retrieval results
- Test the endpoint using the FastAPI auto-generated docs interface at `/docs` — run the canonical query and inspect the full response payload
- Write a `.env.example` file with all required environment variables
---
 
## Day 9 — Streamlit frontend and deployment
 
- Build the Streamlit frontend: chat input with the canonical query as placeholder text, insurer filter sidebar, response display with expandable sources panel showing chunk previews and retrieval ranks
- Wire Streamlit to the FastAPI backend via `requests`
- Write Dockerfiles for both services — FastAPI and Streamlit as separate containers
- Deploy to Railway or Render rather than Azure Container Apps — both support Docker deploys from GitHub in under an hour, which is the right tradeoff on day 9
- Smoke test the deployed version end to end with three queries: one factual, one comparison, one that should trigger the confidence signaller
---
 
## Day 10 — README, documentation, and cleanup
 
- Fill in all placeholder sections of the README: evaluation results tables, chunking decision narrative, hybrid retrieval justification, confidence signaller description
- Write the three failure case entries in `docs/evaluation/` — one per query type, each traced to its root cause
- Add a `docs/corpus/audit.md` with the key terminology differences noted during the day 1 skim and day 5 close reading — verbatim flood/storm definitions with page numbers from each insurer
- Clean up the codebase: remove debug print statements, add docstrings to the main pipeline functions, check `.gitignore` is excluding raw PDFs and Chroma persistence files
- Final smoke test of the live deployment
- Update the README with the live demo link