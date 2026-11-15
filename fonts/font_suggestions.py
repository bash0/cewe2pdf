
"""Optional implementation for suggesting alternative fonts."""

import re

from .character_support import supportsCharacter


class FontSuggestionProvider:
    """Find registered font families that support a missing character."""

    MAX_SUGGESTIONS = 3

    # Words commonly used to distinguish variants of a font family.
    FAMILY_MODIFIERS = {
        'narrow',
        'condensed',
        'expanded',
        'extended',
        'black',
        'light',
        'thin',
        'rounded',
        'display',
    }

    @classmethod
    def _familyNameParts(cls, familyName):
        """Return normalised family-name parts without common modifiers."""

        words = re.findall(r'[a-z0-9]+', familyName.casefold())

        baseWords = [
            word for word in words
            if word not in cls.FAMILY_MODIFIERS
        ]

        return set(words), set(baseWords)

    @classmethod
    def _familyDistance(cls, originalFamily, candidateFamily):
        """Return a simple family-relatedness score.

        Lower scores indicate more closely related family names.
        Zero means identical base names after removing modifiers.
        """

        originalWords, originalBase = cls._familyNameParts(
            originalFamily
        )
        candidateWords, candidateBase = cls._familyNameParts(
            candidateFamily
        )

        if originalBase == candidateBase:
            return 0

        if originalBase and candidateBase:
            if originalBase.issubset(candidateBase):
                return 1
            if candidateBase.issubset(originalBase):
                return 1

        if originalWords & candidateWords:
            return 2

        return 3

    def __init__(self, fonts, fontFamilies, state):
        self.fonts = fonts
        self.fontFamilies = fontFamilies
        self.state = state

    def findAlternatives(self, character, originalFamily, bold, italic):
        """Return up to three alternative font family names.

        Families are ranked by family relatedness, then by how closely
        their available face matches the requested bold/italic style.
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
                familyDistance = self._familyDistance(
                    originalFamily, familyName
                )

                alternatives.append((
                    familyDistance,
                    bestStyleDistance,
                    familyName
                ))

        alternatives.sort(
            key=lambda item: (
                item[0],
                item[1],
                item[2].casefold()
            )
        )

        return [
            familyName
            for _, _, familyName in alternatives[:self.MAX_SUGGESTIONS]
        ]
