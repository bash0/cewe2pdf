"""Render the supported CEWE calendar fixtures and compare approved results."""

from datetime import datetime
from pathlib import Path
import sys

import pikepdf
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from compare_pdf import ComparePDF, ShowDiffsStyle  # type: ignore
from cewe2pdf import convertMcf
from testutils import getLatestResultFile


TEST_DIRECTORY = Path(__file__).parent


def buildAndCompareCalendar(fixtureName, pageDimensions, caplog):
    """Render one fixture, retaining its PDF for manual or pixel comparison."""
    sourceMcf = TEST_DIRECTORY / fixtureName / f'{fixtureName}.mcf'
    date = datetime.today().strftime('%Y%m%d')
    outputPdf = sourceMcf.with_name(f'{fixtureName}.mcf.{date}.pdf')
    approvedPdf = getLatestResultFile(str(Path(TEST_DIRECTORY.name) / fixtureName),
                                      f'{fixtureName}.mcf.*.pdf')

    if outputPdf.exists():
        outputPdf.unlink()

    assert convertMcf(str(sourceMcf), keepDoublePages=False,
                      outputFileName=str(outputPdf))

    with pikepdf.Pdf.open(outputPdf) as renderedPdf:
        assert len(renderedPdf.pages) == 13
        firstPage = renderedPdf.pages[0]
        pageBox = firstPage.mediabox
        assert round(float(pageBox[2])) == pageDimensions[0]
        assert round(float(pageBox[3])) == pageDimensions[1]

    assert not any('Unsupported calendar layout' in record.message
                   for record in caplog.records)

    if approvedPdf is None:
        print(f'No approved PDF result for {fixtureName} to compare with')
        return

    print(f'Compare {outputPdf} with {approvedPdf}')
    comparison = ComparePDF([str(outputPdf), approvedPdf],
                            ShowDiffsStyle.Nothing)
    try:
        assert comparison.compare(), 'Pixel comparison failed'
    finally:
        comparison.cleanup()


@pytest.mark.parametrize(('fixtureName', 'pageDimensions'), [
    ('a4p', (595, 842)),
    ('a4l', (842, 595)),
])
def test_calendarRendersIndependentPages(caplog, fixtureName, pageDimensions):
    """Each fixture produces its cover plus twelve independent month pages."""
    buildAndCompareCalendar(fixtureName, pageDimensions, caplog)


if __name__ == '__main__':
    import pytest
    raise SystemExit(pytest.main([__file__, '-s']))
