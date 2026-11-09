"""Qt paragraph formatting must reach spans with colour-only overrides."""

from pathlib import Path
import sys
from unittest.mock import patch

import pytest
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conversionState import ConversionState
from texts.markup import CollectFontInfo


def test_span_inherits_paragraph_overrides_and_keeps_own_colour():
    body = etree.fromstring('''<body style="font-family:Georgia; font-size:26pt; font-weight:700; font-style:normal;">
      <p style="font-family:Helvetica; font-size:16pt; font-weight:400; font-style:italic; color:#123456;">
        <span style="color:#475569;">Subtitle</span>
      </p>
      <p><span style="color:#1e293b;">Next heading</span></p>
    </body>''')
    with patch('texts.markup.getAvailableFont', side_effect=lambda family, *_: family):
        font, size, weight, style = CollectFontInfo(
            body[0][0], None, [], 'Georgia', 26, 700, 1.0, ConversionState())
        assert (font, size, weight) == ('Helvetica', 16, 400)
        assert style['font-style'] == 'italic'
        assert style['color'] == '#475569'
        font, size, weight, style = CollectFontInfo(
            body[1][0], None, [], 'Georgia', 26, 700, 1.0, ConversionState())
        assert (font, size, weight) == ('Georgia', 26, 700)
        assert style['font-style'] == 'normal'


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__]))
