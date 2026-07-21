# Architecture

CareGuard Stage 1 has five executable boundaries:

1. **Catalogs** load and validate the versioned policy and scenario YAML files with Pydantic v2.
2. **Connectors** translate a common conversation request into a demo, REST, or OpenAI-compatible target call and normalize the answer, sources, tools, provider identity, latency, and errors.
3. **Audit runner** preserves multi-turn history, invokes the connector, and keeps retrieval, admission, answer, tool proposal, and tool execution evidence distinct.
4. **Evaluators** apply deterministic checks and return `PASS`, `PARTIAL`, `FAIL`, or `REVIEW` with a named evidence dimension.
5. **Evidence/reporting** appends one sanitized JSONL record per scenario, indexes run metadata in SQLite, and derives Markdown/JSON reports.

The CareGuard API and demo target are separate FastAPI services under Docker Compose. The CLI can use the demo engine in-process for a zero-network local workflow. Both paths execute the same normalized target behavior.

The default provider is extractive/deterministic. The optional OpenAI-compatible connector reads its key only from server environment state and is restricted to an authorized local endpoint in Stage 1.

