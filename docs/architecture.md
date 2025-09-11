# LocalMind Architecture

LocalMind is organized as a modular Python backend with clear boundaries between ingestion, analysis, retrieval, and presentation layers.

## Data Flow

1. Repository files are scanned and parsed into SQLite metadata records.
2. AST analysis builds dependency graphs and complexity metrics.
3. Symbol embeddings are generated locally and stored in FAISS.
4. Search and chat requests retrieve relevant code chunks.
5. The dashboard exposes indexing, search, chat, and review workflows.

## Components

| Module | Responsibility |
| --- | --- |
| `indexing` | File scanning, symbol extraction, incremental updates |
| `parsers` | AST analysis, import graphs, PR diff review |
| `embeddings` | Sentence-transformer encoding, cache, FAISS persistence |
| `search` | Semantic ranking and duplicate detection |
| `rag` | Context chunking, prompt assembly, Ollama inference |
| `visualization` | Architecture graph rendering and export |
| `dashboard` | Jinja UI and websocket indexing progress |
| `api` | FastAPI route composition |

## Runtime Topology

```
Browser Dashboard
    -> FastAPI (/repositories, /search, /chat, /review)
        -> SQLite metadata
        -> FAISS vectors
        -> Ollama local LLM
```

## Indexing Workflow

Register a repository path, run the indexer, optionally embed symbols, then query through semantic search or chat. Incremental indexing skips unchanged files based on content hashes.

## RAG Pipeline

Questions trigger semantic retrieval over indexed symbols. Retrieved snippets are chunked, assembled into a structured prompt, and answered through Ollama with streaming support.

## Future Improvements

- Background task queue for large monorepos
- Multi-language tree-sitter parsers
- Persistent chat sessions
- IDE plugin integration
