# Configuration file for the Sphinx documentation builder.

project = 'Wall-E'
copyright = '2026, Lydia Chheng'
author = 'Lydia Chheng'
release = '0.1.0'

# Add any Sphinx extension module names here, as strings.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that should be ignored.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The theme to use for HTML and PDF output.
html_theme = 'sphinx_rtd_theme'

html_theme_options = {
    'display_version': True,
    'prev_next_buttons_location': 'both',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
}

html_static_path = ['_static']

# RST settings
rst_prolog = """
.. highlight:: c
"""
