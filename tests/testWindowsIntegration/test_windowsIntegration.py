"""Test Windows-installation discovery without requiring a Windows registry."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

# Keep direct execution as reliable as pytest collection from the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from windowsIntegration import (_executableFolderFromCommand, findInstalledCeweFolder,
                                isCeweInstallationFolder)
from albumConversionSession import AlbumConversionSession
from extraLoggers import configlogger, mustsee


def _makeCeweFolder(folder: Path) -> Path:
    """Create the small part of a CEWE installation used for validation."""
    (folder / 'Resources' / 'config').mkdir(parents=True)
    (folder / 'Resources' / 'config' / 'keyaccount.xml').write_text('<keyaccount/>')
    (folder / 'Resources' / 'photofun' / 'fonts').mkdir(parents=True)
    return folder


def test_isCeweInstallationFolder_requiresExpectedResources():
    with TemporaryDirectory() as temporaryDirectory:
        temporaryPath = Path(temporaryDirectory)
        missingFolder = temporaryPath / 'missing-fonts'
        (missingFolder / 'Resources' / 'config').mkdir(parents=True)
        (missingFolder / 'Resources' / 'config' / 'keyaccount.xml').write_text('<keyaccount/>')

        assert not isCeweInstallationFolder(missingFolder)
        assert isCeweInstallationFolder(_makeCeweFolder(temporaryPath / 'valid-cewe'))


def test_findInstalledCeweFolder_selectsFirstValidCandidate():
    with TemporaryDirectory() as temporaryDirectory:
        temporaryPath = Path(temporaryDirectory)
        invalidFolder = temporaryPath / 'not-cewe'
        invalidFolder.mkdir()
        firstCeweFolder = _makeCeweFolder(temporaryPath / 'first-cewe')
        _makeCeweFolder(temporaryPath / 'second-cewe')

        foundFolder = findInstalledCeweFolder((
            invalidFolder, firstCeweFolder, temporaryPath / 'second-cewe'))

        assert foundFolder == str(firstCeweFolder)


def test_executableFolderFromCommand_handlesNormalWindowsAssociation():
    command = r'"C:\Program Files\Elkjop fotoservice\elkjop fotoservice.exe" "%1"'

    executableFolder = _executableFolderFromCommand(command)

    assert executableFolder == Path(r'C:\Program Files\Elkjop fotoservice')


def test_automaticSessionWritesAllUserVisibleLoggers():
    """Explorer mode retains root, config, and must-see diagnostics in a log."""
    with TemporaryDirectory() as temporaryDirectory:
        albumName = Path(temporaryDirectory) / 'example.mcf'
        session = AlbumConversionSession(
            str(albumName), False, None, None, None, None, 1, 86, None,
            automaticWindows=True)

        session._startAutomaticLog()
        configlogger.warning('configuration diagnostic')
        mustsee.info('must-see diagnostic')
        session._closeAutomaticLog()

        logText = Path(str(albumName) + '.log').read_text(encoding='utf-8')
        assert 'Writing automatic conversion log to:' in logText
        assert logText.count('configuration diagnostic') == 1
        assert logText.count('must-see diagnostic') == 1


def test_automaticSessionDoesNotDuplicatePropagatingLoggers():
    """The PyInstaller fallback configuration lets specialised loggers propagate."""
    originalConfigPropagation = configlogger.propagate
    originalMustSeePropagation = mustsee.propagate
    try:
        configlogger.propagate = True
        mustsee.propagate = True
        with TemporaryDirectory() as temporaryDirectory:
            albumName = Path(temporaryDirectory) / 'example.mcf'
            session = AlbumConversionSession(
                str(albumName), False, None, None, None, None, 1, 86, None,
                automaticWindows=True)
            session._startAutomaticLog()
            configlogger.warning('propagating configuration diagnostic')
            mustsee.info('propagating must-see diagnostic')
            session._closeAutomaticLog()

            logText = Path(str(albumName) + '.log').read_text(encoding='utf-8')
    finally:
        configlogger.propagate = originalConfigPropagation
        mustsee.propagate = originalMustSeePropagation

    assert logText.count('propagating configuration diagnostic') == 1
    assert logText.count('propagating must-see diagnostic') == 1
