# Repository Guidelines

Read relevant `docs/agent/` files before proceeding:

- `workflow.md` — **read before starting any feature** (issues, branching, PRs)
- `architecture.md` — **read before modifying pipeline or structure**
- `code_conventions.md` — **read before writing code**
- `testing_patterns.md` — **read before writing tests**

---

## Quick Reference

```bash
# Run pipeline
scripts/run.sh /path/to/input [video|sfm|process|train|export ...]
docker/run.sh /path/to/input [same options]

# Dev
scripts/lint.sh              # shellcheck + ruff + pyright + pytest
uv run pytest tests/ -k foo  # run specific test
```

## Key Files

- `scripts/run.sh` — single source of truth for pipeline contract
- `config/defaults.sh` — base defaults for all model types
- `webui.py` — Gradio UI wrapping run.sh

## Workflow

1. Read files before editing
2. Run `scripts/lint.sh` after changes
3. Update `README.md`, `webui.py`, Docker wrappers when changing flags

## Paper References (PaperPipe)

This repo implements methods from scientific papers. Papers are managed via `papi` (PaperPipe).

- Paper DB root: run `papi path` (default `~/.paperpipe/`; override via `PAPER_DB_PATH`).
- Add a paper: `papi add <arxiv_id_or_url>` or `papi add <s2_id_or_url>`.
- Inspect a paper (prints to stdout):
  - Equations (verification): `papi show <paper> -l eq`
  - Definitions (LaTeX): `papi show <paper> -l tex`
  - Overview: `papi show <paper> -l summary`
  - Quick TL;DR: `papi show <paper> -l tldr`
- Direct files (if needed): `<paper_db>/papers/{paper}/equations.md`, `source.tex`, `summary.md`, `tldr.md`, `figures/`

MCP Tools (if configured):
- `leann_search(index_name, query, top_k)` - Fast semantic search, returns snippets + file paths
- `retrieve_chunks(query, index_name, k)` - Detailed retrieval with formal citations (DOI, page numbers)
  - `embedding_model` is optional (auto-inferred from index metadata)
  - If specified, must match index's embedding model (check via `list_pqa_indexes()`)
- **Embedding priority** (prefer in order): Voyage AI → Google/Gemini → OpenAI → Local (Ollama)
  - Check available indexes: `leann_list()` or `list_pqa_indexes()`
- **When to use:** `leann_search` for exploration, `retrieve_chunks` for verification/citations

Rules:
- For "does this match the paper?", use `papi show <paper> -l eq` / `-l tex` and compare symbols step-by-step.
- For "which paper mentions X?":
  - Exact string hits (fast): `papi search --rg "X"` (case-insensitive literal by default)
  - Regex patterns: `papi search --rg --regex "pattern"` (for complex patterns like `BRDF\|material`)
  - Ranked search (BM25): `papi index --backend search --search-rebuild` then `papi search "X"`
  - Hybrid (ranked + exact boost): `papi search --hybrid "X"`
  - MCP semantic search: `leann_search()` or `retrieve_chunks()`
- If the agent can't read `~/.paperpipe/`, export context into the repo: `papi export <papers...> --level equations --to ./paper-context/`.
- Use `papi ask "..."` only when you explicitly want RAG synthesis (PaperQA2 default if installed; optional `--backend leann`).
  - For cheaper/deterministic queries: `papi ask "..." --pqa-agent-type fake`
  - For machine-readable evidence: `papi ask "..." --format evidence-blocks`
  - For debugging PaperQA2 output: `papi ask "..." --pqa-raw`
