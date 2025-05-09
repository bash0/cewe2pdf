import math
import reportlab
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from bs4 import BeautifulSoup  # Import BeautifulSoup for HTML parsing

def parse_html_text(html):
    """Parses an HTML string, applying default styles from <body> while handling <p>, <span>, <i>, and <b>."""
    soup = BeautifulSoup(html, "html.parser")
    parsed_data = []

    # Default values (override if <body> specifies styles)
    default_font = "Helvetica"
    default_size = maxfontsize = 14
    default_color = colors.black

    # Extract global styles from <body> if present
    body_elem = soup.find("body")
    if body_elem and body_elem.get("style"):
        styles = {s.split(":")[0].strip(): s.split(":")[1].strip() for s in body_elem.get("style").split(";") if ":" in s}

        if "font-family" in styles:
            default_font = styles["font-family"].split(",")[0].replace('"', '').replace("'", '')
        if "font-size" in styles:
            default_size = int(styles["font-size"].replace("pt", "").strip())
            maxfontsize = max(maxfontsize, default_size)
        if "color" in styles:
            default_color = colors.HexColor(styles["color"])

    # Scan for supported elements
    for elem in soup.find_all(["span", "p", "i", "b"]):  # Include <p>, <i>, <b>
        style = elem.get("style", "")
        font_name = default_font
        font_size = default_size
        font_color = default_color
        is_bold = False
        is_italic = False

        # Process element-specific styles
        styles = {s.split(":")[0].strip(): s.split(":")[1].strip() for s in style.split(";") if ":" in s}

        if "font-family" in styles:
            font_name = styles["font-family"].split(",")[0].replace('"', '').replace("'", '')
        if "font-size" in styles:
            font_size = int(styles["font-size"].replace("pt", "").strip())
            maxfontsize = max(maxfontsize, font_size)
        if "font-weight" in styles:
            is_bold = int(styles["font-weight"].strip()) > 400
        if "font-style" in styles:
            is_italic = styles["font-style"].strip() == 'italic'
        if "color" in styles:
            font_color = colors.HexColor(styles["color"])

        # Handle <b> and <i> tags
        if elem.name == "b":
            is_bold = True
        if elem.name == "i":
            is_italic = True

        if elem.name == "p":
            # Extract only direct text from <p>, excluding nested elements and ignoring newlines
            paragraph_text = ''.join(t.strip() for t in elem.contents if isinstance(t, str))
        else:
            paragraph_text = elem.text # .strip()

        # Add paragraph breaks for <p> tags
        if elem.name == "p":
            paragraph_text += ' '

        # Format text representation
        for char in paragraph_text:
            parsed_data.append((char, font_name, font_size, font_color, is_bold, is_italic))

    return parsed_data, maxfontsize


def processParsedText(parsed_text, c, radius, start_angle_deg, clockwise, inside):
    cx, cy = (0,0) # center
    current_angle = start_angle_deg

    for char, font_name, font_size, font_color, is_bold, is_italic in parsed_text:
        # Adjust font style based on <b> and <i> attributes
        if is_bold and is_italic:
            full_font = f"{font_name} Bold Italic"
        elif is_bold:
            full_font = f"{font_name} Bold"
        elif is_italic:
            full_font = f"{font_name} Italic"
        else:
            full_font = font_name

        # Measure the character's width
        letter_width = pdfmetrics.stringWidth(char, full_font, font_size)

        # Compute letter positioning and rotation

        # Convert the letter width to an angular span (in degrees) on the circle.
        letter_angle_deg = (letter_width / radius) * (180 / math.pi)
        letter_center_angle = current_angle + (letter_angle_deg / 2 if clockwise else -letter_angle_deg / 2)
        letter_center_radians = math.radians(letter_center_angle)

        x = cx + radius * math.cos(letter_center_radians)
        y = cy + radius * math.sin(letter_center_radians)

        if c is not None: # actually draw the text, rather than just calculating the size
            c.setFont(full_font, font_size)
            c.setFillColor(font_color)
            c.saveState()
            c.translate(x, y)
            # Rotate appropriately, flip direction when inside=True.
            c.rotate(letter_center_angle - 90 if inside else letter_center_angle + 90)
            c.drawString(-letter_width / 2, 0, char)
            c.restoreState()

        # Adjust angle progression
        current_angle += letter_angle_deg if clockwise else -letter_angle_deg

    # return the angular extent
    angle_extent = current_angle - start_angle_deg if clockwise else start_angle_deg - current_angle
    return angle_extent


def draw_styled_text_on_arc(c, bodyhtml, radius, start_angle_deg, clockwise=True, inside=False):
    """
    Draws styled text along a circular arc, applying bold and italic styles dynamically.
    Parameters:
      c               : ReportLab canvas object.
      bodyhtml        : HTML string containing styled text.
      radius          : Base radius of the arc.
      start_angle_deg : Starting angle (in degrees).
      clockwise       : Boolean flag to determine letter flow direction.
    """
    # print(bodyhtml)

    parsed_text, maxfontsize = parse_html_text(bodyhtml)

    # Determine effective radius.
    ascenderHeight = maxfontsize * 0.65 # a good enough guess for the height of the ascenders?
    effective_radius = radius if not inside else radius - ascenderHeight

    # Reverse text placement if necessary
    if clockwise and inside:
        parsed_text.reverse()

    # we have to first calculate the angle used by the entire text without drawing it so
    # that we can place it symmetrically around the given start angle
    angular_extent = processParsedText(parsed_text, None, radius, start_angle_deg, clockwise, inside)
    processParsedText(parsed_text, c, radius, start_angle_deg + 90 - (angular_extent / 2), clockwise, inside)


def handleTextArt(pdf, radius, bodyhtml, cwtextart):
    if "enabled" in cwtextart[0].attrib:
        enabledAttrib = cwtextart[0].get('enabled')
        if enabledAttrib != '1':
            return

    widthAngle = 0
    if "widthAngle" in cwtextart[0].attrib:
        widthAngleAttrib = cwtextart[0].get('widthAngle')
        widthAngle = int(widthAngleAttrib)

    clockwise = True
    if "direction" in cwtextart[0].attrib:
        directionAttrib = cwtextart[0].get('direction')
        clockwise = directionAttrib == '1'

    draw_styled_text_on_arc(pdf, bodyhtml, radius, widthAngle, clockwise=clockwise, inside=True)
