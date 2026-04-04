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

# Syntax highlighting configuration
highlight_language = 'c'

# Code block customization
html_use_smartquotes = True

# Add custom CSS for minimal code styling (RTD theme compatible)
html_css_files = ['custom_code_style.css']

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
    'style_nav_header_background': '#2980B9',
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
}

html_static_path = ['_static']

# Rinohtype PDF configuration for beautiful output
rinohtype_use_pdf_images = True

rinoh_documents = [
    ('index', 'wall-e', 'Wall-E: ESP32 micro-ROS Documentation', 'Lydia Chheng', 'manual'),
]

# Page layout settings
latex_elements = {
    'papersize': 'a4',
    'fontpkg': r'\usepackage{palatino}',
}

# RST settings
rst_prolog = """
.. highlight:: c
"""
