"""Optional Windows conveniences for the standalone cewe2pdf executable.

This module is deliberately independent of the renderer.  Importing it on
Linux or macOS is harmless; its Windows-only operations simply report that
they are unavailable.
"""

import ctypes
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Iterable


APPLICATION_NAME = 'cewe2pdf'
EXPLORER_MENU_TEXT = 'Create PDF with cewe2pdf'
FILE_EXTENSIONS = ('.mcf', '.mcfx')
INSTALL_REGISTRY_KEY = r'Software\cewe2pdf'


def isWindowsFrozenExecutable() -> bool:
    """Return whether this is the Windows executable made by PyInstaller."""
    return os.name == 'nt' and getattr(sys, 'frozen', False)


def isCeweInstallationFolder(folder: str | Path) -> bool:
    """Return whether *folder* has the CEWE resources required by cewe2pdf."""
    folderPath = Path(folder)
    return (
        folderPath.is_dir()
        and (folderPath / 'Resources' / 'config' / 'keyaccount.xml').is_file()
        and (folderPath / 'Resources' / 'photofun' / 'fonts').is_dir())


def _registryInstallationFolders() -> tuple[Path, ...]:
    """Return possible application roots from standard Windows uninstall keys."""
    if os.name != 'nt':
        return tuple()

    import winreg  # pylint: disable=import-outside-toplevel

    uninstallKeys = (
        r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
        r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall')
    candidates: list[Path] = []
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for uninstallKey in uninstallKeys:
            try:
                with winreg.OpenKey(hive, uninstallKey) as key:
                    subkeyCount = winreg.QueryInfoKey(key)[0]
                    subkeyNames = (winreg.EnumKey(key, index) for index in range(subkeyCount))
                    for subkeyName in subkeyNames:
                        try:
                            with winreg.OpenKey(key, subkeyName) as subkey:
                                installLocation, _ = winreg.QueryValueEx(subkey, 'InstallLocation')
                                if installLocation:
                                    candidates.append(Path(installLocation))
                        except OSError:
                            continue
            except OSError:
                continue
    return tuple(candidates)


def _executableFolderFromCommand(command: str | None) -> Path | None:
    """Extract an executable's parent folder from a Windows open command."""
    if not command:
        return None
    # Registered commands normally quote an executable path because Program
    # Files contains a space.  Also accept an unusual unquoted path without
    # spaces; anything more elaborate is left to the uninstall-key fallback.
    match = re.match(r'^\s*"([^\"]+\.exe)"|^\s*([^\s]+\.exe)', command, re.IGNORECASE)
    if match is None:
        return None
    return Path(match.group(1) or match.group(2)).parent


def _readRegistryValue(hive, keyName: str, valueName: str = '') -> str | None:
    """Return a registry string value, treating a missing value as normal."""
    import winreg  # pylint: disable=import-outside-toplevel

    try:
        with winreg.OpenKey(hive, keyName) as key:
            value, _ = winreg.QueryValueEx(key, valueName)
            return value if isinstance(value, str) else None
    except OSError:
        return None


def _associatedCeweFolders() -> tuple[Path, ...]:
    """Return folders used by Windows to open MCF and MCFX files.

    The default program is the best evidence for a CEWE installation, and
    works equally for CEWE's retailer-branded editions.  UserChoice is checked
    first because Windows may override the normal extension association there.
    """
    if os.name != 'nt':
        return tuple()

    import winreg  # pylint: disable=import-outside-toplevel

    candidates: list[Path] = []
    for extension in FILE_EXTENSIONS:
        progIds = []
        userChoice = _readRegistryValue(
            winreg.HKEY_CURRENT_USER,
            fr'Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{extension}\UserChoice',
            'ProgId')
        association = _readRegistryValue(winreg.HKEY_CLASSES_ROOT, extension)
        for progId in (userChoice, association):
            if progId and progId not in progIds:
                progIds.append(progId)
        for progId in progIds:
            command = _readRegistryValue(
                winreg.HKEY_CLASSES_ROOT, fr'{progId}\shell\open\command')
            executableFolder = _executableFolderFromCommand(command)
            if executableFolder is not None:
                candidates.append(executableFolder)
    return tuple(candidates)


def findInstalledCeweFolder(candidateFolders: Iterable[str | Path] | None = None) -> str | None:
    """Find a valid local CEWE application folder, or return ``None``.

    The optional candidates argument makes the validation logic easy to test
    without Windows registry access.
    """
    candidates = tuple(candidateFolders) if candidateFolders is not None else (
        _associatedCeweFolders() + _registryInstallationFolders())
    for candidate in candidates:
        if isCeweInstallationFolder(candidate):
            return str(Path(candidate))
    return None


def _notifyExplorerOfAssociationChange() -> None:
    """Ask Explorer to refresh file-association menus after a registry change."""
    if os.name == 'nt':
        # SHCNE_ASSOCCHANGED, SHCNF_IDLIST, ignored item pointers.
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


def _setRegistryDefault(key, value: str) -> None:
    import winreg  # pylint: disable=import-outside-toplevel
    winreg.SetValueEx(key, '', 0, winreg.REG_SZ, value)


def _installExplorerVerb(executablePath: Path, extension: str) -> None:
    import winreg  # pylint: disable=import-outside-toplevel

    verbKeyName = fr'Software\Classes\SystemFileAssociations\{extension}\shell\{APPLICATION_NAME}'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, verbKeyName) as verbKey:
        winreg.SetValueEx(verbKey, 'MUIVerb', 0, winreg.REG_SZ, EXPLORER_MENU_TEXT)
        winreg.SetValueEx(verbKey, 'Icon', 0, winreg.REG_SZ, f'{executablePath},0')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, verbKeyName + r'\command') as commandKey:
        _setRegistryDefault(commandKey, f'"{executablePath}" --automatic "%1"')


def installWindowsIntegration(sourceExecutable: str | Path | None = None) -> Path:
    """Copy the frozen executable locally and install per-user Explorer menus."""
    if not isWindowsFrozenExecutable():
        raise RuntimeError('Windows integration is available only from the frozen Windows executable.')

    sourcePath = Path(sourceExecutable or sys.executable).resolve()
    localAppData = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    installFolder = localAppData / APPLICATION_NAME
    installFolder.mkdir(parents=True, exist_ok=True)
    installedExecutable = installFolder / sourcePath.name
    if sourcePath != installedExecutable:
        shutil.copy2(sourcePath, installedExecutable)

    import winreg  # pylint: disable=import-outside-toplevel
    for extension in FILE_EXTENSIONS:
        _installExplorerVerb(installedExecutable, extension)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, INSTALL_REGISTRY_KEY) as installationKey:
        winreg.SetValueEx(installationKey, 'InstallPath', 0, winreg.REG_SZ, str(installedExecutable))
    _notifyExplorerOfAssociationChange()
    return installedExecutable


def uninstallWindowsIntegration() -> str | None:
    """Remove the per-user Explorer menus, leaving the installed EXE in place."""
    if os.name != 'nt':
        raise RuntimeError('Windows integration is available only on Windows.')

    import winreg  # pylint: disable=import-outside-toplevel
    installedPath = None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, INSTALL_REGISTRY_KEY) as installationKey:
            installedPath, _ = winreg.QueryValueEx(installationKey, 'InstallPath')
    except OSError:
        pass

    for extension in FILE_EXTENSIONS:
        verbKeyName = fr'Software\Classes\SystemFileAssociations\{extension}\shell\{APPLICATION_NAME}'
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, verbKeyName + r'\command')
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, verbKeyName)
        except OSError:
            continue
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, INSTALL_REGISTRY_KEY)
    except OSError:
        pass
    _notifyExplorerOfAssociationChange()
    return installedPath


def confirmInstallation() -> bool:
    """Ask a double-click user before changing files or the registry."""
    if os.name != 'nt':
        return False
    message = (
        'Install cewe2pdf for this Windows user?\n\n'
        'This copies the executable to your local application folder and adds\n'
        '“Create PDF with cewe2pdf” to the right-click menu for MCF and MCFX files.')
    # MB_YESNO | MB_ICONQUESTION. IDYES is 6.
    return ctypes.windll.user32.MessageBoxW(None, message, APPLICATION_NAME, 0x24) == 6


def showMessage(message: str, error: bool = False) -> None:
    """Show a short native Windows message without adding a GUI dependency."""
    if os.name == 'nt':
        icon = 0x10 if error else 0x40  # MB_ICONERROR / MB_ICONINFORMATION
        ctypes.windll.user32.MessageBoxW(None, message, APPLICATION_NAME, icon)
    else:
        print(message)
