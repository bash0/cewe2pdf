import reportlab.lib.colors

def ReorderColorBytesMcf2Rl(colorAttrib:str):
    # Reorder for alpha value - CEWE uses #AARRGGBB, expected #RRGGBBAA
    if colorAttrib.startswith('#'):
        colorInt = int(colorAttrib.lstrip('#'), 16)
    else:
        colorInt = int(colorAttrib)
    colorRGB = colorInt & 0x00FFFFFF
    colorA = (colorInt & 0xFF000000) >> 24
    colorRGBA = (colorRGB << 8) + colorA
    color = reportlab.lib.colors.HexColor(colorRGBA, False, True)
    return color
