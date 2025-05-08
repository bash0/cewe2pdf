import html
import logging
import math

import reportlab
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from bs4 import BeautifulSoup  # Import BeautifulSoup for HTML parsing
from lxml import etree

def parse_html_text(html):
    """Parses an HTML string, applying default styles from <body> while handling <p>, <span>, <i>, and <b>."""
    soup = BeautifulSoup(html, "html.parser")
    parsed_data = []

    # Default values (override if <body> specifies styles)
    default_font = "Helvetica"
    default_size = 18
    default_color = colors.black

    # Extract global styles from <body> if present
    body_elem = soup.find("body")
    if body_elem and body_elem.get("style"):
        styles = {s.split(":")[0].strip(): s.split(":")[1].strip() for s in body_elem.get("style").split(";") if ":" in s}

        if "font-family" in styles:
            default_font = styles["font-family"].split(",")[0].replace('"', '').replace("'", '')
        if "font-size" in styles:
            default_size = int(styles["font-size"].replace("pt", "").strip())
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
        if "color" in styles:
            font_color = colors.HexColor(styles["color"])

        # Handle <b> and <i> tags
        if elem.name == "b":
            is_bold = True
        if elem.name == "i":
            is_italic = True

        if elem.name == "p":
            # Extract only direct text from <p>, excluding nested elements and ignoring accidental newlines
            paragraph_text = ''.join(t.strip() for t in elem.contents if isinstance(t, str))
        else:
            paragraph_text = elem.text # .strip()

        # Add paragraph breaks for <p> tags
        if elem.name == "p":
            # paragraph_text += "\n"
            paragraph_text += ' '

        # Format text representation
        for char in paragraph_text:
            parsed_data.append((char, font_name, font_size, font_color, is_bold, is_italic))

    return parsed_data


def draw_styled_text_on_arc(c, html, center, radius, start_angle_deg, clockwise=True):
    """
    Draws styled text along a circular arc, applying bold and italic styles dynamically.
    Parameters:
      c               : ReportLab canvas object.
      html            : HTML string containing styled text.
      center          : Tuple (cx, cy) for circle center.
      radius          : Base radius of the arc.
      start_angle_deg : Starting angle (in degrees).
      clockwise       : Boolean flag to determine letter flow direction.
    """
    cx, cy = center
    parsed_text = parse_html_text(html)  # Use the new HTML parser

    # Reverse text placement if `clockwise=False`
    if not clockwise:
        parsed_text.reverse()

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

        # Set font properties dynamically
        c.setFont(full_font, font_size)
        c.setFillColor(font_color)

        # Measure the character's width
        letter_width = pdfmetrics.stringWidth(char, full_font, font_size)

        # Compute letter positioning and rotation
        letter_angle_deg = (letter_width / radius) * (180 / math.pi)
        letter_center_angle = current_angle + (letter_angle_deg / 2 if clockwise else -letter_angle_deg / 2)
        angle_rad = math.radians(letter_center_angle)

        x = cx + radius * math.cos(angle_rad)
        y = cy + radius * math.sin(angle_rad)

        c.saveState()
        c.translate(x, y)
        c.rotate(letter_center_angle + 90)
        c.drawString(-letter_width / 2, 0, char)
        c.restoreState()

        # Adjust angle progression
        current_angle += letter_angle_deg if clockwise else -letter_angle_deg



def draw_text_on_arc(c, text, center, radius, start_angle_deg, fontName, fontSize, fontColor, inside=False):
    """
    Draws text along a circular arc with options for font metrics, color, and correct inside text orientation.
    Code courtesy of Copilot!

    Parameters:
      c               : ReportLab canvas object.
      text            : Text string to be rendered.
      center          : Tuple (cx, cy) representing the center of the circle.
      radius          : Base radius of the circle.
      start_angle_deg : Starting angle (in degrees) for the text.
      fontName        : Name of the font to use (e.g., 'Helvetica').
      fontSize        : Font size in points.
      fontColor       : The color for the text (e.g., colors.blue).
      inside          : Boolean flag; if True, text is drawn along the inner edge ("upside down"), maintaining correct order.
    """
    cx, cy = center

    # Determine effective radius.
    effective_radius = radius if not inside else radius - fontSize

    # Set the font and fill color.
    c.setFont(fontName, fontSize)
    c.setFillColor(fontColor)

    # Reverse text order when inside=True to maintain correct orientation.
    characters = text[::-1] if inside else text

    current_angle = start_angle_deg  # Starting angle for the first character

    for char in characters:
        # Measure the width of the character using font metrics.
        letter_width = pdfmetrics.stringWidth(char, fontName, fontSize)

        # Convert the letter width to an angular span (in degrees) on the circle.
        letter_angle_deg = (letter_width / effective_radius) * (180 / math.pi)

        # Compute the center angle for this character's arc segment.
        letter_center_angle = current_angle + letter_angle_deg / 2
        angle_rad = math.radians(letter_center_angle)

        # Calculate the (x, y) coordinates on the circle using the effective radius.
        x = cx + effective_radius * math.cos(angle_rad)
        y = cy + effective_radius * math.sin(angle_rad)

        # Save the canvas state before applying transformations.
        c.saveState()

        c.translate(x, y)

        # Rotate appropriately�flip direction when inside=True.
        c.rotate(letter_center_angle - 90 if inside else letter_center_angle + 90)

        # Draw the character, offsetting horizontally by half its width to center it.
        c.drawString(-letter_width / 2, 0, char)

        # Restore the canvas state before processing the next character.
        c.restoreState()

        # Update the current angle by the angular width of the printed character.
        current_angle += letter_angle_deg


def handleTextArt(pdf, body, cwtextart, fontname, fontsize):
    if "enabled" in cwtextart[0].attrib:
        enabledAttrib = cwtextart[0].get('enabled')
        if enabledAttrib != '1':
            return

    # print(f"cwtextart {cwtextart}")
    # text = ""
    # for p in htmlparas:
    #     htmlspans = p.findall(".*")
    #     if len(htmlspans) < 1: # i.e. there are no spans, just a paragraph
    #         text = text + p.text
    #     else:
    #         if p.text is not None:
    #             text = text + p.text
    #         for item in htmlspans:
    #             if item.tag == 'br':
    #                 br = item
    #                 text = text + br.tail
    #             elif item.tag == 'span':
    #                 span = item
    #                 if span.text is not None:
    #                     text = text + html.escape(span.text)
    #                 brs = span.findall(".//br")
    #                 if len(brs) > 0:
    #                     for br in brs:
    #                         text = text + br.tail
    #                 if span.tail is not None:
    #                     text = text +  html.escape(span.tail)

    # draw_text_on_arc(pdf, body, (0,0), 100, 270, fontname, fontsize, reportlab.lib.colors.red, True)
    bodyxml = etree.tostring(body, pretty_print=True, encoding="unicode")
    print(bodyxml)
    draw_styled_text_on_arc(pdf, bodyxml, (0,0), 100, 0, clockwise=False)
