"""Unit tests for the local compare_pdf helper's code-facing API."""

import logging
import sys
from pathlib import Path

import numpy as np
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPARE_PDF_ROOT = PROJECT_ROOT / 'tests' / 'compare-pdf'
sys.path.insert(0, str(COMPARE_PDF_ROOT))

from compare_pdf import ComparePDF, PageTolerance, ShowDiffsStyle


def comparison_with_tolerances(page_tolerances=None):
    """Construct the small part of ComparePDF needed for image-array tests."""
    comparison = ComparePDF.__new__(ComparePDF)
    comparison.pdf_paths = ['new.pdf', 'approved.pdf']
    comparison.pdf_documents = []
    comparison.showdiffs = ShowDiffsStyle.Nothing
    comparison.page_tolerances = page_tolerances or {}
    comparison.logger = logging.getLogger('cewe2pdf.test')
    return comparison


def one_pixel_difference():
    approved = np.zeros((2, 2, 3), dtype=np.uint8)
    new = approved.copy()
    new[0, 0] = (1, 2, 3)
    return new, approved


def test_comparison_is_exact_without_a_page_tolerance(caplog):
    new, approved = one_pixel_difference()

    with caplog.at_level(logging.INFO, logger='cewe2pdf.test'):
        assert not comparison_with_tolerances()._compare_images([new, approved], 1)

    assert '1 px' in caplog.text
    assert 'maximum per-channel difference 3' in caplog.text
    assert 'maximum combined RGB difference 6' in caplog.text


def test_page_tolerance_requires_every_limit(caplog):
    new, approved = one_pixel_difference()
    tolerance = PageTolerance(
        max_different_pixels=1,
        max_channel_difference=3,
        max_combined_rgb_difference=6,
        reason='A deliberately small test allowance.',
    )

    with caplog.at_level(logging.INFO, logger='cewe2pdf.test'):
        assert comparison_with_tolerances({1: tolerance})._compare_images([new, approved], 1)

    assert 'accepted within tolerance' in caplog.text
    assert tolerance.reason in caplog.text


def test_page_tolerance_rejects_a_difference_above_any_limit():
    new, approved = one_pixel_difference()
    tolerance = PageTolerance(
        max_different_pixels=1,
        max_channel_difference=2,
        max_combined_rgb_difference=6,
        reason='This limit is intentionally too small.',
    )

    assert not comparison_with_tolerances({1: tolerance})._compare_images([new, approved], 1)


@pytest.mark.parametrize(
    'kwargs',
    [
        {'max_different_pixels': -1},
        {'max_channel_difference': -1},
        {'max_combined_rgb_difference': -1},
        {'reason': ''},
    ],
)
def test_page_tolerance_validates_its_arguments(kwargs):
    values = {
        'max_different_pixels': 0,
        'max_channel_difference': 0,
        'max_combined_rgb_difference': 0,
        'reason': 'A reason.',
    }
    values.update(kwargs)

    with pytest.raises(ValueError):
        PageTolerance(**values)
