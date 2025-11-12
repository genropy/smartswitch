# Claude Code Instructions - SmartSwitch

## Project Context

**SmartSwitch** is a Python library for intelligent rule-based function dispatch, combining type checking with runtime value conditions.

### Current Status
- **Development Status**: Beta (`Development Status :: 4 - Beta`)
- **Version**: 0.6.0
- **Has Implementation**: Yes (complete with tests and documentation)
- **Coverage**: 82% (197 comprehensive tests)
- **Plugin System**: v0.6.0 with `on_decorate()` hook and metadata sharing

### Project Overview

SmartSwitch provides a clean, Pythonic API for dispatching functions based on:
- Type rules (`typerule`) - Type checking for arguments
- Value rules (`valrule`) - Runtime condition checks
- Named registry - Lookup handlers by function name

The library is optimized for real-world use cases where dispatch overhead is negligible compared to actual work (API calls, database queries, business logic).

## Repository Information

- **Owner**: genropy
- **Repository**: https://github.com/genropy/smartswitch
- **Documentation**: https://smartswitch.readthedocs.io (when live)
- **License**: MIT

## Project Structure

```
smartswitch/
├── .github/workflows/        # CI/CD pipelines
│   ├── test.yml             # Multi-OS tests + coverage
│   ├── docs.yml             # Documentation build
│   └── publish.yml          # PyPI release automation
├── docs/                    # MkDocs documentation
│   ├── index.md            # ✅ Complete
│   ├── installation.md     # ✅ Complete
│   ├── quickstart.md       # ✅ Complete
│   └── guide/basic.md      # ✅ Complete
├── src/smartswitch/
│   ├── __init__.py         # Package exports
│   └── core.py             # Main Switcher class
├── tests/
│   ├── test_smartswitch.py      # Basic tests
│   └── test_complete.py         # 22 comprehensive tests
├── temp/                    # Temporary files (not committed)
├── pyproject.toml          # Package configuration
├── mkdocs.yml              # Documentation config
├── README.md               # Project overview
└── CLAUDE.md               # This file
```

## Language Policy

- **Code, comments, and commit messages**: English
- **Documentation**: English (primary)
- **Communication with user**: Italian (per user preference)

## Git Commit Policy

- **NEVER** include Claude as co-author in commits
- **ALWAYS** remove "Co-Authored-By: Claude <noreply@anthropic.com>" line
- Use conventional commit messages following project style

## Temporary Files Policy

- All temporary files MUST be in `temp/` directory
- `temp/.gitignore` ignores all files except itself
- Never commit temporary files to repository

## Documentation Standards

**SmartSwitch follows We-Birds documentation standards:**

- **Test-First Documentation**: `~/.genro/standards/documentation-standards.md`
- **Architecture & Diagrams**: `~/.genro/standards/documentation-architecture-standards.md`

**Key Requirements**:
- All docs must be derived from tests (no hallucination)
- Architecture page MUST exist at `docs/appendix/architecture.md`
- Architecture page MUST start with Mermaid diagrams (visual-first)
- MkDocs MUST have Mermaid support and `toc.integrate`
- Tech reviews generate `tech_report/tech_report_NNN.md` (private)

## Development Guidelines

### Core Principles

1. **Keep it simple**: The library has no external dependencies (core uses only stdlib)
2. **Performance matters**: Current optimizations include signature caching, pre-compiled type checks, manual kwargs building
3. **Test thoroughly**: Maintain 90%+ coverage (current: 95%)
4. **Document clearly**: Every feature should have examples in docs

### Testing

```bash
# Run tests with coverage
pytest tests/ -v --cov=smartswitch

# Expected: 22/22 tests passed, 95% coverage
```

### Linting

```bash
# Check code style
ruff check src/smartswitch/
black --check src/smartswitch/
mypy src/smartswitch/
```

### Documentation

```bash
# Build docs locally
mkdocs build

# Serve docs for preview
mkdocs serve
```

## CI/CD Setup

The project has complete CI/CD configured:

- **GitHub Actions**: test.yml, docs.yml, publish.yml
- **Codecov**: Target 90% coverage (.codecov.yml)
- **Read the Docs**: Auto-builds from .readthedocs.yaml
- **PyPI Publishing**: Automated via GitHub Actions on tag push

### External Services Setup

**Codecov:**
1. Connect repository at https://codecov.io
2. Add `CODECOV_TOKEN` as GitHub secret

**Read the Docs:**
1. Import project from https://readthedocs.org
2. Configuration already in `.readthedocs.yaml`

## Known Issues and TODOs

### Documentation Status

✅ **All core documentation is complete:**
- User Guide: installation, quickstart, basic usage
- Core Features: named-handlers, api-discovery, typerules, valrules, best-practices
- Plugin System: development guide, middleware pattern, logging (v0.4.0+)
- Examples: 8+ real-world examples
- API Reference: complete with docstrings
- Architecture: comprehensive diagrams and explanations

**Note**: Plugin documentation was reorganized in v0.6.0 from scattered locations into dedicated `docs/plugins/` directory.

### Future Enhancements

- Consider adding async support for async handlers
- Add more examples for common use cases (API routing, event handling, etc.)
- Performance benchmarks documentation

## Release Process

When ready to release:

1. **Update version**:
   - `pyproject.toml` → `version = "x.y.z"`
   - `src/smartswitch/__init__.py` → `__version__ = "x.y.z"`

2. **Verify tests and docs**:
   ```bash
   pytest tests/ -v --cov=smartswitch
   mkdocs build
   ```

3. **Create and push tag**:
   ```bash
   git tag -a vx.y.z -m "Release x.y.z"
   git push origin vx.y.z
   ```

4. **GitHub Actions will automatically**:
   - Run tests on multiple OS/Python versions
   - Build package
   - Publish to PyPI

## Bug History

### Fixed During Development

**Handler not registered by name**: Functions decorated with `typerule`/`valrule` were not added to `_spells` registry, making them unretrievable by name.
- **Fix**: Added `self._spells[func.__name__] = func` in decorator
- **File**: `src/smartswitch/core.py`
- **Impact**: Named handler lookup now works correctly

## Performance Characteristics

- **Dispatch overhead**: ~1-2 microseconds
- **Good for**: Functions doing real work (>1ms) - I/O, business logic, etc.
- **Not ideal for**: Ultra-fast functions (<10μs) called millions of times
- **Optimizations applied**:
  - Signature caching (inspect.signature called once)
  - Pre-compiled type checks
  - Manual kwargs building (avoids bind_partial overhead)
  - `__slots__` for memory efficiency

## Mistakes to Avoid

❌ **DON'T**:
- Add external dependencies to core library
- Commit temporary files outside `temp/`
- Include Claude as co-author in commits
- Break backward compatibility without major version bump
- Skip tests when adding features

✅ **DO**:
- Keep core library dependency-free
- Put temporary work files in `temp/`
- Maintain high test coverage (90%+)
- Document all public APIs
- Follow semantic versioning

---

**Author**: Giovanni Porcari <softwell@softwell.it>
**License**: MIT
**Python**: 3.10+
