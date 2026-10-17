"""Verify automatic web links in normal CEWE text paragraphs."""

from pathlib import Path
import sys

import pymupdf
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from testutils import configureTestImportPaths

configureTestImportPaths(__file__)

from texts.links import addWebLinksToPdf
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


def test_wrappedHttpUrlCreatesExternalPdfLinks(tmp_path):
    outputFile = tmp_path / 'wrapped-web-link.pdf'
    url = 'http://example.com/a/long/path/which/wraps/onto/another/line'
    _renderParagraph(outputFile, 120, url)
    addWebLinksToPdf(outputFile, {url})

    with pymupdf.open(outputFile) as renderedPdf:
        links = renderedPdf[0].get_links()

    assert len(links) > 1
    assert all(link['kind'] == pymupdf.LINK_URI for link in links)
    assert {link['uri'] for link in links} == {url}


def test_albumTextEscapesUrlAndAddsInvisibleSlashBreaks():
    assert AddAlbumText('', 'See https://example.com/a?x=1&y=2, please.') == (
        'See https:/<font size="0.01"> </font>/<font size="0.01"> </font>'
        'example.com/<font size="0.01"> </font>a?x=1&amp;y=2, please.')


def test_albumTextEscapesOrdinaryTextWithoutSubstitution():
    assert AddAlbumText('', 'The sea & sky') == 'The sea &amp; sky'
