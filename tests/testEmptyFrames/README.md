# Empty decorative photo frames

CEWE's print preview includes decorative passepartout artwork even when the
native `image` element has no filename or cutout. The photograph opening stays
clear; the empty frame does not gain the photo's configured border/shadow or
an editor placeholder. A frame XML can contain both a mask and visible clip art;
a mask alone has no visible content until a photograph is supplied.

The tests generate small SVG/XML resources and candidate PDFs locally, without
installed CEWE assets. They check transparent openings against a coloured page,
frame colour and opacity, an asymmetric mirrored/rotated example, omitted
plain/mask-only/unavailable frames, and the distinct missing-photo case.
They exercise the real image-area, resource and clip-art renderers. The synthetic
resources are regression probes; the rule comes from controlled CEWE preview
comparison, rather than treating fixture artwork as CEWE's specification.

Run directly with Python or through pytest:

```text
python tests/testEmptyFrames/test_emptyFrames.py
python -m pytest tests/testEmptyFrames -q
```
