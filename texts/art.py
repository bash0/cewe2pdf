import logging
import math
from bs4 import BeautifulSoup  # Import BeautifulSoup for HTML parsing
from lxml import etree
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics

from borders import processDecorationBorders
from fontHandling import getMissingFontSubstitute
from conversionState import ConversionState
from renderContext import RenderContext

# A CEWE 8.1 TextArt box has no stored radius.  A newly-created 490-unit
# square box has the same arc as the 171-unit legacy wrapper-table margin.
CEWE8_DEFAULT_TEXTART_RADIUS_RATIO = 171 / 490

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

        # Format text representation
        for char in paragraph_text:
            parsed_data.append((char, font_name, font_size, font_color, is_bold, is_italic))

    return parsed_data, maxfontsize


def processParsedText(parsed_text, pdf, originalRadius, start_angle_deg, clockwise, maxfontsize,
                      state: ConversionState, circleCenterY=0, ellipseRadiusY=None):
    notifiedFontError = False
    cx, cy = (0, circleCenterY)
    current_angle = start_angle_deg

    for char, font_name, font_size, font_color, is_bold, is_italic in parsed_text:
        # Adjust font style based on <b> and <i> attributes. This reliance on a naming convention
        # is a bit weak, though there are only a few fonts / font families which do not follow it.
        # You can find those unconventional fonts by setting the config logger message level to info.
        if is_bold and is_italic:
            full_font = f"{font_name} Bold Italic"
        elif is_bold:
            full_font = f"{font_name} Bold"
        elif is_italic:
            full_font = f"{font_name} Italic"
        else:
            full_font = font_name

        # Measure the character's width. This will fail with a KeyError if the
        # font is missing, which it might be for unconventionally named fonts
        try:
            letter_width = pdfmetrics.stringWidth(char, full_font, font_size)
        except KeyError:
            fail_font = full_font
            full_font = getMissingFontSubstitute(font_name, state) # honouring any configured font substitutions
            if not notifiedFontError: # just one message per text art
                logging.error(f"Unregistered font in TextArt: {fail_font}, font substitution: {full_font}")
                notifiedFontError = True
            letter_width = pdfmetrics.stringWidth(char, full_font, font_size)

        # Convert the letter width to an angular span (in degrees).  Legacy
        # TextArt follows a circle; CEWE 8 rectangle TextArt follows an
        # ellipse, whose local arc length varies with the current angle.
        if ellipseRadiusY is None:
            arc_radius = originalRadius
        else:
            current_angle_radians = math.radians(current_angle)
            arc_radius = math.hypot(
                originalRadius * math.sin(current_angle_radians),
                ellipseRadiusY * math.cos(current_angle_radians))
        letter_angle_deg = (letter_width / arc_radius) * (180 / math.pi)
        letter_center_angle = current_angle + letter_angle_deg / 2
        letter_center_radians = math.radians(letter_center_angle)

        # Compute letter positioning and rotation
        # For clockwise we need to reduce the radius and to move the letter
        # placement inwards, putting the top of the letter up against the arc
        radius_x = originalRadius - maxfontsize * 0.7 if clockwise else originalRadius
        radius_y = ellipseRadiusY if ellipseRadiusY is not None else originalRadius
        if clockwise:
            radius_y -= maxfontsize * 0.7
        x = cx + radius_x * math.cos(letter_center_radians)
        y = cy + radius_y * math.sin(letter_center_radians)

        if pdf is not None: # actually draw the text, rather than just calculating the size
            pdf.saveState()
            pdf.setFont(full_font, font_size)
            pdf.setFillColor(font_color)
            pdf.translate(x, y)
            # The ellipse tangent is the baseline. Reversing it produces the
            # clockwise orientation while retaining the legacy circle result.
            tangent_angle = math.degrees(math.atan2(
                radius_y * math.cos(letter_center_radians),
                -radius_x * math.sin(letter_center_radians)))
            pdf.rotate(tangent_angle + 180 if clockwise else tangent_angle)
            pdf.drawString(-letter_width / 2, 0, char)
            pdf.restoreState()

        # Adjust angle progression
        current_angle += letter_angle_deg

    # return the angular extent
    angle_extent = current_angle - start_angle_deg

    # uncomment this to see the arc, amongst other things you can see that the
    # text is drawn with the baseline on the arc
    # if c is not None:
    #     print(f"Start angle {start_angle_deg}, extent {angle_extent}, originalRadius {originalRadius}, radius {radius}, clockwise {clockwise}")
    #     c.arc(-originalRadius, -originalRadius, +originalRadius, +originalRadius, startAng=start_angle_deg, extent=angle_extent)

    return angle_extent


def draw_styled_text_on_arc(pdf, bodyhtml, radius, start_angle_deg, state: ConversionState,
                            clockwise=True, circleCenterY=0, ellipseRadiusY=None):
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

    # Determine effective radius. This adjusts the radius by an empirically
    # determined value to account for the placement of the baseline in the
    # letter. This radius will be the same for both clockwise and anti, but
    # we'll have to adjust the letters individually in relation to this
    fiddleFactor = maxfontsize * 0.9
    effectiveRadius = radius + fiddleFactor
    effectiveEllipseRadiusY = None
    if ellipseRadiusY is not None:
        effectiveEllipseRadiusY = ellipseRadiusY + fiddleFactor

    # Reverse text placement if necessary
    if clockwise:
        parsed_text.reverse()

    # we have to first calculate the angle used by the entire text without drawing it so
    # that we can place it symmetrically around the given start angle
    givenStartAngle = 90 - start_angle_deg if clockwise else start_angle_deg - 90
    angularExtent = processParsedText(parsed_text, None, effectiveRadius, start_angle_deg,
        clockwise, maxfontsize, state, ellipseRadiusY=effectiveEllipseRadiusY)
    centredStartAngle = givenStartAngle - (angularExtent * 0.5)

    processParsedText(parsed_text, pdf, effectiveRadius, centredStartAngle, clockwise, maxfontsize,
                      state, circleCenterY, effectiveEllipseRadiusY)


def handleTextArt(pdf, radius, bodyhtml, cwtextart, state: ConversionState, circleCenterY=0,
                  ellipseRadiusY=None):
    if "enabled" in cwtextart[0].attrib:
        enabledAttrib = cwtextart[0].get('enabled')
        if enabledAttrib != '1':
            return

    widthAngle = 0
    if "widthAngle" in cwtextart[0].attrib:
        widthAngleAttrib = cwtextart[0].get('widthAngle')
        widthAngle = int(widthAngleAttrib)

    direction = True
    if "direction" in cwtextart[0].attrib:
        directionAttrib = cwtextart[0].get('direction')
        direction = directionAttrib == '1'

    draw_styled_text_on_arc(pdf, bodyhtml, radius, widthAngle, state,
                            clockwise=direction, circleCenterY=circleCenterY,
                            ellipseRadiusY=ellipseRadiusY)


def processTextArt(area, areaWidth, areaHeight, areaRot, pdf, transCx, transCy, body, leftPad, topPad,
                   cwtextart, context: RenderContext, state: ConversionState):
    """Render one TextArt area, including its border and arc geometry."""
    pdf.translate(transCx, transCy)
    pdf.rotate(-areaRot)
    for decorationTag in area.findall('decoration'):
        processDecorationBorders(decorationTag, areaHeight, areaWidth, pdf, context)
    bodyhtml = etree.tostring(body, pretty_print=True, encoding="unicode")

    # CEWE 7 and earlier put a TextArt radius in the margin of the wrapper
    # table in the HTML text. CEWE 8.1 saves the same TextArt as a plain
    # paragraph, without retaining that margin or introducing a dedicated
    # radius attribute. Retain the legacy circular value when present.
    #
    # The CEWE 8 rectangle behaviour is an ellipse: its horizontal and
    # vertical radii scale independently with the area's width and height.
    # The top inset is based on the shorter box side. This leaves a tall
    # TextArt box in its established position, but moves a wide ellipse up so
    # that its text stays equally close to the top edge. The radius ratio is
    # calibrated from CEWE's 490 x 490 MCF-unit default TextArt area, whose
    # legacy representation held a 171-unit radius.
    #
    # CEWE's TextArt "inside margin" is textFormat.IndentMargin. The parser
    # has already converted it to leftPad/topPad. It reduces the radii while
    # retaining the same ellipse centre, moving the whole arc inward.
    radius = topPad - leftPad
    circleCenterY = 0
    ellipseRadiusY = None
    if radius <= 0:
        baseRadius = (context.mcf_to_reportlab * areaWidth
                      * CEWE8_DEFAULT_TEXTART_RADIUS_RATIO)
        radius = max(1.0, baseRadius - leftPad)
        if areaHeight != areaWidth:
            baseEllipseRadiusY = (context.mcf_to_reportlab * areaHeight
                                  * CEWE8_DEFAULT_TEXTART_RADIUS_RATIO)
            ellipseRadiusY = max(1.0, baseEllipseRadiusY - topPad)
            shorterSide = min(areaWidth, areaHeight)
            topOfEllipse = context.mcf_to_reportlab * (
                areaHeight * 0.5
                - shorterSide * (0.5 - CEWE8_DEFAULT_TEXTART_RADIUS_RATIO))
            circleCenterY = topOfEllipse - baseEllipseRadiusY
    handleTextArt(pdf, radius, bodyhtml, cwtextart, state, circleCenterY, ellipseRadiusY)
    pdf.rotate(areaRot)
    pdf.translate(-transCx, -transCy)
