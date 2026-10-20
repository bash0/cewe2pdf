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

The helper in this repository writes the simple CLP encoding:

    ClpFile.convertSVGtoCLP('example-mask.svg')

Keep the editable SVG source outside the installed resource folder, then place
the resulting .clp files beside the XML descriptor.  Validate the resource in
the CEWE editor first.  Once accepted, copy the exact resource tree into a
self-contained test fixture, for example:

    tests/hps/5026/photofun/decorations/<designElementId>/<resource-name>/

Test INI files can point 'hpsFolder' at 'tests/hps', ensuring that cewe2pdf
uses the fixture rather than a developer's installed CEWE content.
