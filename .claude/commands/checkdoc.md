<!-- gtext:{"outputs":[{"path":"checkdoc.md"}]} -->
<!-- Template for /checkdoc command - combines templates from meta repos -->

# Documentation Review Command

**Purpose**: Perform comprehensive documentation review to detect inconsistencies between code and documentation.

---

## Your Task

You are performing a **documentation consistency review**. Follow these steps systematically:

### 1. **Analyze Current Codebase**

Read the main source files to understand:
- Public API (classes, functions, methods)
- Function signatures and parameters
- Available features and functionality
- Recent changes or new features

### 2. **Review README.md**

Check for:
- **Outdated examples**: Do code examples match current API?
- **Broken links**: Are all links valid?
- **Missing features**: Are new features documented?
- **Incorrect signatures**: Do function calls match actual code?
- **Installation instructions**: Are they current?
- **Usage examples**: Do they work with current version?

### 3. **Review Documentation (docs/)**

If documentation exists, check:
- **API references**: Match actual code signatures
- **Guides and tutorials**: Use current API
- **Code examples**: Are syntactically valid and executable
- **Cross-references**: All internal links work
- **Version information**: Reflects current state

### 4. **Review Jupyter Notebooks (if present)**

Check notebooks for:
- **Executable cells**: Do they run without errors?
- **Import statements**: Match current package structure
- **API usage**: Reflects current version
- **Output cells**: Are they up to date?
- **Dependencies**: Are they current?

### 5. **Report Findings**

Create a structured report with:

#### ✅ Consistent Items
- List what is correctly documented

#### ⚠️ Inconsistencies Found
For each issue:
- **Location**: File and line/section
- **Issue**: Description of inconsistency
- **Current code**: What the code actually does
- **Documentation**: What the docs say
- **Severity**: High/Medium/Low

#### 🔧 Recommended Fixes
Prioritized list of changes needed

---

## Guidelines

- Be thorough but concise
- Focus on user-facing documentation
- Check both inline docstrings and external docs
- Verify all code examples are valid Python syntax
- Test import statements and function calls mentally
- Flag any deprecated features still in docs
- Note missing documentation for new features

---

## Output Format

Provide your findings in this structure:

```markdown
## Documentation Review Report

**Project**: [name]
**Date**: [date]
**Coverage**: README, docs/, notebooks

---

### ✅ What's Good

[List of correctly documented items]

---

### ⚠️ Inconsistencies Found

#### High Priority
1. [Issue with location and details]

#### Medium Priority
1. [Issue with location and details]

#### Low Priority
1. [Issue with location and details]

---

### 🔧 Recommended Actions

1. [Prioritized fix]
2. [Prioritized fix]

---

### 📊 Summary

- Total issues found: X
- High priority: X
- Medium priority: X
- Low priority: X
```

---

**Remember**: Focus on helping users understand and use the project correctly. Documentation is the first impression!


# Library-Specific Documentation Checks

**Context**: This is a Python library in the genro-libs ecosystem.

---

## Additional Library-Specific Checks

Beyond the standard documentation review, check these library-specific items:

### 1. **Package Metadata (pyproject.toml)**

Verify:
- `description` matches README summary
- `keywords` reflect actual functionality
- `classifiers` are accurate
- `dependencies` match actual usage
- `version` is consistent across files

### 2. **API Documentation**

Check that all public APIs are documented:
- Module-level docstrings
- Class docstrings with description
- Method/function docstrings with:
  - Parameters (with types)
  - Return values (with types)
  - Raises (exceptions)
  - Examples (when helpful)

### 3. **Type Hints**

Verify consistency:
- Type hints in code match docstring descriptions
- Return type annotations present
- Parameter type hints match examples

### 4. **Examples and Quickstart**

Ensure examples:
- Import the library correctly
- Use the current API
- Show common use cases
- Are runnable without modification
- Cover main features

### 5. **Installation Instructions**

Check:
- PyPI package name is correct
- Installation command works: `pip install [package-name]`
- Optional dependencies documented if applicable
- Python version requirements accurate

### 6. **Testing Documentation**

If test examples are in docs:
- Test syntax is current
- Test commands work (pytest, etc.)
- Coverage requirements mentioned

### 7. **Changelog/Version History**

If present:
- Latest version documented
- Breaking changes highlighted
- Migration guides for major versions

---

## Library Standards Checklist

- [ ] README has installation section
- [ ] README has quickstart examples
- [ ] README shows import statement
- [ ] All public functions/classes have docstrings
- [ ] Examples use actual package name
- [ ] Type hints present and match docs
- [ ] pyproject.toml metadata is accurate
- [ ] Dependencies are documented
- [ ] License information present

---

**Focus**: Ensure users can install, import, and use the library based on documentation alone.

