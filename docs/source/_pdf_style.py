"""Custom rinohtype style for Wall-E documentation."""

from rinoh.style import StyleSheet
from rinoh.color import Color

# Create a custom stylesheet
stylesheet = StyleSheet('wall-e')

# Color palette - Enhanced for syntax highlighting
PRIMARY_BLUE = Color(0x2980B9)
DARK_BLUE = Color(0x1a5490)
ACCENT_TEAL = Color(0x16a085)
TEXT_DARK = Color(0x2c3e50)
TEXT_GRAY = Color(0x7f8c8d)
LIGHT_BG = Color(0xecf0f1)

# Code styling colors
CODE_BG = Color(0x272822)      # Monokai dark background
CODE_TEXT = Color(0xf8f8f2)    # Light text
CODE_KEYWORD = Color(0xff79c6)  # Pink for keywords
CODE_STRING = Color(0xa1efe4)   # Cyan for strings
CODE_COMMENT = Color(0x75715e)  # Gray for comments
CODE_NUMBER = Color(0xbd93f9)   # Purple for numbers
INLINE_BG = Color(0xf4f4f4)    # Light gray for inline code
INLINE_TEXT = Color(0xc7254e)  # Dark red for inline code

# Paragraph styles
stylesheet['paragraph'] = dict(
    font_size=10,
    line_spacing=1.3,
    text_color=TEXT_DARK,
    space_above=6,
    space_below=6,
)

# Heading styles with professional formatting
stylesheet['heading'] = dict(
    font_weight='bold',
    text_color=DARK_BLUE,
    space_above=12,
    space_below=6,
)

stylesheet['h1'] = dict(
    base='heading',
    font_size=28,
    text_color=PRIMARY_BLUE,
    space_above=18,
    space_below=12,
)

stylesheet['h2'] = dict(
    base='heading',
    font_size=20,
    text_color=DARK_BLUE,
    space_above=14,
    space_below=8,
)

stylesheet['h3'] = dict(
    base='heading',
    font_size=14,
    text_color=ACCENT_TEAL,
    space_above=10,
    space_below=6,
)

stylesheet['h4'] = dict(
    base='heading',
    font_size=12,
    text_color=TEXT_DARK,
)

# Enhanced code block styling with border and padding
stylesheet['literal block'] = dict(
    font_name='monospace',
    font_size=8.5,
    text_color=CODE_TEXT,
    background_color=CODE_BG,
    padding_left=12,
    padding_right=12,
    padding_top=8,
    padding_bottom=8,
    border_width='0.5pt',
    border_color=DARK_BLUE,
    space_above=10,
    space_above_paragraph=10,
    space_below=10,
    space_below_paragraph=10,
)

# Inline literal (code in text) styling
stylesheet['literal'] = dict(
    font_name='monospace',
    font_size=9,
    text_color=INLINE_TEXT,
    background_color=INLINE_BG,
    padding_left=3,
    padding_right=3,
    border_width='0pt',
)

# Enhanced inline code with better visibility
stylesheet['inline literal'] = dict(
    font_name='monospace',
    font_size=9,
    text_color=INLINE_TEXT,
    background_color=INLINE_BG,
    padding_left=4,
    padding_right=4,
    font_weight='normal',
)

# Code styling for highlighted syntax
stylesheet['code'] = dict(
    font_name='monospace',
    font_size=8.5,
    text_color=CODE_TEXT,
    background_color=CODE_BG,
    padding_left=3,
    padding_right=3,
)

# Highlighted tokens for syntax highlighting
stylesheet['keyword'] = dict(
    font_weight='bold',
    text_color=CODE_KEYWORD,
)

stylesheet['string'] = dict(
    text_color=CODE_STRING,
)

stylesheet['comment'] = dict(
    font_style='italic',
    text_color=CODE_COMMENT,
)

stylesheet['number'] = dict(
    font_weight='bold',
    text_color=CODE_NUMBER,
)

# Lists
stylesheet['bullet list'] = dict(
    space_above=6,
    space_below=6,
)

stylesheet['enumerated list'] = dict(
    space_above=6,
    space_below=6,
)

# Block quotes
stylesheet['block quote'] = dict(
    margin_left=18,
    text_color=TEXT_GRAY,
    border_left='3pt solid ' + str(PRIMARY_BLUE),
    padding_left=10,
)

# Tables
stylesheet['table'] = dict(
    space_above=8,
    space_below=8,
)

# Emphasis and strong
stylesheet['emphasis'] = dict(
    font_style='italic',
)

stylesheet['strong'] = dict(
    font_weight='bold',
    text_color=DARK_BLUE,
)


stylesheet['h3'] = dict(
    base='heading',
    font_size=14,
    text_color=ACCENT_TEAL,
    space_above=10,
    space_below=6,
)

stylesheet['h4'] = dict(
    base='heading',
    font_size=12,
    text_color=TEXT_DARK,
)

# Code formatting
stylesheet['literal'] = dict(
    font_name='monospace',
    font_size=9,
    text_color=CODE_TEXT,
    background_color=CODE_BG,
)

# Lists
stylesheet['bullet list'] = dict(
    space_above=6,
    space_below=6,
)

stylesheet['enumerated list'] = dict(
    space_above=6,
    space_below=6,
)

# Block quotes
stylesheet['block quote'] = dict(
    margin_left=18,
    text_color=TEXT_GRAY,
)

# Tables
stylesheet['table'] = dict(
    space_above=8,
    space_below=8,
)

