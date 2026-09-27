"""Exercise command-line page-selection semantics through PDF rendering."""

from pathlib import Path
import sys
from unittest.mock import patch

from pikepdf import Pdf


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from cewe2pdf import convertMcf
from albumConversionSession import AlbumConversionSession
from ceweInfo import PdfProductStyle
from infrastructure.extraLoggers import mustsee
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


def test_partialPageSelectionIsReportedBeforeRendering():
    session = object.__new__(AlbumConversionSession)
    session.page_numbers = PageSelection(frozenset([4, 5, 8]))

    with patch.object(mustsee, 'info') as info:
        session._reportPartialPageSelection(PdfProductStyle.AlbumSingleSide, 32)

    info.assert_called_once_with('Processing selected pages: 4-5, 8.')
