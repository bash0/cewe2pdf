"""The page categories used while converting a CEWE book."""

from enum import Enum


class PageProcessingType(Enum):
    """An internal processing role; CEWE does not use these names in MCF files."""

    Undetermined = 0
    RegularPage = 1
    FrontInsideCoverBackground = 2
    Cover = 3
    FrontInsideCover = 4
    BackInsideCover = 5

    def __str__(self):
        return self.name
