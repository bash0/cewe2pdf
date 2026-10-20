import logging
import math
from functools import partial
from bs4 import BeautifulSoup  # Import BeautifulSoup for HTML parsing
from lxml import etree
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics

from decorations.borders import processDecorationBorders
from fonts.manager import getMissingFontSubstitute
from conversionState import ConversionState
from renderContext import RenderContext
from .spacing import getLetterSpacing
from .backgrounds import drawTextArtBackground
from .shadows import drawTextArtShadow

# A CEWE 8.1 TextArt box has no stored radius.  A newly-created 490-unit
# square box has the same arc as the 171-unit legacy wrapper-table margin.
CEWE8_DEFAULT_TEXTART_RADIUS_RATIO = 171 / 490
# The same default box leaves 74 MCF units above the arc for 18-point text.
# This is a font inset, not a fraction of a resized box: otherwise large
# lettering can rise above its area even when its curve has the right shape.
CEWE8_DEFAULT_TEXTART_TOP_INSET_MCF_PER_POINT = (490 / 2 - 171) / 18

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


def measureTextArtGlyphs(parsed_text, state: ConversionState):
    """Resolve fonts and widths once, shared by centring and drawing."""
    notifiedFontError = False
    glyphs = []
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

        glyphs.append((char, full_font, font_size, font_color, letter_width))
    return glyphs


def getTextArtGlyphAngles(glyphs, radiusX, startAngle, radiusY=None, letterSpacing=0):
    """Return glyph centres and total angular extent, with gaps only between glyphs."""
    currentAngle = startAngle
    angles = []
    for index, glyph in enumerate(glyphs):
        if radiusY is None:
            arcRadius = radiusX
        else:
            angleRadians = math.radians(currentAngle)
            arcRadius = math.hypot(
                radiusX * math.sin(angleRadians), radiusY * math.cos(angleRadians))
        letterAngle = math.degrees(glyph[4] / arcRadius)
        angles.append(currentAngle + letterAngle / 2)
        currentAngle += letterAngle
        # Tracking changes the advance, not the glyph's width or its rotation
        # about its own centre. Negative gaps are intentional and must not be
        # clamped, even when they make neighbouring characters overlap.
        if index < len(glyphs) - 1:
            currentAngle += math.degrees(letterSpacing / arcRadius)
    return angles, currentAngle - startAngle


def getCentredTextArtStartAngle(glyphs, radiusX, centreAngle, radiusY=None, letterSpacing=0):
    """Centre the measured arc at the same angle used when it is drawn."""
    _, extent = getTextArtGlyphAngles(glyphs, radiusX, centreAngle, radiusY, letterSpacing)
    if radiusY is None or radiusY == radiusX:
        return centreAngle - extent / 2

    # On an ellipse, measuring at 0 degrees and drawing near 90 degrees gives
    # different extents. Solve start + extent(start)/2 = centre instead.
    # The minimum local radius bounds every advance, including negative gaps,
    # so these endpoints bracket a solution without a font- or box-size guess.
    maximumDistance = sum(glyph[4] for glyph in glyphs) + abs(letterSpacing) * max(0, len(glyphs) - 1)
    maximumExtent = math.degrees(maximumDistance / min(radiusX, radiusY))
    lower = centreAngle - maximumExtent
    upper = centreAngle + maximumExtent
    startAngle = centreAngle
    for _ in range(40):
        startAngle = (lower + upper) / 2
        _, extent = getTextArtGlyphAngles(glyphs, radiusX, startAngle, radiusY, letterSpacing)
        error = startAngle + extent / 2 - centreAngle
        if abs(error) < 1e-8:
            break
        if error < 0:
            lower = startAngle
        else:
            upper = startAngle
    return startAngle


def getTextArtGlyphPosition(radiusX, radiusY, angle, baselineInset=0):
    """Return a baseline point offset perpendicular to the original curve."""
    theta = math.radians(angle)
    cosTheta, sinTheta = math.cos(theta), math.sin(theta)
    if radiusX == radiusY:
        # For a circle this is exactly the old inward radius adjustment,
        # including the tangent calculation used by the approved examples.
        radiusX -= baselineInset
        radiusY -= baselineInset
        x, y = radiusX * cosTheta, radiusY * sinTheta
    else:
        x, y = radiusX * cosTheta, radiusY * sinTheta
        if baselineInset != 0:
            # An ellipse's normal is proportional to (b*cos(t), a*sin(t)).
            # Subtracting the inset from both axes instead pulls the letters
            # sideways towards the centre and crowds wide, shallow TextArt.
            normalLength = math.hypot(radiusY * cosTheta, radiusX * sinTheta)
            x -= baselineInset * radiusY * cosTheta / normalLength
            y -= baselineInset * radiusX * sinTheta / normalLength
    tangent = math.degrees(math.atan2(radiusY * cosTheta, -radiusX * sinTheta))
    return x, y, tangent


def drawTextArtGlyphs(glyphs, angles, pdf, radiusX, radiusY, clockwise, circleCenterY=0, baselineInset=0):
    """Draw measured glyphs without changing their size for letter spacing."""
    if radiusY is None:
        radiusY = radiusX
    for glyph, letter_center_angle in zip(glyphs, angles):
        char, full_font, font_size, font_color, letter_width = glyph
        x, y, tangent_angle = getTextArtGlyphPosition(radiusX, radiusY, letter_center_angle, baselineInset)

        pdf.saveState()
        pdf.setFont(full_font, font_size)
        pdf.setFillColor(font_color)
        pdf.translate(x, circleCenterY + y)
        pdf.rotate(tangent_angle + 180 if clockwise else tangent_angle)
        pdf.drawString(-letter_width / 2, 0, char)
        pdf.restoreState()


def draw_styled_text_on_arc(pdf, bodyhtml, radius, start_angle_deg, state: ConversionState,
                            clockwise=True, circleCenterY=0, ellipseRadiusY=None, letterSpacing=0):
    """
    Draw styled text on its curve, or return the prepared drawing when pdf is None.
    Parameters:
      c               : ReportLab canvas object.
      bodyhtml        : HTML string containing styled text.
      radius          : Base radius of the arc.
      start_angle_deg : Starting angle (in degrees).
      clockwise       : Boolean flag to determine letter flow direction.
    """
    # print(bodyhtml)

    glyphs, maxfontsize = parse_html_text(bodyhtml)

    # Determine effective radius. This adjusts the radius by an empirically
    # determined value to account for the placement of the baseline in the
    # letter. This radius will be the same for both clockwise and anti, but
    # we'll have to adjust the letters individually in relation to this
    fiddleFactor = maxfontsize * 0.9
    effectiveRadius = radius + fiddleFactor
    effectiveEllipseRadiusY = None
    if ellipseRadiusY is not None:
        effectiveEllipseRadiusY = ellipseRadiusY + fiddleFactor

    # Preserve the empirically matched advance radius. The painted clockwise
    # baseline is inset separately; measuring advances on that smaller curve
    # lengthens the text's angular span, unlike CEWE's crowded lettering.
    glyphHeight = maxfontsize * 0.7
    if clockwise:
        glyphs.reverse()

    # Resolve the same font metrics for both measurement and drawing. This
    # also avoids repeating missing-font diagnostics during ellipse centring.
    glyphs = measureTextArtGlyphs(glyphs, state)
    givenStartAngle = 90 - start_angle_deg if clockwise else start_angle_deg - 90
    centredStartAngle = getCentredTextArtStartAngle(
        glyphs, effectiveRadius, givenStartAngle, effectiveEllipseRadiusY, letterSpacing)
    angles = getTextArtGlyphAngles(
        glyphs, effectiveRadius, centredStartAngle, effectiveEllipseRadiusY, letterSpacing)[0]
    drawing = partial(drawTextArtGlyphs, glyphs, angles,
        radiusX=effectiveRadius, radiusY=effectiveEllipseRadiusY, clockwise=clockwise,
        circleCenterY=circleCenterY, baselineInset=glyphHeight if clockwise else 0)
    # A deferred drawing shares this exact layout between the shadow mask and
    # foreground. Resolve fonts once, avoiding duplicated substitution messages.
    if pdf is None:
        return drawing
    drawing(pdf)
    return None


def handleTextArt(pdf, radius, bodyhtml, cwtextart, state: ConversionState, circleCenterY=0,
                  ellipseRadiusY=None, letterSpacing=0):
    if "enabled" in cwtextart[0].attrib:
        enabledAttrib = cwtextart[0].get('enabled')
        if enabledAttrib != '1':
            return None

    widthAngle = 0
    if "widthAngle" in cwtextart[0].attrib:
        widthAngleAttrib = cwtextart[0].get('widthAngle')
        widthAngle = int(widthAngleAttrib)

    direction = True
    if "direction" in cwtextart[0].attrib:
        directionAttrib = cwtextart[0].get('direction')
        direction = directionAttrib == '1'

    return draw_styled_text_on_arc(pdf, bodyhtml, radius, widthAngle, state,
                            clockwise=direction, circleCenterY=circleCenterY,
                            ellipseRadiusY=ellipseRadiusY, letterSpacing=letterSpacing)


def processTextArt(area, areaWidth, areaHeight, areaRot, pdf, transCx, transCy, body, leftPad, topPad,
                   cwtextart, context: RenderContext, state: ConversionState):
    """Render one TextArt area, including its border and arc geometry."""
    pdf.translate(transCx, transCy)
    pdf.rotate(-areaRot)
    bodyhtml = etree.tostring(body, pretty_print=True, encoding="unicode")
    _, maxfontsize = parse_html_text(bodyhtml)

    # CEWE 7 and earlier put a TextArt radius in the margin of the wrapper
    # table in the HTML text. CEWE 8.1 saves the same TextArt as a plain
    # paragraph, without retaining that margin or introducing a dedicated
    # radius attribute. Retain the legacy circular value when present.
    #
    # The CEWE 8 rectangle behaviour is an ellipse: its horizontal and
    # vertical radii scale independently with the area's width and height.
    # The top inset follows the font size rather than the shorter box side.
    # Scaling the inset with the box happened to work for the original
    # 490-unit / 18-point examples, but puts 72-point lettering above its box.
    # Keep the established radii (and therefore curvature and direction),
    # translating their centre to retain the font-sized space above the arc.
    # Both calibrations come from the same legacy 490-unit default box.
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
        else:
            baseEllipseRadiusY = baseRadius
        topOfEllipse = context.mcf_to_reportlab * (
            areaHeight * 0.5
            - maxfontsize * CEWE8_DEFAULT_TEXTART_TOP_INSET_MCF_PER_POINT)
        circleCenterY = topOfEllipse - baseEllipseRadiusY
    drawing = handleTextArt(None, radius, bodyhtml, cwtextart, state, circleCenterY, ellipseRadiusY,
        getLetterSpacing(area.find('text/textFormat'), context.mcf_to_reportlab))
    if drawing is not None:
        drawTextArtBackground(pdf, area, radius, ellipseRadiusY, circleCenterY,
            context.mcf_to_reportlab * maxfontsize * CEWE8_DEFAULT_TEXTART_TOP_INSET_MCF_PER_POINT)
        drawTextArtShadow(pdf, area, areaWidth, areaHeight, areaRot, drawing, context, state)
    for decorationTag in area.findall('decoration'):
        processDecorationBorders(decorationTag, areaHeight, areaWidth, pdf, context)
    if drawing is not None:
        drawing(pdf)
    pdf.rotate(areaRot)
    pdf.translate(-transCx, -transCy)
