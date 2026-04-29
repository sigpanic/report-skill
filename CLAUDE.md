# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP server that generates Word documents from `.doc`/`.docx` templates. Two-stage workflow: (1) **specialization** — analyze a template to create a profile + Skill file, (2) **report generation** — use the Skill to fill content and generate formatted reports.

## Commands

```bash
# Activate venv + install deps
.venv\Scripts\activate && pip install -r requirements.txt

# Run the MCP server (stdio-based)
python -m src.mcp_server.server

# Type checking
pyright src/

# Test: analyze a template
python -c "from src.template_parser.analyzer import analyze_template_compact; import json; print(json.dumps(analyze_template_compact('path/to/template.docx'), ensure_ascii=False, indent=2))"

# Test: generate a report (programmatic)
python -c "from src.doc_generator.generator import generate_report; generate_report(template_path='...', output_path='...', profile={...}, field_values={...}, sections=[...])"
```

## Architecture

### Source Layout

```
src/
├── mcp_server/server.py        # MCP stdio Server + 6 tool handlers
├── protocol/
│   ├── schema.py               # MCP tool JSON Schemas (6 tools)
│   ├── profile_schema.py       # Pydantic models: TemplateProfile, PageSetup, CoverPage, TableInfo, SectionInfo, FormatRules, etc.
│   ├── ts_generator.py         # Auto-generates TypeScript interfaces from Pydantic models
│   └── constants.py            # Agent framework definitions, skill key obfuscation, error messages
├── template_parser/
│   ├── parser.py               # Low-level .doc/.docx parsing (page setup, header/footer, paragraphs, tables, format extraction)
│   ├── analyzer.py             # Builds compact representation, auto-classifies content types, checks profile completeness
│   └── course_parser.py        # Parses .pptx/.ppt/.docx/.doc course materials (with optional OCR via Tesseract)
├── doc_generator/
│   ├── generator.py            # Run-level template copy + content fill: cover fields, table fields, section content, annotations removal
│   └── verifier.py             # Compares generated doc vs template: page setup, paragraphs (font/size/bold/italic), tables
├── skill_generator/
│   └── generator.py            # Generates specialized Skill markdown files from TemplateProfile
└── constraints/
    └── style_rules.py          # Simple constraint passthrough
```

### Data Flow

1. **Template Analysis**: `parser.py` extracts raw doc structure → `analyzer.py` builds compact JSON (text + content_type classification + draft format rules) + TS interface guide
2. **Profile Creation**: LLM writes `TemplateProfile` JSON from compact data + TS interface → `save_profile` validates via Pydantic (`extra="forbid"`) and checks completeness. Format rules come from `_draft_format_rules` (code-extracted) overridden by natural language requirements from annotation text.
3. **Skill Generation**: `generate_skill` fills template strings → produces Skill `.md` → auto-registers to all detected Agent framework dirs (`.trae/skills/`, `.claude/commands/`, `.cursor/rules/`, etc.)
4. **Report Generation**: `generate_report` copies template → run-level replaces cover/text field runs → inserts section content (paragraphs + tables + images) → removes annotations/patterns → saves as `.doc` or `.docx`
5. **Verification**: `verify_format` compares page setup, paragraph formatting (font/alignment), and table dimensions between template and output

### Key Design Decisions

- **LLM-driven semantic understanding**: `analyzer.py` extracts raw structured data; the LLM interprets it to write the `TemplateProfile` JSON. Never hardcode pattern detection in code.
- **Pydantic `extra="forbid"`**: All models reject undefined fields. The TS interfaces are generated from the Pydantic models as the single source of truth.
- **Skill key auth**: Every tool requires a `skill_key` split across two locations in the Skill file. Forces agents to read the full Skill before calling tools.
- **Run-level format preservation**: Generator copies the template `.docx`, then replaces run text in-place. Keeps original font/size/underline/color from the template.
- **Automatic Skill registration**: `generate_skill` detects Agent framework directories and copies the Skill file to all of them.

### Compact Data Format

The compact JSON is simplified to only what the LLM needs:
- `content[]`: paragraphs with `text` (string), `content_type` (classification), and optional `hint: true` for annotation text
- `_draft_format_rules`: code-extracted format defaults (font, spacing) for LLM review
- `_format_notes`: auto-detected format-related keywords found in annotation text
- `_summary`: high-level structure overview
- No run-level format details, no format catalog, no cross-referencing needed

### Important Patterns

- `.doc` files are converted to `.docx` via Windows COM (`win32com.client` - Word must be installed)
- **Profile fields are auto-summarized** from `cover_page.fields` + `tables[].fields` — the top-level `fields` array in the profile is generated by `fix_profile_pydantic()`
- **Cover field matching** uses fuzzy label startswith matching + run-level text replacement
- **Table field matching** matches profile tables to doc tables by row/col count + label similarity
- **Annotation removal** uses `annotation_patterns` (substring) and `removal_patterns` (regex) from the profile
- `analyze_template` also saves a `*_guide.md` file with TS interface definitions for LLM consumption

### Config

- `.env`: `STUDENT_ID`, `STUDENT_NAME`, `STUDENT_CLASS`
- `config.yaml`: `naming_format`, `template_path`, `output_base_dir`
- OCR: Tesseract via `pytesseract` with `chi_sim.traineddata` in project root
