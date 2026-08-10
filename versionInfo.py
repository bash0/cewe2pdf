"""Program version and optional Git build identification."""

import subprocess
from pathlib import Path
from extraLoggers import mustsee


# Change this deliberately when a change to bash0/cewe2pdf master warrants a
# new user-facing version.  The successful-master GitHub workflow adds the
# automatic build number to its tag.
PROGRAM_VERSION = "1.0"


def getGitBuildIdentification():
    """Return the nearest cewe2pdf build tag and revision, if Git is available."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--long", "--always", "--dirty",
             "--match", "cewe2pdf-v*"],
            cwd=Path(__file__).resolve().parent,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError, subprocess.CalledProcessError):
        return None

    return result.stdout.strip() or None


def logVersionInformation():
    """Log the user-facing version and Git provenance when it is available."""
    gitBuildIdentification = getGitBuildIdentification()
    if gitBuildIdentification is None:
        mustsee.info(f"cewe2pdf version {PROGRAM_VERSION}; Git identification is unavailable")
    else:
        mustsee.info(f"cewe2pdf version {PROGRAM_VERSION}; Git identification: {gitBuildIdentification}")
