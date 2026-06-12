# THAILLM-HARNESS

THAILLM-HARNESS is a Python harness for the FahMai Thai enterprise data-agent benchmark. It routes benchmark questions through deterministic guardrails, SQL planning, markdown retrieval, finance/reconciliation logic, and final-answer formatting.

The implementation lives in [`Fahmai/`](Fahmai/README.md). This root README is the quick-start guide for setup, configuration, common commands, and current project status.

## Repository Layout

```text
.
|-- data/
|   |-- questions.csv
|   `-- ground_truth.csv
|-- Fahmai/
|   |-- agent/          # Pipeline, router, guardrails, specialists, tools
|   |-- prompts/        # Prompt contracts for pipeline stages
|   |-- scripts/        # CLI helpers for smoke tests, benchmarks, schema, RAG
|   |-- artifacts/      # Generated benchmark outputs and schema/vector caches
|   |-- specialists/    # Specialist behavior specs
|   |-- tools/          # Tool contract docs
|   `-- README.md       # Detailed architecture notes
|-- Master Prompt.md
`-- README.md
```

## Requirements

- Python 3.10 or newer
- `pip`
- Optional: live PostgreSQL/Supabase access for SQL execution
- Optional: `rg`/ripgrep for faster markdown search
- Optional: a configured LLM endpoint for `--use-llm`

The only required Python dependency in this repo is PostgreSQL client support:

```powershell
cd Fahmai
python -m pip install -r requirements.txt
```

## Configuration

Configuration is loaded from environment variables or `Fahmai/.env`. The `.env` file is ignored by git.

Common variables:

| Variable | Purpose | Default |
|---|---|---|
| `FAHMAI_DATABASE_URL` | Full PostgreSQL connection URL. Overrides host/user/password fields. | Built from DB fields |
| `FAHMAI_DB_HOST` | PostgreSQL host. | `0.tcp.ap.ngrok.io` |
| `FAHMAI_DB_PORT` | PostgreSQL port. | `26551` |
| `FAHMAI_DB_NAME` | Database name. | `fahmai` |
| `FAHMAI_DB_USER` | Database user. | `fahmai_app` |
| `FAHMAI_DB_PASSWORD` | Database password. | empty |
| `FAHMAI_DB_SEARCH_PATH` | PostgreSQL search path. | `core,mart,public,rag` |
| `FAHMAI_CORPUS_ROOT` | Markdown/table corpus root. | `fah-mai-the-finale-enterprise-data-agentic-showdown` |
| `FAHMAI_LLM_PROVIDER` | LLM provider name. Use `gemma_local`, `vllm`, `sglang`, `local`, or `opentyphoon`. | `opentyphoon` |
| `FAHMAI_LLM_API_KEY` | API key for hosted LLM calls. | empty |
| `OPENTYPHOON_API_KEY` | Fallback OpenTyphoon API key. | empty |
| `FAHMAI_EMBEDDING_URL` | OpenAI-compatible embeddings endpoint. | ModelHarbor URL |

Example local `.env`:

```dotenv
FAHMAI_DB_HOST=localhost
FAHMAI_DB_PORT=5432
FAHMAI_DB_NAME=fahmai
FAHMAI_DB_USER=fahmai_app
FAHMAI_DB_PASSWORD=change-me
FAHMAI_CORPUS_ROOT=../fah-mai-the-finale-enterprise-data-agentic-showdown
```

Use a read-only database role for untrusted SQL. The harness validates candidate SQL before execution, but validation should be treated as an application guard, not a database permission boundary.

## Quick Start

Run the offline smoke test:

```powershell
cd Fahmai
python scripts/smoke_test.py
```

Inspect schema, using PostgreSQL when available and CSV fallback otherwise:

```powershell
python scripts/inspect_schema.py --table dim_product
python scripts/build_schema_cache.py
```

Run a single benchmark question:

```powershell
python scripts/run_question.py --id L3-Q-EASY-001
```

Run a custom question:

```powershell
python scripts/run_question.py --question "What is the MSRP for sku NT-LT-001?"
```

Run a question with an explicit read-only SQL candidate:

```powershell
python scripts/run_question.py --id L3-Q-EASY-001 --sql "SELECT sku_id, msrp_thb FROM dim_product WHERE sku_id = 'NT-LT-001'"
```

Run a small benchmark slice:

```powershell
python scripts/run_benchmark.py --limit 10
```

Evaluate an existing benchmark CSV:

```powershell
python scripts/evaluate_benchmark.py --predictions artifacts/benchmark_routes.csv
```

## RAG and Vector Search

Keyword RAG searches markdown documents under the configured corpus root:

```powershell
python scripts/run_question.py --question "What did memo MIN-OPS-2025-04 say about delivery delay?" --execute-rag
```

Vector RAG requires an embeddings endpoint and a built JSONL index:

```powershell
python scripts/test_embedding.py
python scripts/build_vector_index.py --limit 100
python scripts/vector_search.py "Galaxy Pro launch campaign"
```

## LLM Use

The harness can use a configured LLM for final composing:

```powershell
python scripts/test_llm.py
python scripts/run_question.py --id L3-Q-EASY-001 --use-llm
```

For local Gemma through vLLM on `localhost:8000`:

```powershell
.\scripts\start_gemma_vllm.ps1
.\scripts\use_gemma_local.ps1
python scripts\test_llm.py
```

`--use-local-llm` is currently an alias for `--use-llm`; the actual provider is selected by environment variables such as `FAHMAI_LLM_PROVIDER`.

## Outputs

Benchmark commands write to `Fahmai/artifacts/` by default:

- `benchmark_routes.csv` - compact per-question route and score output
- `benchmark_states.jsonl` - full pipeline state per question
- `benchmark_summary.json` - score summary for that run
- `schema_cache.json` - generated schema cache
- `vector_index_qwen3.jsonl` - optional vector index

Historical benchmark artifacts are also checked in under `Fahmai/artifacts/`. The current documented reconciler run is `benchmark_reconciler_current_summary.json`:

```text
Total: 100
Matched: 80
Accuracy: 80%

EASY: 25/25
MED: 19/20
HARD: 1/20
XHARD: 20/20
REF: 5/5
INJ: 10/10
```

## Architecture

At a high level, `agent.pipeline.run_pipeline()` does this:

```text
question
  -> normalize
  -> guardrail
  -> route
  -> plan
  -> optional SQL and/or RAG specialists
  -> validate evidence
  -> canonical injection/reference answer, reconciler, or final composer
```

Important files:

| Area | Files |
|---|---|
| Pipeline entry point | `Fahmai/agent/pipeline.py` |
| Normalization and routing | `Fahmai/agent/normalizer.py`, `Fahmai/agent/router.py` |
| Planning and decomposition | `Fahmai/agent/planner.py`, `Fahmai/agent/decomposer.py` |
| Prompt-injection handling | `Fahmai/agent/guardrails/` |
| SQL execution | `Fahmai/agent/specialists/sql.py`, `Fahmai/agent/tools/postgres.py`, `Fahmai/agent/tools/sql_generator.py` |
| RAG search | `Fahmai/agent/specialists/rag.py`, `Fahmai/agent/tools/markdown_search.py`, `Fahmai/agent/tools/vector_search.py` |
| Final answers | `Fahmai/agent/composer.py`, `Fahmai/agent/reconciler.py`, `Fahmai/agent/references.py` |

See [`Fahmai/README.md`](Fahmai/README.md) for the detailed pipeline diagram and stage responsibilities.

## Troubleshooting

- `python scripts/run_question.py --id ...` can hang or fail if the default PostgreSQL tunnel is not available. Configure `FAHMAI_DATABASE_URL` or DB fields in `Fahmai/.env`.
- `RAG no_data` usually means `FAHMAI_CORPUS_ROOT` does not point to the FahMai dataset corpus.
- Vector search needs `Fahmai/artifacts/vector_index_qwen3.jsonl`. Build it with `scripts/build_vector_index.py`.
- Hosted LLM composing needs `FAHMAI_LLM_API_KEY` or `OPENTYPHOON_API_KEY`.
- Run commands from `Fahmai/` unless you provide explicit paths.

## Development Notes

- Keep generated run outputs under `Fahmai/artifacts/`.
- Prefer deterministic SQL/pattern logic for benchmark-critical answers.
- Add tests or smoke checks when changing routing, SQL generation, guardrail behavior, or answer formatting.
- For untrusted SQL execution, enforce read-only permissions at the database role/session level in addition to the Python validator.
