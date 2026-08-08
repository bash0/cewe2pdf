"""The page categories used while converting a CEWE book."""

from enum import Enum


class PageType(Enum):
    """A conversion concept; CEWE does not use these names in its MCF files."""

    Unknown = 0
    Normal = 1
    SingleSide = 2
    Cover = 3
    EmptyPage = 4
    BackInsideCover = 5

    def __str__(self):
        return self.name
