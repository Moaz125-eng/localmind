# LocalMind

LocalMind is a fully local AI-powered codebase intelligence platform. It analyzes software repositories, builds semantic understanding of source code, and provides developer tooling such as semantic search, repository Q&A, architecture visualization, duplicate logic detection, refactor suggestions, and pull request analysis.

Everything runs on your machine without external API keys or cloud LLM providers.

## Features

- Repository indexing with incremental updates
- AST-based code intelligence and dependency graphs
- Local embedding pipeline with FAISS vector storage
- Natural language semantic code search
- Repository chat powered by local Ollama inference
- Duplicate logic detection and refactor suggestions
- Pull request diff analysis
- Architecture visualization and web dashboard

## Requirements

- Python 3.12+
- [Ollama](https://ollama.com/) for local LLM inference
- Docker (optional)

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn localmind.api.app:create_app --factory --reload
```

Open `http://localhost:8000/` for the dashboard.

Health check: `GET http://localhost:8000/health`

## Indexing Workflow

```bash
python scripts/index_repo.py my-app /path/to/repo --embed
```

Or use the API:

```bash
curl -X POST http://localhost:8000/repositories \
  -H 'Content-Type: application/json' \
  -d '{"name":"my-app","root_path":"/path/to/repo"}'

curl -X POST http://localhost:8000/repositories/1/index \
  -H 'Content-Type: application/json' \
  -d '{"incremental":true}'

curl -X POST http://localhost:8000/embeddings/repositories/1
```

## RAG Pipeline

1. Index repository files and extract symbols
2. Embed functions/classes with sentence-transformers
3. Retrieve top matching snippets for a question
4. Assemble prompt context and stream answer from Ollama

Example chat request:

```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"Where is websocket logic implemented?","repository_id":1}'
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for module boundaries and runtime topology.

```
Browser Dashboard
    -> FastAPI (/repositories, /search, /chat, /review)
        -> SQLite metadata
        -> FAISS vectors
        -> Ollama local LLM
```

## API Overview

| Endpoint | Purpose |
| --- | --- |
| `POST /repositories` | Register repository |
| `POST /repositories/{id}/index` | Run indexer |
| `POST /embeddings/repositories/{id}` | Build vectors |
| `POST /search` | Semantic code search |
| `POST /chat` | Repository Q&A |
| `GET /insights/duplicates` | Duplicate detection |
| `POST /review/pull-request` | PR diff analysis |
| `GET /review/repositories/{id}/architecture` | Dependency summary |

## Docker

```bash
docker compose up --build
```

## Development

```bash
pytest
ruff check src tests
mypy src
```

## Future Improvements

- Background task queue for large monorepos
- Multi-language tree-sitter parsers
- Persistent chat sessions
- IDE plugin integration

## License

MIT
