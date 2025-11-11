"""Sphinx configuration for SmartSwitch documentation."""

import os
import sys
from pathlib import Path

# Add source directory to path for autodoc
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Project information
project = "SmartSwitch"
copyright = "2025, Genropy Team"
author = "Genropy Team"
release = "0.5.0"
version = "0.5"

# General configuration
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.githubpages",
    "sphinx_autodoc_typehints",
    "myst_parser",  # For Markdown support
    "sphinxcontrib.mermaid",  # For Mermaid diagrams - CRITICAL for architecture docs
]

# MyST Parser configuration (Markdown)
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "substitution",
    "tasklist",
]
myst_heading_anchors = 3

# CRITICAL: Treat ```mermaid blocks as mermaid directives
myst_fence_as_directive = ["mermaid"]

# Source files
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# The master toctree document
master_doc = "index"

# List of patterns to ignore
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "dev-notes",  # Exclude development notes from published docs
    "temp",  # Exclude temporary files
]

# Suppress specific warnings
suppress_warnings = [
    "toc.not_included",  # Documents not in toctree (like README, etc.)
    "myst.xref_missing",  # Missing cross-references (external links, etc.)
    "misc.highlighting_failure",  # Highlighting failures for special characters
]

# HTML output configuration
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "includehidden": True,
    "titles_only": False,
    "prev_next_buttons_location": "bottom",
    "style_external_links": True,
}

html_static_path = ["_static", "assets"]
html_css_files = ["custom.css"]

# Logo and favicon paths (relative to docs/ directory)
_logo_path = Path(__file__).parent / "assets" / "logo.png"
html_logo = "assets/logo.png" if _logo_path.exists() else None
html_favicon = "assets/logo.png" if _logo_path.exists() else None

# HTML context
html_context = {
    "display_github": True,
    "github_user": "genropy",
    "github_repo": "smartswitch",
    "github_version": "main",
    "conf_py_path": "/docs/",
}

# Autodoc configuration
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

# Intersphinx configuration
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# Napoleon configuration (Google-style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = True
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Mermaid configuration (CRITICAL for diagrams)
mermaid_output_format = "raw"
mermaid_init_js = """
mermaid.initialize({
    startOnLoad: true,
    theme: 'default',
    flowchart: {
        useMaxWidth: true,
        htmlLabels: true
    }
});
"""
