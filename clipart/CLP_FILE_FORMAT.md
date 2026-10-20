# The CLP file format (*.clp) used in CEWE FOTO

Copyright (c) 2020 by BarchSteel

The CEWE software uses its own format for the clipart, also called decorations. They can easily be identified by looking at the file names in the program folder under Resources\photofun\decorations. 

Let's look at a presumably simple file: `\Resources\photofun\decorations\line_single_black.clp`

The file contents is pure text, but it does to look like any known file format. It seems to be some sort of encoding and/or scrambling. If we look carefully, we see that for the encoding of the data only numbers and lower-case letters: 0-9, a-z (0x30-0x39 und 0x61-0x7A) are used. The total number of code points is 
If we count the 10 characters for numbers plus 26 for the Arabic letters, we only get 36 unique code-points for the encoded text. That is a 36/256 = 14% coding efficiency, which is strangle low.
 
If look around a little bit in this folder, we find the file 'cliparts_default.xml' which contains a line:

```xml
<clipart file="line_single_black.svg" designElementId="63457" designElementType="clipart"/>
```


It looks like the .clp file is somehow related to a .svg fie.  
  
Let's look at one of the included files
"Resources\photofun\categories\SVGTemplates\gifts\002-M-SF\002-M-SF1.svg"
It starts with the following text:

```text
<?xml version="1.0" encoding
```

If we look at the same file with a Hex-Editor, we see these bytes:

```text
3C 3F 78 6D 6C 20 76 65 72 73 69 6F 6E 3D 22 31 2E 30 22
```


Now let's look again at the line_single_black.clp:
The file starts with this:

```text
a3c3f786d6qc2076v65727369x6hf6e3d
```

We immediately see similarities, if we organize the text with proper spacing: 

```text
a 3C 3F 78 6D 6qC 20 76 v65 72 73 69 x6hF 6E 3D
```

Many of the bytes appear identically in the .svg file.
The sequence '3C 3F 78 6D' is clearly `<?xm` which is the plain-text start of the svg-file. The first character 'a' is maybe some header for the .clp-file and is not needed.
And if we look at 6qC, it almost looks like 6C which would the next character to complete `<?xml`, so the 'q' is somewhat extra in there. The same goes for 'v','x', and 'h'. If just remove them, we end up with a hexadecimal representation of the start of a valid file.

After looking around at a few other .clp files we can come up with these rules for decoding a .clp to a .svg file:

## Decoding

1. Discard the first character. It is always an 'a'. This is some sort of header.
2. Discard all characters except 0-9 and a-f. This will result in a valid hexadecimal string.
3. Decode the hexadecimal string to its binary representation.

## Using custom clip-art files
You can use your own .clp files in the CEWE software, but it is not known if
this will work if you really order a photo book with custom clip-art.  You have
been warned.

Older CEWE versions used a catalogue file called 'cliparts_default.xml'.  That
file is no longer present in current installations: CEWE scans the resource
folders instead.  Downloaded content is normally installed below:

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
