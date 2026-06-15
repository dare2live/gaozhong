# Top-level architecture from first principles

Date: 2026-06-12

Scope: project-wide architecture for modules, data states, and configuration ownership.

## Controller verdict

Verdict: `PROCEED`, but do not declare the current data foundation complete.

The existing layered direction in `docs/architecture.md` is mostly correct:
raw files -> extraction -> DuckDB canonical tables -> nodes/edges -> service/API -> frontend.
The missing top-level contract is a data-state model that distinguishes raw acquisition,
review-only structured drafts, canonical DB imports, derived graph links, and D0 verification.

## First-principles substrate

The product is not "a website that displays teaching content".
It is a teaching and exam-prep operating system whose claims are only useful when the
underlying education data is true, traceable, and narrow enough to verify.

Fundamental truths:

1. A teacher-facing recommendation is only correct if every upstream fact has a known source.
2. A raw file existing on disk is not equivalent to a structured truth row.
3. A structured JSONL row is not equivalent to an import-ready canonical DB row.
4. A green API response is not equivalent to a correct teaching payload.
5. A generated graph edge is not truth; it is a derived claim that needs evidence.
6. Unknown data must remain `unknown`, `partial`, or `needs_review`; it must not become `0`, empty array, or a demo fallback.
7. Configuration owns policy and source contracts; services own computation; DB owns canonical facts; docs/reports own evidence.

## Occam filter

Rejected complexity:

- No new monorepo.
- No event bus.
- No second database.
- No cache layer.
- No per-source mini-framework.
- No separate "exam DB" unless DuckDB tables become a proven bottleneck.

Minimal necessary architecture:

```text
config contracts
  -> source acquisition
  -> extractor
  -> structured draft
  -> review/import gate
  -> canonical DuckDB tables
  -> derived nodes/edges
  -> thin services/API
  -> frontend render only
  -> audit evidence
```

This is simple enough to reason about and still strong enough for D0 accuracy.

## Current historical-paper inventory

Measured from current files and `exam_questions` on 2026-06-12:

| Source family | Local evidence | DB evidence | Current architectural status |
|---|---|---:|---|
| GAOKAO-Bench 2010-2022 | `data/external/gaokao_bench/*.jsonl` | 2010-2022 rows exist; totals vary by year | `imported_canonical`, but not all rows are New Curriculum II D0 truth rows |
| GAOKAO-Bench Updates 2023 | `data/external/gaokao_bench_2023/*.json` | 2023 has 24 rows | `imported_canonical_partial`; needs paper contract review |
| Local PDF 2024/2025 | hard-coded in `scripts/import_recent_exams.py` from sibling gaokao paths | 2024 has 9 rows; 2025 has 9 rows | `imported_canonical_passage_level`; not full item-level truth |
| EOL 2021/2022 | `data/external/exam_sources/eol/*.docx`, `.txt`, structured drafts | not imported by EOL source | `raw_acquired` + `structured_draft`; not import-ready |
| 2021 listening candidate | `data/external/exam_sources/listening_candidates/*sunedu*` | not imported | `candidate_only`; label is New Gaokao I, not II |
| 2023 PDF | `data/external/gaokao_2023_xgkii_english.pdf` | not proven as item-level import source in current check | `raw_acquired_or_legacy`; needs registry entry and extraction contract |

Key implication: the project did capture historical exam material, but the current M0 truth baseline should remain open until each target year has a reviewed source-state transition through import and strict reconciliation.

## Data-state machine

Every external data object must be in exactly one highest achieved state:

| State | Meaning | Required evidence | May feed DB? |
|---|---|---|---|
| `declared` | Source exists in config | `backend/config/sources.yaml` entry | No |
| `raw_acquired` | File exists locally and checksum/size pass | source manifest + sha256 + min bytes | No |
| `text_extracted` | Text extracted from raw artifact | text path + min chars + extraction log | No |
| `structured_draft` | Parser emitted rows with source spans | JSONL + row counts + missing-span report | No |
| `reviewed` | Human/tool review resolved type, answer, span ambiguity | review report + residual list | No |
| `import_ready` | Dry-run import has no unexplained gaps/pollution | strict pre-import diff | Yes |
| `imported_canonical` | Rows exist in canonical DuckDB tables | import batch manifest + DB counts | Yes |
| `linked` | Canonical rows have nodes/edges/tags | graph audit + orphan checks | Yes |
| `d0_verified` | End-to-end gate proves required accuracy | D0 gate + truth-baseline strict report | Yes |

Rule: downstream layers may only consume objects at or above their required state.

## Module architecture

### `backend/services/data_sources/`

Owner: external source registry and acquisition evidence.

Contracts:

- Input: `backend/config/sources.yaml`
- Output: raw files, extracted text, acquisition manifest
- Side effects: write only under `data/external/` and `data/reports/`
- Forbidden: DB writes, question parsing, graph linking

Core responsibilities:

- Load source contracts.
- Download or verify local artifacts.
- Check sha256, size, min text chars, and empty payloads.
- Preserve source URL, landing page, observed scope, and configured status.

### `backend/services/extraction/`

Owner: raw/text -> structured domain drafts.

Contracts:

- Input: files from `data_sources`
- Output: structured JSONL drafts in `data/external/**` or `data/structured/**`
- Side effects: no DB writes unless called by an explicit import step
- Forbidden: silent fallback, cross-domain business policy, UI payload shaping

Submodules:

- `extraction/curriculum.py`
- `extraction/textbook.py`
- `extraction/exam.py`
- `extraction/exam_eol.py` or equivalent if EOL parser graduates from audit script

### `backend/services/imports/`

Owner: structured draft -> canonical DuckDB import.

This module should be added before more exam-source imports.

Contracts:

- Input: reviewed structured drafts and import policy config.
- Output: import batch manifest plus canonical DB rows.
- Side effects: DB writes only in controller-owned write windows.
- Required mode: dry-run diff first, write second.

### `backend/services/canonical.py`

Owner: canonical entity normalization.

It should continue to own stable concept identity, but not source acquisition or parsing.

### `backend/services/links.py` and `backend/services/graph.py`

Owner: derived relationships and graph read model.

Rules:

- `edges` are first-class derived evidence, not raw truth.
- Every non-obvious relation needs `evidence_json`.
- No API route should invent graph relationships ad hoc.

### `backend/services/audit/`

Owner: verifier logic.

Audit modules must classify:

- source completeness
- row/span coverage
- DB reconciliation
- graph orphans
- API payload substance
- frontend real-content smoke

### `backend/api/routes/`

Owner: HTTP contract only.

Rules:

- No raw file reads.
- No business derivation.
- No ad hoc source parsing.
- No route-level JOIN that duplicates service logic.

### `frontend/static/`

Owner: render only.

Rules:

- Fetch typed payloads from API.
- Show degraded/partial/unknown states visibly.
- Never convert missing data into empty normal UI.

## Data architecture

### Raw zone

Paths:

- `data/external/`
- `data/curriculum/`
- `data/textbooks/`

Rules:

- Immutable where practical.
- Content-addressed through sha256.
- One artifact can have many downstream structured drafts.

### Structured draft zone

Paths:

- `data/structured/`
- `data/external/**/structured_draft.jsonl`

Rules:

- Review-only until `import_ready`.
- Must include source file, source span or preview, observed number, answer number if applicable, parser status, and residual findings.

### Canonical DB zone

DuckDB owns canonical project facts:

- curriculum: `cefr_vocab`, `grammar_items`, `theme_contexts`
- textbooks: `textbooks`, `units`, `sections`, `section_text`, `unit_vocab_intro`, `phrases`
- exams: `exam_questions`
- question bank: `question_bank`, `question_tags`, `tag_dictionary`
- graph: `nodes`, `edges`
- audit: `audit_findings`
- file lineage: `file_manifest`

Rule: canonical tables should not store parser uncertainty as normal data. If uncertainty remains, store state as `needs_review` or hold row in structured draft.

### Derived zone

Derived facts:

- graph nodes/edges
- recommendation candidates
- trend outputs
- course material links
- weakness summaries

Rules:

- Regenerable from canonical facts.
- Must not become a second truth source.
- If persisted, include source run id or evidence JSON.

### Evidence zone

Paths:

- `data/reports/`
- `docs/week*_review_round1.md`
- `docs/data_accuracy_audit.md`
- `analysis/project_state_ledger.md`

Rules:

- Evidence can be stale; it is not the truth source.
- Evidence must name the command, exit code, and artifact paths.
- Surprising clean results require verifier verification.

## Configuration architecture

Configuration is the policy layer. A policy duplicated in code is a future data bug.

| Config | Owns | Must not own |
|---|---|---|
| `backend/config/sources.yaml` | source URLs, local paths, sha256, min bytes/chars, observed scope | parser logic |
| `backend/config/question_types.yaml` | question-type names, section grouping, expected numbering | row extraction code |
| `backend/config/thresholds.yaml` | audit thresholds and release gates | source lists |
| `backend/config/course_templates.yaml` | 40-lesson structure and required blocks | generated lesson content |
| `backend/config/content_principles.yaml` | content style constraints and forbidden shortcuts | source-specific rules |
| `backend/config/political_blacklist.yaml` | content exclusion list | audit implementation |
| proposed `backend/config/exam_paper_contracts.yaml` | expected year/paper/section/item coverage | source URLs |
| proposed `backend/config/import_policies.yaml` | import readiness rules and dry-run gates | source extraction |
| proposed `backend/config/allowed_relations.yaml` | valid graph relations and evidence requirements | graph query implementation |

Occam rule: add a new config file only when the policy would otherwise be duplicated in more than one module.

## Target directory shape

Do not move everything at once. This is the target shape:

```text
backend/
  api/routes/                 thin HTTP contracts
  config/                     policy and source contracts
  db/schema.sql               canonical table contracts
  services/
    data_sources/             registry + fetch + acquisition manifests
    extraction/               raw/text -> structured drafts
    imports/                  reviewed drafts -> canonical DB
    canonical.py              stable identity normalization
    links.py                  derived relationship builders
    graph.py                  graph read model
    audit/                    verifiers and D0 gates
    question_bank/            composition and bank-facing service
    course/                   lesson/course material service
    placement/                placement tests and scoring
    students/                 student profile and answer state
scripts/
  tools/
    data_sources/             CLI wrappers for acquisition
    audit/                    CLI wrappers for verifiers
data/
  external/                   raw acquired artifacts and source-local drafts
  structured/                 durable structured sources
  db/                         DuckDB runtime DB
  reports/                    generated evidence
docs/
  data_accuracy_audit.md      D0 state
  top_level_architecture_first_principles.md
analysis/
  project_state_ledger.md     controller ledger
```

## Verification grid

| Layer | Gate | Failure example |
|---|---|---|
| Source acquisition | sha256, min bytes, min text chars, no empty payload | docx URL downloads an HTML error page |
| Extraction | expected rows, source span, answer mapping, no answer contamination in stem | parser matches `31 July` as question 31 |
| Import | dry-run diff, duplicate check, no pollution candidates | EOL source imports shifted answer numbers |
| Canonical DB | primary keys, no orphan foreign references, year/type counts | `exam_questions` has 2022 rows but not the expected target count |
| Graph | nodes/edges no orphans, relation allowlist | route computes relationship outside graph service |
| API | payload schema plus real content check | HTTP 200 with empty list for required data |
| Frontend | renders real fields and degraded flags | partial source shown as complete |
| Release | `data_accuracy_check.py`, truth-baseline strict, Moth/CodeGraph | D0 passes but M0 truth baseline still fails |

## Migration plan

1. Freeze this architecture as the controller contract.
2. Register every existing exam source in `backend/config/sources.yaml`, including GAOKAO-Bench, GAOKAO-Bench Updates, local PDFs, EOL docx, and listening candidates.
3. Convert EOL parser from audit-only script into `backend/services/extraction/exam_eol.py` only after its missing-span audit is clean.
4. Add `backend/services/imports/` with dry-run-first import batches.
5. Replace hard-coded `scripts/import_recent_exams.py` PDF paths with registry-driven source IDs.
6. Add `exam_paper_contracts.yaml` so 2021/2022 New Curriculum II coverage is judged against an explicit expected set.
7. Keep `truth_baseline_audit.py --strict` as the M0 falsification gate until it passes for the configured target scope.

## Load-bearing decisions

1. Source-state machine is mandatory.
2. `sources.yaml` becomes the source contract owner.
3. DB writes require import-ready evidence.
4. Frontend/API cannot turn partial data into normal-looking success.
5. Existing historical exam rows are useful, but not sufficient D0 proof for New Curriculum II coverage.

## Smallest reversible next step

Register all currently known historical exam artifacts in `sources.yaml` and run the data-source acquisition tool in `--reuse-existing --strict` mode.

If that fails, fix the source contract first. Do not patch importers around a broken source contract.
