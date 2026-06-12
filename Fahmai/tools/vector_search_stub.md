# Qwen3 Vector Search

The harness now supports Qwen3 embeddings through an OpenAI-compatible embeddings endpoint.

Default config:

```env
FAHMAI_EMBEDDING_PROVIDER=modelharbor
FAHMAI_EMBEDDING_URL=http://swarm-manager.modelharbor.com:56980/v1/embeddings
FAHMAI_EMBEDDING_MODEL=qwen3-embedding
FAHMAI_VECTOR_INDEX_PATH=artifacts/vector_index_qwen3.jsonl
```

The ModelHarbor model id is `qwen3-embedding`, backed by `Qwen/Qwen3-Embedding-8B`.

## Commands

Test embedding endpoint:

```powershell
python scripts/test_embedding.py
```

Build a small test index:

```powershell
python scripts/build_vector_index.py --limit 100
```

Search vector index:

```powershell
python scripts/vector_search.py "Galaxy Pro launch campaign"
```

Run RAG with hybrid vector + keyword retrieval:

```powershell
python scripts/run_question.py --question "What did memo MIN-OPS-2025-04 say about delivery delay?" --execute-rag
```

If the embedding endpoint or vector index is unavailable, RAG falls back to keyword search and records the vector warning in the attempt log.
