"""Warn about changed CEWE stacking conventions without rearranging artwork."""

import logging
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch
from xml.etree import ElementTree

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from ceweInfo import PdfProductStyle
from conversionState import ConversionState
from pageElements import _warnIfAreaOrderDiffers, processElements
from pageTypes import PageProcessingType


def pageWithZpositions(values):
    page = ElementTree.Element('page', pagenr='2', type='normalpage')
    for value in values:
        area = ElementTree.SubElement(page, 'area', areatype='clipartarea')
        position = ElementTree.SubElement(area, 'position', left='120', top='10',
            width='20', height='20', rotation='0')
        if value is not None:
            position.set('zposition', value)
    return page


def test_equal_and_unavailable_zpositions_do_not_warn(caplog):
    """Ties are valid and optional malformed metadata must not prevent drawing."""
    page = pageWithZpositions([None, 'invalid', 'nan', 'inf', '1', '1', '2,5', '10'])
    ElementTree.SubElement(page, 'area')  # No position available to this diagnostic.
    with caplog.at_level(logging.WARNING):
        _warnIfAreaOrderDiffers(page, 3)
    assert not caplog.records


def test_first_decrease_warns_with_page_context(caplog):
    page = pageWithZpositions(['10', '2', '1'])
    with caplog.at_level(logging.WARNING):
        _warnIfAreaOrderDiffers(page, 3)
    assert len(caplog.records) == 1
    assert 'zposition' in caplog.text
    assert 'Page 3' in caplog.text
    assert 'MCF pagenr 2' in caplog.text


@pytest.mark.parametrize('style', [
    PdfProductStyle.AlbumSingleSide,
    PdfProductStyle.AlbumDoubleSide,
])
def test_odd_page_warns_and_keeps_xml_drawing_order(style, caplog):
    """Check the resolved source page, rather than its empty odd-page record."""
    book = ElementTree.Element('fotobook')
    source = pageWithZpositions(['10', '2'])
    for identifier, area in enumerate(source.findall('area'), start=101):
        ElementTree.SubElement(area, 'clipart', designElementId=str(identifier))
    book.append(source)
    oddPage = ElementTree.SubElement(book, 'page', pagenr='3', type='normalpage')
    before = ElementTree.tostring(book)
    with caplog.at_level(logging.WARNING), patch('pageElements.processAreaClipartTag') as draw:
        processElements({}, book, '', style, '', True, oddPage, 3,
            PageProcessingType.RegularPage, Mock(), 100, 100, False,
            SimpleNamespace(mcf_to_reportlab=1), ConversionState(), Mock(),
            {}, {}, {}, {}, ())
    assert len(caplog.records) == 1
    assert [invocation.args[0].get('designElementId')
        for invocation in draw.call_args_list] == ['101', '102']
    assert ElementTree.tostring(book) == before


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q', *sys.argv[1:]]))
