import logging
import os

from fontTools import ttLib
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from ceweInfo import CeweInfo
from extraLoggers import mustsee, configlogger
from otf import getTtfsFromOtfs
from pathutils import localfont_dir, findFileInDirs, findFilesInDir


def findAndRegisterFonts(configSection, appDataDir, albumBaseFolder, cewe_folder): # pylint: disable=too-many-statements
    ttfFiles = []
    fontDirs = []
    fontsToRegister = {}
    familiesToRegister = {}

    if cewe_folder:
        fontDirs.append(CeweInfo.getCeweFontsFolder(cewe_folder))

    # if a user has installed fonts locally on his machine, then we need to look there as well
    localFontFolder = localfont_dir()
    if os.path.exists(localFontFolder):
        fontDirs.append(str(localFontFolder))

    try:
        searchlocations = (albumBaseFolder, os.path.curdir, os.path.dirname(os.path.realpath(__file__)))
        configFontFileName = findFileInDirs('additional_fonts.txt', searchlocations)
        mustsee.info(f'Using additional font definitions from: {configFontFileName}')
        with open(configFontFileName, 'r') as fp: # this works on all relevant platforms so pylint: disable=unspecified-encoding
            for line in fp:
                line = line.strip()
                if not line:
                    continue # ignore empty lines
                if line.startswith("#"):
                    continue # ignore comments
                if line.find(" = ") != -1:
                    # Old "font name = /path/to/file" format
                    p = line.split(" = ", 1)
                    path = os.path.expandvars(p[1])
                else:
                    path = os.path.expandvars(line)

                if not os.path.exists(path):
                    configlogger.error(f'Custom additional font file does not exist: {path}')
                    continue
                if os.path.isdir(path):
                    fontDirs.append(path)
                else:
                    ttfFiles.append(path)
            fp.close()
    except ValueError: # noqa: E722. This is a locally thrown exception
        mustsee.info(f'No additional_fonts.txt found in {searchlocations}')
    except: # noqa: E722 # pylint: disable=bare-except
        configlogger.error('Cannot read additional fonts from {configFontFileName}')
        configlogger.error('Content example:')
        configlogger.error('/tmp/vera.ttf')

    addTtfFilesFromFontdirs(ttfFiles, fontDirs, appDataDir)

    buildFontsToRegisterFromTtfFiles(ttfFiles, fontsToRegister, familiesToRegister)

    logging.info(f"Registering {len(fontsToRegister)} fonts")
    # We need to loop over the keys, not the list iterator, so we can delete keys from the list in the loop
    for curFontName in list(fontsToRegister):
        try:
            pdfmetrics.registerFont(TTFont(curFontName, fontsToRegister[curFontName]))
            configlogger.info(f"Registered '{curFontName}' from '{fontsToRegister[curFontName]}'")
        except: # noqa: E722 # pylint: disable=bare-except
            configlogger.error(f"Failed to register font '{curFontName}' (from {fontsToRegister[curFontName]})")
            del fontsToRegister[curFontName]    # remove this item from the font list, so it won't be used later and cause problems.

    # The reportlab manual says:
    #  Before using the TT Fonts in Platypus we should add a mapping from the family name to the individual font
    #  names that describe the behaviour under the <b> and <i> attributes.
    #  from reportlab.pdfbase.pdfmetrics import registerFontFamily
    #  registerFontFamily('Vera',normal='Vera',bold='VeraBd',italic='VeraIt',boldItalic='VeraBI')
    # So now we've registered the fonts, making them known to the pdf system. Now for the font families...
    #  FIRST we register families explicitly defined in the .ini configuration, because they are
    #  potentially providing correct definitions for families which are not correctly identified by
    #  the normal heuristic family setup above  - the "fixed" FranklinGothic being a good example:
    #   fontFamilies =
    #      FranklinGothic,FranklinGothic,FranklinGothic Medium,Franklin Gothic Book Italic,FranklinGothic Medium Italic
    explicitlyRegisteredFamilyNames = getExplicitlyRegisteredFamilyNames(configSection, fontsToRegister)

    # Now we can register the families we have "observed" and built up as we read the font files,
    #  but ignoring any family name which was registered explicitly from configuration
    registerFontFamilies(familiesToRegister, explicitlyRegisteredFamilyNames)

    loadMissingFontSubstitutions(configSection, fontsToRegister)

    logging.info("Ended font registration")

    return fontsToRegister # pass back a list of all the available fonts


def buildFontsToRegisterFromTtfFiles(ttfFiles, fontList, fontFamilyList):
    if len(ttfFiles) > 0:
        redefinedCount = 0
        ttfFiles = list(dict.fromkeys(ttfFiles)) # remove duplicates
        for ttfFile in ttfFiles:
            font = ttLib.TTFont(ttfFile)

            # See https://learn.microsoft.com/en-us/typography/opentype/spec/name#name-ids
            # The dp4 fontviewer shows the contents of ttf files https://us.fontviewer.de/
            fontFamily = font['name'].getDebugName(1) # eg Arial
            fontSubFamily = font['name'].getDebugName(2) # eg Regular, Bold, Bold Italic
            fontFullName = font['name'].getDebugName(4) # eg usually a combo of 1 and 2
            if fontFamily is None:
                configlogger.warning(f'Could not get family (name) of font: {ttfFile}')
                continue
            if fontSubFamily is None:
                configlogger.warning(f'Could not get subfamily of font: {ttfFile}')
                continue
            if fontFullName is None:
                configlogger.warning(f'Could not get full font name: {ttfFile}')
                continue

            # Cewe offers the users "fonts" which really name a "font family" (so that you can then use
            # the B or I buttons to get bold or italic.)  The mcf file contains those (family) names.
            # So we're going to register (with pdfmetrics):
            #   (1) a lookup between the cewe font (family) name and up to four fontNames (for R,B,I,BI)
            #   (2) a lookup between these four fontNames and the ttf file implementing the font
            # Observe that these fontNames are used only internally in this code, to create the one-to-four
            #  connection between the cewe font (family) name and the ttf files. The names used to be created
            #  in code, but now we just use the official full font name
            # EXCEPT that there's a special case ... the three FranklinGothic ttf files from CEWE are badly defined
            #  because the fontFullName is identical for all three of them, namely FranklinGothic, rather than
            #  including the subfamily names which are Regular, Medium, Medium Italic
            if (fontFullName == fontFamily) and fontSubFamily not in ('Regular', 'Light', 'Roman'):
                # We have a non-"normal" subfamily where the full font name which is not different from the family name.
                # That may be a slightly dubious font definition, and it seems to cause us trouble. First, warn about it,
                # in case people have actually used these rather "special" fonts:
                configlogger.warning(f"fontFullName == fontFamily '{fontFullName}' for a non-regular subfamily '{fontSubFamily}'. A bit strange!")
                # Some of the special cases really are special and probably OK, but CEWE FranklinGothic
                # is a case in point where I think the definition is just wrong, and we can successfully
                # fix it, in combination with a manual FontFamilies defintion in the .ini file:
                if fontFamily == "FranklinGothic":
                    fontFullName = fontFamily + " " + fontSubFamily
                    configlogger.warning(f"  constructed fontFullName '{fontFullName}' for '{fontFamily}' '{fontSubFamily}'")

            if fontSubFamily == "Regular" and fontFullName == fontFamily + " Regular":
                configlogger.warning(f"Revised regular fontFullName '{fontFullName}' to '{fontFamily}'")
                fontFullName = fontFamily

            if fontFullName in fontList:
                configlogger.info(f"'{fontFullName}' redefined: the first definition '{fontList[fontFullName]}' is preferred over '{ttfFile}'")
                redefinedCount = redefinedCount + 1
            else:
                fontList[fontFullName] = ttfFile

            # first time we see a family we create an empty entry from that family to the R,B,I,BI font names
            if fontFamily not in fontFamilyList:
                fontFamilyList[fontFamily] = {
                    "normal": None,
                    "bold": None,
                    "italic": None,
                    "boldItalic": None
                }

            # then try some heuristics to guess which fonts in a potentially large font family can be
            # used to represent the more limited set of four fonts offered by cewe. We should perhaps
            # prefer a particular name (eg in case both Light and Regular exist) but for now the last
            # font in each weight wins
            if fontSubFamily in {"Regular", "Light", "Roman"}:
                fontFamilyList[fontFamily]["normal"] = fontFullName
            elif fontSubFamily in {"Bold", "Medium", "Heavy", "Xbold", "Demibold", "Demibold Roman"}:
                fontFamilyList[fontFamily]["bold"] = fontFullName
            elif fontSubFamily in {"Italic", "Light Italic", "Oblique"}:
                fontFamilyList[fontFamily]["italic"] = fontFullName
            elif fontSubFamily in {"Bold Italic", "Medium Italic", "BoldItalic", "Heavy Italic", "Bold Oblique", "Demibold Italic"}:
                fontFamilyList[fontFamily]["boldItalic"] = fontFullName
            else:
                configlogger.warning(f"Unhandled fontSubFamily '{fontSubFamily}', using fontFamily '{fontFamily}' as the regular font name")
                fontFamilyList[fontFamily]["normal"] = fontFamily
                fontList[fontFamily] = ttfFile

        if redefinedCount > 0:
            configlogger.warning(f"Multiple ttf files found for {redefinedCount} fonts, increase the cewe2pdf.config log level to see redefinitions")

def verifyFontNameConventions(m_familyname, normal=None, bold=None, italic=None, boldItalic=None):
    # It seems usual that the bold, italic and boldItalic fonts are named with the normal name
    # plus the words "bold", "italic", "bold italic". Let's verify that, because TextArt relies
    # on it! There are few exceptions, and they're probably not likely to occur in practice
    nonConventional = False
    if bold is not None:
        if bold.lower() != f"{normal.lower()} bold":
            nonConventional = True
    if italic is not None:
        if italic.lower() != f"{normal.lower()} italic":
            nonConventional = True
    if boldItalic is not None:
        if boldItalic.lower() != f"{normal.lower()} bold italic":
            nonConventional = True
    if nonConventional:
        configlogger.info(f"Unconventional font names in family '{m_familyname}': n='{normal}' b='{bold}' i='{italic}' bi='{boldItalic}'")

def getExplicitlyRegisteredFamilyNames(defaultConfigSection, fontList):
    if defaultConfigSection is None:
        return []
    explicitFamilyNames = []
    ff = defaultConfigSection.get('FontFamilies', '').splitlines()  # newline separated list of folders
    explicitFontFamilies = filter(lambda bg: (len(bg) != 0), ff)
    for explicitFontFamily in explicitFontFamilies:
        members = explicitFontFamily.split(",")
        if len(members) == 5:
            m_familyname = members[0].strip()
            m_n = members[1].strip()
            m_b = members[2].strip()
            m_i = members[3].strip()
            m_bi = members[4].strip()
            # using font names here which are not already registered as fonts will cause crashes
            # later, so check for that before registering the family
            fontsOk = True
            msg = ""
            for fontToCheck in (m_n, m_b, m_i, m_bi):
                if fontToCheck not in fontList:
                    if fontsOk:
                        msg = f"Configured font family {m_familyname} ignored because of unregistered fonts: "
                    msg += f"{fontToCheck} "
                    fontsOk = False
            if not fontsOk:
                configlogger.error(msg)
            else:
                pdfmetrics.registerFontFamily(m_familyname, normal=m_n, bold=m_b, italic=m_i, boldItalic=m_bi)
                explicitFamilyNames.append(m_familyname)
                configlogger.warning(f"Using configured font family '{m_familyname}': '{m_n}','{m_b}','{m_i}','{m_bi}'")
                verifyFontNameConventions(m_familyname, normal=m_n, bold=m_b, italic=m_i, boldItalic=m_bi)
        else:
            configlogger.error(f'Invalid FontFamilies line ignored (!= 5 comma-separated strings): {explicitFontFamily}')
    return explicitFamilyNames


def addTtfFilesFromFontdirs(ttfFiles, fontDirs, appDataDir):
    if len(fontDirs) > 0:
        mustsee.info(f'Scanning for ttf/otf files in {str(fontDirs)}')
        for fontDir in fontDirs:
            # this is what we really want to do to find extra ttf files:
            #   ttfextras = glob.glob(os.path.join(fontDir, '*.ttf'))
            # but case sensitivity is a problem which will kick in - at least - when executing
            # a Linux subsystem on a Windows machine and file system. So we use a case insensitive
            # alternative [until Python 3.12 when glob itself offers case insensitivity] Ref the
            # discussion at https://stackoverflow.com/questions/8151300/ignore-case-in-glob-on-linux
            ttfextras = findFilesInDir(fontDir, '*.ttf', walk_structure=False)
            # walk_structure set to True looks like a good idea, so we could keep our own
            # downloaded fonts, eg from Google Fonts, in separate folders. But it turns out
            # that Windows really assumes that searches are restricted to a single folder,
            # so that deleted fonts may be moved to a "Deleted" sub folder.
            ttfFiles.extend(sorted(ttfextras))

            # CEWE deliver some fonts as otf, which we cannot use witout first converting to ttf
            #   see https://github.com/bash0/cewe2pdf/issues/133
            otfFiles = findFilesInDir(fontDir, '*.otf')
            if len(otfFiles) > 0:
                ttfsFromOtfs = getTtfsFromOtfs(otfFiles,appDataDir)
                ttfFiles.extend(sorted(ttfsFromOtfs))


def registerFontFamilies(fontFamilies, explicitlyRegisteredFamilyNames):
    if len(fontFamilies) > 0:
        for familyName, fontFamily in fontFamilies.items():
            if fontFamily['normal'] is None:
                if fontFamily['italic'] is not None:
                    alternateNormal = 'italic'
                elif fontFamily['bold'] is not None:
                    alternateNormal = 'bold'
                elif fontFamily['boldItalic'] is not None:
                    alternateNormal = 'boldItalic'
                else:
                    alternateNormal = ''
                    configlogger.error(f"Font family '{familyName}' has no normal font and no alternate. The font will not be available")
                if alternateNormal:
                    fontFamily['normal'] = fontFamily[alternateNormal]
                    configlogger.warning(f"Font family '{familyName}' has no normal font, chosen {fontFamily['normal']} from {alternateNormal}")
            for key, value in dict(fontFamily).items(): # looping through normal, bold, italic, bold italic
                if value is None:
                    del fontFamily[key]
            if familyName not in explicitlyRegisteredFamilyNames:
                pdfmetrics.registerFontFamily(familyName, **fontFamily)
                configlogger.info(f"Registered fontfamily '{familyName}': {fontFamily}")
                verifyFontNameConventions(familyName, **fontFamily)
            else:
                configlogger.info(f"Font family '{familyName}' was already registered from configuration file")


# if a font is missing when we need it then we'll try to find an
# alternative from this table
missingFontSubstitutions = {
    "Arial": "Liberation Sans Narrow",
    "Arial Narrow": "Liberation Sans Narrow",
    "Arial Rounded MT Bold": "Poppins",
    "Bodoni": "EB Garamond",
    "Calibri": "Liberation Sans Narrow",
    "CalligraphScript": "Dancing Script",
    "CEWE Head": "Liberation Sans",
    "FranklinGothic": "Liberation Sans Narrow",
    "Pecita": "Dancing Script",
    "Stafford": "Liberation Sans Narrow",
    "Balloon Caps": "Liberation Sans Narrow",
    # Crafty Girls
    # Function
    # Harlow Solid Italic
    # Segoe UI Symbol
    }

def loadMissingFontSubstitutions(configSection, availableFonts):
    global missingFontSubstitutions  # pylint: disable=global-statement
    if configSection is None:
        return
    # build the known missing font substitutions table
    fs = configSection.get('missingFontSubstitutions', '').splitlines()  # newline separated list of fontname: fontname pairs
    ffs = list(filter(lambda fnp: (len(fnp) != 0), fs)) # filter out empty entries
    f2fs = tuple(map(lambda fnp: os.path.expandvars(fnp), ffs)) # expand environment vars pylint: disable=unnecessary-lambda
    for fnp in f2fs:
        definition = fnp.split(':')
        if len(definition) == 2:
            originalfont = definition[0].strip()
            newfont = definition[1].strip()
            if originalfont == '' and newfont == '':
                missingFontSubstitutions = {}
            else:
                if originalfont != '' and newfont != '':
                    if newfont not in availableFonts:
                        configlogger.error(f"Font substitution with '{newfont}' ignored, that font has not been found")
                        continue
                    missingFontSubstitutions[originalfont] = newfont
                else:
                    configlogger.error(f"Invalid font substitution '{originalfont}' : '{newfont}' ignored")
                    continue


def getMissingFontSubstitute(family):
    if family in missingFontSubstitutions: # IMO this is clearest so pylint: disable=consider-using-get
        bodyfont = missingFontSubstitutions[family]
    else:
        bodyfont = 'Helvetica'
        # reportlabs actually offers Helvetica, which is a bit strange since it is a proprietary font.
    return bodyfont
