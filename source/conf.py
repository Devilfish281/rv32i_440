# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import datetime
import os
import sys

# -- Path setup --------------------------------------------------------------

# If your project is in the parent directory, add it to sys.path
sys.path.insert(0, os.path.abspath("../../src/rv32i_440"))  # Adjust the path as needed

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
project = "CPU Design and Simulation Project"
copyright = "2025, Matthew Dobley"
author = "Matthew Dobley"
release = "0.1.0"
copyright = f"{datetime.datetime.now().year}, {author}"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",  # For Google/NumPy docstring support
    "sphinx_autodoc_typehints",
    "sphinx_rtd_theme",
    # ... other extensions
]


templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"  # If you installed the Read the Docs theme
html_static_path = ["_static"]
