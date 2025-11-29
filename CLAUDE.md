# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Essential Commands (use these exact commands):**
- `uv run poe format` - Format code (BLACK + RUFF) - ONLY allowed formatting command
- `uv run poe type-check` - Run mypy type checking - ONLY allowed type checking command  
- `uv run poe test` - Run tests with default markers (excludes java/rust by default)
- `uv run poe test -m "python or go"` - Run specific language tests
- `uv run poe lint` - Check code style without fixing

**Test Markers:**
Available pytest markers for selective testing:
- `python`, `go`, `java`, `rust`, `typescript`, `php`, `perl`, `csharp`, `elixir`, `terraform`, `clojure`, `swift`, `bash`, `ruby`, `ruby_solargraph`
- `snapshot` - for symbolic editing operation tests

**Project Management:**
- `uv run serena-mcp-server` - Start MCP server from project root
- `uv run index-project` - Index project for faster tool performance

**Always run format, type-check, and test before completing any task.**

## Architecture Overview

Serena is a dual-layer coding agent toolkit:

### Core Components

**1. SerenaAgent (`src/serena/agent.py`)**
- Central orchestrator managing projects, tools, and user interactions
- Coordinates language servers, memory persistence, and MCP server interface
- Manages tool registry and context/mode configurations

**2. SolidLanguageServer (`src/solidlsp/ls.py`)**  
- Unified wrapper around Language Server Protocol (LSP) implementations
- Provides language-agnostic interface for symbol operations
- Handles caching, error recovery, and multiple language server lifecycle

**3. Tool System (`src/serena/tools/`)**
- **file_tools.py** - File system operations, search, regex replacements
- **symbol_tools.py** - Language-aware symbol finding, navigation, editing
- **memory_tools.py** - Project knowledge persistence and retrieval
- **config_tools.py** - Project activation, mode switching
- **workflow_tools.py** - Onboarding and meta-operations

**4. Configuration System (`src/serena/config/`)**
- **Contexts** - Define tool sets for different environments (desktop-app, agent, ide-assistant)
- **Modes** - Operational patterns (planning, editing, interactive, one-shot)
- **Projects** - Per-project settings and language server configs

### Language Support Architecture

Each supported language has:
1. **Language Server Implementation** in `src/solidlsp/language_servers/`
2. **Runtime Dependencies** - Automatic language server downloads when needed
3. **Test Repository** in `test/resources/repos/<language>/`
4. **Test Suite** in `test/solidlsp/<language>/`

### Memory & Knowledge System

- **Markdown-based storage** in `.serena/memories/` directories
- **Project-specific knowledge** persistence across sessions
- **Contextual retrieval** based on relevance
- **Onboarding support** for new projects

## Development Patterns

### Adding New Languages
1. Create language server class in `src/solidlsp/language_servers/`
2. Add to Language enum in `src/solidlsp/ls_config.py` 
3. Update factory method in `src/solidlsp/ls.py`
4. Create test repository in `test/resources/repos/<language>/`
5. Write test suite in `test/solidlsp/<language>/`
6. Add pytest marker to `pyproject.toml`

### Adding New Tools
1. Inherit from `Tool` base class in `src/serena/tools/tools_base.py`
2. Implement required methods and parameter validation
3. Register in appropriate tool registry
4. Add to context/mode configurations

### Testing Strategy
- Language-specific tests use pytest markers
- Symbolic editing operations have snapshot tests
- Integration tests in `test_serena_agent.py`
- Test repositories provide realistic symbol structures

## Configuration Hierarchy

Configuration is loaded from (in order of precedence):
1. Command-line arguments to `serena-mcp-server`
2. Project-specific `.serena/project.yml`
3. User config `~/.serena/serena_config.yml`
4. Active modes and contexts

## Key Implementation Notes

- **Symbol-based editing** - Uses LSP for precise code manipulation
- **Caching strategy** - Reduces language server overhead
- **Error recovery** - Automatic language server restart on crashes
- **Multi-language support** - 16+ languages with LSP integration
- **MCP protocol** - Exposes tools to AI agents via Model Context Protocol
- **Async operation** - Non-blocking language server interactions

## Spectrena Lineage Integration

This Serena fork includes automatic lineage tracking for Spectrena projects. When Serena is used in a project with Spectrena lineage enabled, all code edits are automatically recorded with task context.

### How It Works

**Dual MCP Server Architecture:**
```
Claude Code
    │
    ├──► spectrena-mcp (task_start, task_complete, ready_specs)
    │           │
    │           ▼
    │    ┌─────────────────┐
    └──► │ .spectrena/     │ ◄── serena-mcp (replace_symbol, insert_after)
         │ lineage         │         │
         └─────────────────┘         │
                                     │
         (Serena auto-records edits with active task context)
```

### Modified Tools

All symbolic editing tools now support optional `task_id` parameter and automatic lineage recording:

- `replace_symbol_body(name_path, relative_path, body, task_id=None)` - Records symbol modifications
- `insert_after_symbol(name_path, relative_path, body, task_id=None)` - Records insertions
- `insert_before_symbol(name_path, relative_path, body, task_id=None)` - Records insertions
- `rename_symbol(name_path, relative_path, new_name, task_id=None)` - Records renames

**Behavior:**
- If `task_id` is provided explicitly, uses that task ID
- If `task_id` is None, automatically retrieves active task from `.spectrena/lineage` database
- If no task context is available, edits proceed normally without recording (graceful degradation)
- All recording is logged for debugging

### Lineage Database Detection

The lineage recorder searches upward from the current directory for:
- `.spectrena/lineage.db` (SQLite backend)
- `.spectrena/lineage/` (SurrealDB embedded backend)

If no database is found, Serena operates normally without lineage tracking.

### Recorded Information

Each code change records:
- **task_id**: Spectrena task identifier (e.g., "CORE-001-T01")
- **file_path**: Relative path to modified file
- **symbol_fqn**: Fully qualified symbol name (e.g., "src/auth.py:User.authenticate")
- **change_type**: "modify", "create", "rename", or "delete"
- **tool_used**: Serena tool name
- **old_content_hash**: SHA-256 hash of content before edit (for diffing)
- **new_content_hash**: SHA-256 hash of content after edit
- **timestamp**: ISO-8601 timestamp

### Benefits

- **Full traceability**: Spec → task → code changes
- **Impact analysis**: "What code was touched by task X?"
- **Automatic**: No manual `record_change()` calls required
- **Non-invasive**: Works with or without Spectrena
- **Backward compatible**: Existing Serena workflows unchanged

### Implementation Protocol

When working on Spectrena-managed projects:

1. **Before coding**: `task_start(task_id)` via spectrena-mcp to set context
2. **Read spec**: Use `task_context(task_id)` for requirements
3. **Find code**: Use Serena `find_symbol` to locate edit points
4. **Edit code**: Use Serena edit tools (auto-tracked!)
5. **Complete**: `task_complete(task_id, minutes)` via spectrena-mcp

## Working with the Codebase

- Project uses Python 3.11 with `uv` for dependency management
- Strict typing with mypy, formatted with black + ruff
- Language servers run as separate processes with LSP communication
- Memory system enables persistent project knowledge
- Context/mode system allows workflow customization