"""
Sphinx config file.
Uses several extensions to get API docs and sourcecode.
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

from pathlib import Path
from typing import Optional, Type, TypeVar

import tomlkit

# This assumes that we have the full project root above, containing pyproject.toml
_root = Path(__file__).parent.parent.absolute()
_toml = tomlkit.loads((_root / "pyproject.toml").read_text(encoding="utf8"))

T = TypeVar("T")


def find(key: str, default: Optional[T] = None, as_type: Type[T] = str) -> Optional[T]:
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
_github_user = find("tool.poetry.repository").split("/")[-1]

# Copyright string (for documentation)
# It's not clear whether we're supposed to, but we'll add the license
# noinspection PyShadowingBuiltins
copyright = find("tool.tyrannosaurus.sources.copyright").strip("'")
_license = find("tool.tyrannosaurus.sources.doc_license")
_license_url = find("tool.tyrannosaurus.sources.doc_license_url")
if _license is not None and _license_url is not None:
    _license = _license.strip("'", "")
    copyright += f', <a href="{_license_url}">{_license}</a>'
elif _license is not None:
    copyright += f", {_license}"
_license = find("tool.tyrannosaurus.sources.doc_license")
_license_url = find("tool.tyrannosaurus.sources.doc_license_url")

# Load extensions
# These should be in docs/requirements.txt
# Napoleon is bundled in Sphinx, so we don't need to list it there
# NOTE: 'autoapi' here refers to sphinx-autoapi
# See https://sphinx-autoapi.readthedocs.io/
extensions = [
    "autoapi.extension",
    "sphinx.ext.napoleon",
    "sphinx_copybutton",
    "sphinx_rtd_theme",
    "sphinxcontrib.mermaid",
]
master_doc = "index"
napoleon_include_special_with_doc = True
autoapi_type = "python"
autoapi_dirs = [str(_root / project)]
autoapi_keep_files = True
autoapi_python_class_content = "both"
autoapi_member_order = "groupwise"
autoapi_options = ["private-members", "undoc-members", "special-members"]

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
    github_user=_github_user,
    github_repo=project,
    github_version="main",
    conf_py_path="/docs/",
)

# doc types to build
sphinx_enable_epub_build = False
sphinx_enable_pdf_build = False
exclude_patterns = ["_build", "Thumbs.db", ".*", "~*", "*~", "*#"]

if __name__ == "__main__":
    print(f"{project} v{version}\n© Copyright {copyright}")
