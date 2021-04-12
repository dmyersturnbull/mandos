"""
Sphinx config file.
Uses several extensions to get API docs and sourcecode.
https://www.sphinx-doc.org/en/master/usage/configuration.html
https://github.com/JamesALeedham/Sphinx-Autosummary-Recursion/blob/master/docs/conf.py
"""
import sys
from pathlib import Path
from typing import Optional, Type, TypeVar

import tomlkit
from sphinx.ext.autosummary import templates

# This assumes that we have the full project root above, containing pyproject.toml
_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, _root)
_toml = tomlkit.loads((_root / "pyproject.toml").read_text(encoding="utf8"))

T = TypeVar("T")


def find(key: str, default: Optional[T] = None, as_type: Type[T] = str) -> Optional[T]:
    """
    Gets a value from pyproject.toml, or a default.
    Args:
        key: A period-delimited TOML key; e.g. ``tools.poetry.name``
        default: Default value if any node in the key is not found
        as_type: Convert non-``None`` values to this type before returning
    Returns:
        The value converted to ``as_type``, or ``default`` if it was not found
    """
    at = _toml
    for k in key.split("."):
        at = at.get(k)
        if at is None:
            return default
    return as_type(at)


# Basic information, used by Sphinx
# Leave language as None unless you have multiple translations
language = None
project = find("tool.poetry.name")
version = find("tool.poetry.version")
release = version
author = ", ".join(find("tool.poetry.authors", as_type=list))

# Copyright string (for documentation)
# It's not clear whether we're supposed to, but we'll add the license
copyright = find("tool.tyrannosaurus.sources.copyright")
_license = find("tool.tyrannosaurus.sources.doc_license")
_license_url = find("tool.tyrannosaurus.sources.doc_license_url")
if _license is not None and _license_url is not None:
    _license = _license.strip("'", "")
    copyright += f', <a href="{_license_url}">{_license}</a>'
elif _license is not None:
    copyright += f", {_license}"

# Paths
templates_path = ["_templates"]
html_static_path = ["_static"]
exclude_patterns = ["_build", "_templates", "Thumbs.db", ".*", "~*", "*~", "*#"]

# Load extensions
# These should be in docs/requirements.txt
# Napoleon is bundled in Sphinx, so we don't need to list it there
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx_autodoc_typehints",
    "sphinx.ext.napoleon",
    "sphinx_copybutton",
    "sphinxcontrib.mermaid",
    "sphinx_rtd_theme",
]

# Configure API docs generation
autosummary_generate = True  # Turn on sphinx.ext.autosummary
autoclass_content = "both"  # Add __init__ doc (ie. params) to class summaries
html_show_sourcelink = False  # Remove 'view source code' from top of page (for html, not python)
autodoc_inherit_docstrings = True  # If no docstring, inherit from base class
# set_type_checking_flag = True  # Enable 'expensive' imports for sphinx_autodoc_typehints
add_module_names = False  # Remove namespaces from class/method signatures
autosummary_imported_members = True
autodoc_default_flags = [
    # Make sure that any autodoc declarations show the right members
    "members",
    "inherited-members",
    "private-members",
    "show-inheritance",
]

# intersphinx_mapping = {
#    "python": ("https://docs.python.org/3/", None),
# }

# Theme configuration
# The vast majority of Sphinx themes are unmaintained
# This includes the commonly used alabaster theme
# The readthedocs theme is pretty good anyway
# These can be specific to the theme, or processed by Sphinx directly
# https://www.sphinx-doc.org/en/master/usage/configuration.html
html_theme = "sphinx_rtd_theme"
html_theme_options = dict(
    collapse_navigation=False,
    navigation_depth=False,
    style_external_links=True,
)
html_context = dict(
    display_github=True,
    github_user="dmyersturnbull",
    github_repo="mandos",
    github_version="main",
    conf_py_path="/docs/",
)

# Doc types to build
sphinx_enable_epub_build = False
sphinx_enable_pdf_build = False


if __name__ == "__main__":
    print(f"{project} v{version}\n© Copyright {copyright}")
