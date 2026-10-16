"""Exercise command-line page-selection semantics through PDF rendering."""

from pathlib import Path
import sys
from unittest.mock import patch

from pikepdf import Pdf
import pymupdf


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from cewe2pdf import convertMcf
from albumConversionSession import AlbumConversionSession
from ceweInfo import PdfProductStyle
from infrastructure.extraLoggers import mustsee
from pageLabels import PdfPageLabel, pageLabelDefinitions
from pageSelection import PageSelection


FIXTURE = PROJECT_ROOT / 'tests' / 'testEmptyPageOne' / 'test_emptyPageOne.mcf'


def test_doublePageSelectionProducesCompletePhysicalSpreads(tmp_path):
    """Cover, opening, one ordinary, and closing spread make four PDF pages."""
    outputFile = tmp_path / 'selected-spreads.pdf'
    selection = PageSelection(frozenset([1, 3, 30]), include_cover=True)

    assert convertMcf(str(FIXTURE), True, selection,
                      outputFileName=str(outputFile))

    with Pdf.open(outputFile) as pdf:
        assert len(pdf.pages) == 4

    with pymupdf.open(outputFile) as pdf:
        assert pdf.get_page_labels() == [
            {'startpage': 0, 'prefix': 'Cover', 'firstpagenum': 1},
            {'startpage': 1, 'prefix': '', 'style': 'D', 'firstpagenum': 1},
            {'startpage': 2, 'prefix': '2-3', 'firstpagenum': 1},
            {'startpage': 3, 'prefix': '', 'style': 'D', 'firstpagenum': 30},
        ]


def test_pageLabelDefinitionsRestartAtGapsAndSpreadLabels():
    """Selections and retained spreads cannot use one continuous number run."""
    labels = [
        PdfPageLabel(prefix='Cover'),
        PdfPageLabel(style='D', first_page_number=1),
        PdfPageLabel(style='D', first_page_number=4),
        PdfPageLabel(prefix='5-6'),
    ]

    assert pageLabelDefinitions(labels) == [
        {'startpage': 0, 'prefix': 'Cover', 'style': '', 'firstpagenum': 1},
        {'startpage': 1, 'prefix': '', 'style': 'D', 'firstpagenum': 1},
        {'startpage': 2, 'prefix': '', 'style': 'D', 'firstpagenum': 4},
        {'startpage': 3, 'prefix': '5-6', 'style': '', 'firstpagenum': 1},
    ]


def test_partialPageSelectionIsReportedBeforeRendering():
    session = object.__new__(AlbumConversionSession)
    session.page_numbers = PageSelection(frozenset([4, 5, 8]))

    with patch.object(mustsee, 'info') as info:
        session._reportPartialPageSelection(PdfProductStyle.AlbumSingleSide, 32)

    info.assert_called_once_with('Processing selected pages: 4-5, 8.')
