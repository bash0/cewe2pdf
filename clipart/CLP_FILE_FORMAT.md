# CLP encoding and custom resources

Copyright (c) 2020 by BarchSteel

The [original decoding investigation](../documents/history/clp-decoding-notes-2020.md)
records how the format was identified. This document owns the current decoding and
resource-authoring notes; the encoding is not encryption.

## Encoding and decoding

A CLP file begins with `a`, followed by a hexadecimal representation of SVG bytes.
Delivered files can intersperse extra lowercase letters outside the hexadecimal range.
The reader checks the prefix, discards `g` through `z`, and decodes the remaining hex.
Use [ClpFile](clpfile.py) rather than maintaining a second parser.

## Replacement colours

MCF `ClipartConfiguration` records can attach alpha to a replacement RGB colour:
`target="#000000,0"` means transparent black. The catalogue parser converts this
to SVG `rgba(0,0,0,0)` paint. Ordinary RGB replacements retain the established
six-digit colour representation.

Replacements apply to `fill`, `stroke` and gradient `stop-color` in inline styles
and SVG presentation attributes. Paint alpha combines with existing SVG opacity
and the area's decoration opacity; changing one colour does not change the whole
object's opacity. Transparent paint reveals underlying artwork or page content.
It does not cut a hole through other shapes already painted underneath it.

## Using custom clip-art files

You can use your own .clp files in the CEWE software, but it is not known if
this will work if you really order a photo book with custom clip-art.  You have
been warned.

Older CEWE versions used a catalogue file called 'cliparts_default.xml'.  That
file is no longer present in current installations: CEWE scans the resource
folders instead. For example, a Windows installation using account 5026 stores
its downloaded decorations below:

    %LOCALAPPDATA%\CEWE\hps\5026\photofun\decorations

Use a unique numeric designElementId, place an XML descriptor and the .clp
files in their own folder below that location, and restart CEWE.  The editor
can search for the numeric ID directly.  XML descriptors name files with an
'.svg' extension even when the installed files are .clp.

## Creating custom passepartouts (masks and frames)

A passepartout is a 'fading' decoration with:

* an XML descriptor;
* a mask .clp, which defines the visible shape of the photograph;
* a frame/clip .clp, which is painted above the photograph; and
* optionally, a preview .clp for CEWE's decoration picker.

For example, the descriptor has this shape:

    <decoration type="fading" designElementId="990001" id="example-frame">
      <categories><category>category-travel</category></categories>
      <fading designElementType="passepartout" file="example-mask.svg"
              keepAspectRatio="1" ratio="0.8056">
        <clipart file="example-clip.svg" designElementType="clipart" ratio="0.8056"/>
        <fotoarea height="0.57" width="0.83" x="0.085" y="0.285"/>
      </fading>
    </decoration>

There is an important geometry convention.  The frame/clip SVG canvas covers
the complete passepartout and must have the aspect ratio declared by 'ratio'.
The mask SVG canvas covers only the photograph aperture and must have the
aspect ratio implied by 'fotoarea', not the full frame.  If these canvases are
made square by default, CEWE may display the frame but cewe2pdf will not
interpret the mask and frame consistently.

### Passepartout mirroring

MCF `ClipartConfiguration` on the image selects the reflection: `mirror="x"`
reflects across the x axis (top to bottom), `mirror="y"` across the y axis
(left to right), and `mirror="both"` does both. An absent mirror setting keeps
the resource's original orientation. These are reflections in the area's local
coordinates, before its page rotation.

Reflect the frame artwork and the mask within its photograph opening, then
move that opening within the full frame. For a normalised opening `(x, y, w, h)`,
horizontal reflection changes `x` to `1 - x - w`; vertical reflection changes
`y` to `1 - y - h`. The photograph's pixels and saved cutout keep their
orientation. Reflecting the entire photo/frame composite would incorrectly
mirror the photograph. Combined shadows use the same reflected geometry.

The portable [colour-replacement fixture](../tests/testClipartColorReplacement/README.md)
includes editor-created examples for all four orientations using frame 127517.
No explicit mirroring-permission flag has been identified in the inspected
resource XML or JSON; editor control availability is not used by the converter
to override a saved MCF mirror setting.

### Encoding and installing a custom passepartout

The helper in this repository writes the simple CLP encoding:

    ClpFile.convertSVGtoCLP('example-mask.svg')

Keep the editable SVG source outside the installed resource folder, then place
the resulting .clp files beside the XML descriptor.  Validate the resource in
the CEWE editor first.  Once accepted, copy the exact resource tree into a
self-contained test fixture, for example:

    tests/hps/5026/photofun/decorations/<designElementId>/<resource-name>/

Test INI files can point 'hpsFolder' at 'tests/hps', ensuring that cewe2pdf
uses the fixture rather than a developer's installed CEWE content.
