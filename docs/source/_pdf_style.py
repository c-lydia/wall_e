"""Custom rinohtype style for Wall-E documentation."""

from rinoh.style import StyleSheet, Matcher
from rinoh.styles import style as default_style
from rinoh.text import Paragraph
from rinoh.flowable import Code

# Create a custom stylesheet
stylesheet = StyleSheet('Wall-E', base=default_style)

# Define colors
primary_blue = '#2980B9'
dark_blue = '#1a5490'
light_gray = '#f5f5f5'
dark_gray = '#333333'

# Styling rules
stylesheet['Paragraph'] = dict(
    font_size=11,
    line_spacing=1.2,
    text_align='justify',
)

stylesheet['Heading 1'] = dict(
    font_size=24,
    font_weight='bold',
    font_color=dark_blue,
    space_above=18,
    space_below=12,
)

stylesheet['Heading 2'] = dict(
    font_size=18,
    font_weight='bold',
    font_color=primary_blue,
    space_above=14,
    space_below=10,
)

stylesheet['Heading 3'] = dict(
    font_size=14,
    font_weight='bold',
    font_color='#333333',
    space_above=10,
    space_below=6,
)

stylesheet['Literal'] = dict(
    font_family='monospace',
    font_size=10,
    font_color='#d73a49',
)

stylesheet['Code'] = dict(
    font_family='monospace',
    font_size=10,
    background_color=light_gray,
    padding=5,
)

stylesheet['Emphasis'] = dict(
    font_style='italic',
)

stylesheet['Strong'] = dict(
    font_weight='bold',
)
