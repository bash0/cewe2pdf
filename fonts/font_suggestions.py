
"""Optional implementation for suggesting alternative fonts."""

from .character_support import supportsCharacter


class FontSuggestionProvider:
    """Find registered font families that support a missing character."""

    MAX_SUGGESTIONS = 3

    def __init__(self, fonts, fontFamilies, state):
        self.fonts = fonts
        self.fontFamilies = fontFamilies
        self.state = state

    def findAlternatives(self, character, originalFamily, bold, italic):
        """Return up to three alternative font family names.

        Families are ranked by how closely their available face matches
        the requested bold/italic style.
        """

        requestedStyle = (int(bool(bold)), int(bool(italic)))

        # Each style is represented by its bold/italic characteristics.
        styleCharacteristics = {
            'normal': (0, 0),
            'bold': (1, 0),
            'italic': (0, 1),
            'boldItalic': (1, 1)
        }

        originalFamilyKey = originalFamily.casefold()
        alternatives = []

        for familyName, familyFaces in self.fontFamilies.items():
            if familyName.casefold() == originalFamilyKey:
                continue

            bestStyleDistance = None

            for style, fontFace in familyFaces.items():
                if style not in styleCharacteristics:
                    continue

                fontFile = self.fonts.get(fontFace)
                if fontFile is None:
                    continue

                if supportsCharacter(
                        character, fontFile, self.state) is not True:
                    continue

                faceStyle = styleCharacteristics[style]
                styleDistance = (
                    abs(requestedStyle[0] - faceStyle[0])
                    + abs(requestedStyle[1] - faceStyle[1])
                )

                if (bestStyleDistance is None
                        or styleDistance < bestStyleDistance):
                    bestStyleDistance = styleDistance

            if bestStyleDistance is not None:
                alternatives.append((bestStyleDistance, familyName))

        alternatives.sort(
            key=lambda item: (item[0], item[1].casefold())
        )

        return [
            familyName
            for _, familyName in alternatives[:self.MAX_SUGGESTIONS]
        ]
