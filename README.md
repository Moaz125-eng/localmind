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

Health check: `GET http://localhost:8000/health`

## Project Layout

```
src/localmind/
├── api/           HTTP routes and application factory
├── core/          Settings, logging, shared utilities
├── indexing/      Repository scanning and metadata storage
├── parsers/       AST and tree-sitter analysis
├── embeddings/    Local embedding generation and FAISS storage
├── search/        Semantic search over indexed code
├── rag/           Retrieval-augmented generation with Ollama
├── visualization/ Architecture and dependency graphs
└── dashboard/     Web UI templates and static assets
```

## License

MIT
