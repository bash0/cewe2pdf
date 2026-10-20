"""Measure line breaks and alignment with PDF character spacing enabled."""

from io import BytesIO
from pathlib import Path
import sys

import pytest
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from texts.outlines import TextEffectsParagraph


def makeParagraph(text, spacing):
    style = ParagraphStyle('spacing test', fontName='Helvetica', fontSize=36, leading=42,
        alignment=TA_CENTER, splitLongWords=True)
    style.letterSpacing = spacing
    return TextEffectsParagraph(text, style)


def lineTexts(paragraph):
    return [''.join(fragment.text for fragment in line.words) for line in paragraph.blPara.lines]


def test_spacedTextWrapsAndCentresUsingVisibleWidth():
    paragraph = makeParagraph('Text with shadow', 10)
    paragraph.wrap(330, 500)
    assert lineTexts(paragraph) == ['Text with', 'shadow']
    for line in paragraph.blPara.lines:
        text = ''.join(fragment.text for fragment in line.words)
        visibleWidth = stringWidth(text, 'Helvetica', 36) + (len(text) - 1) * 10
        assert line.extraSpace == pytest.approx(330 - visibleWidth)
    assert paragraph.height == 84
    paragraph.wrap(330, 500)
    assert lineTexts(paragraph) == ['Text with', 'shadow']
    paragraph.wrap(700, 500)
    assert lineTexts(paragraph) == ['Text with shadow']


def test_negativeSpacingAllowsMoreTextOnTheLine():
    paragraph = makeParagraph('Text with shadow', -1)
    width = stringWidth('Text with shadow', 'Helvetica', 36) - 5
    paragraph.wrap(width, 500)
    assert lineTexts(paragraph) == ['Text with shadow']


def test_inlineStylesAndExplicitBreaksArePreserved():
    paragraph = makeParagraph('Text <b>with</b> shadow<br/>Next <i>line</i>', 10)
    paragraph.wrap(330, 500)
    assert lineTexts(paragraph) == ['Text with', 'shadow', 'Next line']
    assert [fragment.fontName for fragment in paragraph.blPara.lines[0].words if fragment.text.strip()] == [
        'Helvetica', 'Helvetica-Bold']
    assert paragraph.blPara.lines[1].lineBreak
    pdf = Canvas(BytesIO())
    paragraph.drawOn(pdf, 20, 20)
    pdf.save()


def test_overlongWordSplitsWithoutLosingStyleOrCharacters():
    paragraph = makeParagraph('abc<b>defghij</b>', 10)
    paragraph.wrap(100, 500)
    assert ''.join(lineTexts(paragraph)) == 'abcdefghij'
    assert len(paragraph.blPara.lines) > 1
    assert all(line.extraSpace >= 0 for line in paragraph.blPara.lines)
    assert paragraph.blPara.lines[-1].words[-1].fontName == 'Helvetica-Bold'


def test_existingHyphenRemainsAnAvailableBreak():
    paragraph = makeParagraph('Text-with-shadow', 10)
    paragraph.style.embeddedHyphenation = 1
    paragraph.wrap(330, 500)
    assert lineTexts(paragraph) == ['Text-with-', 'shadow']


def test_zeroWidthSpaceAdvanceStillPreservesTheSpace():
    spacing = -stringWidth(' ', 'Helvetica', 36)
    paragraph = makeParagraph('abc def', spacing)
    paragraph.wrap(500, 500)
    assert lineTexts(paragraph) == ['abc def']


if __name__ == '__main__':
    sys.exit(pytest.main([__file__]))
