"""The look of the form: page size, colours, sizes and spacing, and the answer formats.

Every measurement is in PDF points (1 point = 1/72 inch, about 0.35 mm). Coordinates follow the PDF itself:
x is measured from the left edge, y from the BOTTOM edge of the page.
"""

# ---- Page (A4)
PAGE_WIDTH = 595.28
PAGE_HEIGHT = 841.89
MARGIN = 42                 # left and right margin
BOTTOM = 39                 # start a new page when content would go below this line (the footer sits under it)

# ---- Colours (red, green, blue; each 0 to 1)
RED = (0.8, 0, 0)           # mandatory boxes and the red * markers
INK = (0, 0, 0)             # text, lines, section outlines
GREY = (0.35, 0.35, 0.35)   # footer and secondary text
RULE = (0.75, 0.75, 0.75)   # thin lines between rows, footer line
WHITE = (1, 1, 1)
ACCENT = (0, 0, 0)          # header line, question numbers, buttons (black: an official form, no brand colour)
TINT = (0.88, 0.88, 0.88)   # grey band behind each section heading
BANK_SHADE = (0.95, 0.95, 0.95)  # background of the "For Bank Use Only" section

# ---- Text sizes
LABEL = 7.5                 # question labels
TEXT = 8.5                  # answers, options and tick-box wording

# ---- Boxes and spacing
BOX = 15                    # height of a one-line answer box
COLUMNS = 12                # each section is a grid of 12 columns; a question takes as many as it needs
COLUMN_GAP = 4              # gap between grid columns
PAD = 6                     # space inside a section's outline
BAND = 13                   # height of a section's grey heading band
SECTION_GAP = 5             # gap between sections
INDENT = 14                 # follow-up questions are indented under the tick box that switches them on
SIGN_OFF = 46               # height of the signature / date / company stamp lines

# 13.2 is the only question placed by hand, to match the approved 4-page copy of the form:
# its label sits beside a fixed-width box, this far after the label.
BESIDE_GAP = 14.7

# ---- Answer formats: (keys refused while typing, what a whole answer must look like, message if it doesn't)
# The first two are regular expressions used by the form's JavaScript in Acrobat.
FORMATS = {
    "number": ("[^0-9]", r"^\d+$", "should be a whole number"),
    "amount": ("[^0-9.,]", r"^\d{1,3}(,?\d{3})*(\.\d{1,2})?$", "is not an amount"),
    "phone": ("[^0-9+() -]", r"^\+?[\d ()-]*\d[\d ()-]*$", "is not a phone number (digits, spaces, + - ( ) only)"),
    "account": ("[^0-9-]", r"^\d[\d-]*\d$|^\d$", "is not an account number (digits and - only)"),
}

# Characters SWIFT messages can't carry (plus # & @ %, used in addresses and company names): refused while typing.
BAD_CHARS = "[^A-Za-z0-9 .,\\-/()':?+#&@%\\r\\n]"
