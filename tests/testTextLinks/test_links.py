"""Verify automatic web links in normal CEWE text paragraphs."""

from pathlib import Path
import sys

from lxml import etree
import pymupdf
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from testutils import configureTestImportPaths

configureTestImportPaths(__file__)

from texts.links import _urlsInText, addWebLinksToPdf, getAlbumTextUrls
from texts.markup import AddAlbumText
from texts.outlines import TextEffectsParagraph


def _renderParagraph(outputFile, width, text):
    pdf = canvas.Canvas(str(outputFile))
    frame = Frame(40, 650, width, 120)
    paragraph = TextEffectsParagraph(
        AddAlbumText('', text), getSampleStyleSheet()['Normal'])
    frame.addFromList([paragraph], pdf)
    pdf.save()


def test_literalHttpUrlBecomesExternalPdfLink(tmp_path):
    outputFile = tmp_path / 'web-link.pdf'
    url = 'https://example.com/path?first=one&second=two'
    _renderParagraph(outputFile, 240, f'Visit {url}.')
    addWebLinksToPdf(outputFile, {url})

    with pymupdf.open(outputFile) as renderedPdf:
        links = renderedPdf[0].get_links()

    assert links
    assert all(link['kind'] == pymupdf.LINK_URI for link in links)
    assert {link['uri'] for link in links} == {url}


def test_wrappedHttpUrlCreatesOneExternalPdfLink(tmp_path):
    outputFile = tmp_path / 'wrapped-web-link.pdf'
    url = 'http://example.com/a/long/path/which/wraps/onto/another/line'
    _renderParagraph(outputFile, 120, url)
    addWebLinksToPdf(outputFile, {url})

    with pymupdf.open(outputFile) as renderedPdf:
        links = renderedPdf[0].get_links()

    # One logical URL must stay one annotation even when its rendering is
    # divided into several slash-separated fragments.
    assert len(links) == 1
    assert all(link['kind'] == pymupdf.LINK_URI for link in links)
    assert {link['uri'] for link in links} == {url}


def test_urlFragmentsAcrossPdfTextRunsBecomeExternalLink(tmp_path):
    outputFile = tmp_path / 'split-web-link.pdf'
    url = 'https://storysontheroad2023.blogspot.com/'
    pdf = canvas.Canvas(str(outputFile))
    font = 'Helvetica'
    fontSize = 14
    xPosition = 40
    fragments = (
        ('https:/', fontSize),
        (' ', 0.01),
        ('/', fontSize),
        (' ', 0.01),
        ('storysontheroad2023.blogspot.com/', fontSize),
        (' ', 0.01),
    )
    for text, textSize in fragments:
        pdf.setFont(font, textSize)
        pdf.drawString(xPosition, 650, text)
        xPosition += pdfmetrics.stringWidth(text, font, textSize)
    pdf.save()

    addWebLinksToPdf(outputFile, {url})

    with pymupdf.open(outputFile) as renderedPdf:
        extractedText = renderedPdf[0].get_text()
        links = renderedPdf[0].get_links()

    assert 'https:/ / storysontheroad2023.blogspot.com/' in extractedText
    assert len(links) == 1
    assert links[0]['uri'] == url


def test_albumTextEscapesUrlAndAddsInvisibleSlashBreaks():
    assert AddAlbumText('', 'See https://example.com/a?x=1&y=2, please.') == (
        'See https:/<font size="0.01"> </font>/<font size="0.01"> </font>'
        'example.com/<font size="0.01"> </font>a?x=1&amp;y=2, please.')


def test_albumTextEscapesOrdinaryTextWithoutSubstitution():
    assert AddAlbumText('', 'The sea & sky') == 'The sea &amp; sky'


def test_urlInParenthesesExcludesTheClosingParenthesis():
    assert _urlsInText('(https://www.youtube.com/watch?v=zvB0jZKRKrk)') == {
        'https://www.youtube.com/watch?v=zvB0jZKRKrk'}


def test_urlAtParagraphEndDoesNotAbsorbNextParagraphStart():
    album = etree.fromstring(
        '<album><text><![CDATA[<html><body>'
        '<p>Visit https://example.com/</p>'
        '<p>A second paragraph</p>'
        '</body></html>]]></text></album>')

    assert getAlbumTextUrls(album) == {'https://example.com/'}
