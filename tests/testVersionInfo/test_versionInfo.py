from subprocess import CalledProcessError
from unittest.mock import Mock, patch

from versionInfo import (PROGRAM_VERSION, getGitBuildIdentification,
    getVersionInformationText, logVersionInformation)


def test_get_git_build_identification_returns_description():
    completedProcess = Mock(stdout="cewe2pdf-v0.11-build-184-3-g1234567-dirty\n")
    with patch("versionInfo.subprocess.run", return_value=completedProcess):
        assert getGitBuildIdentification() == "cewe2pdf-v0.11-build-184-3-g1234567-dirty"


def test_get_git_build_identification_handles_missing_git():
    with patch("versionInfo.subprocess.run", side_effect=FileNotFoundError):
        assert getGitBuildIdentification() is None


def test_get_git_build_identification_handles_non_git_directory():
    with patch("versionInfo.subprocess.run", side_effect=CalledProcessError(128, "git")):
        assert getGitBuildIdentification() is None


def test_get_git_build_identification_uses_frozen_build_information():
    gitBuildIdentification = "cewe2pdf-v1.0-build-178-0-g1234567"
    with patch("versionInfo.FROZEN_GIT_BUILD_IDENTIFICATION", gitBuildIdentification):
        with patch("versionInfo.subprocess.run") as gitDescribe:
            assert getGitBuildIdentification() == gitBuildIdentification

    gitDescribe.assert_not_called()


def test_get_version_information_text():
    gitBuildIdentification = "cewe2pdf-v1.0-build-178-0-g1234567"
    with patch("versionInfo.getGitBuildIdentification", return_value=gitBuildIdentification):
        assert getVersionInformationText() == (
            f"cewe2pdf version {PROGRAM_VERSION}; Git identification: {gitBuildIdentification}")


def test_log_version_information_with_git_build_identification():
    gitBuildIdentification = "cewe2pdf-v0.99-build-184-3-g1234567-dirty"
    with patch("versionInfo.getGitBuildIdentification", return_value=gitBuildIdentification):
        with patch("versionInfo.mustsee.info") as logInfo:
            logVersionInformation()

    logInfo.assert_called_once_with(
        f"cewe2pdf version {PROGRAM_VERSION}; Git identification: {gitBuildIdentification}")


def test_log_version_information_without_git_build_identification():
    with patch("versionInfo.getGitBuildIdentification", return_value=None):
        with patch("versionInfo.mustsee.info") as logInfo:
            logVersionInformation()

    logInfo.assert_called_once_with(
        f"cewe2pdf version {PROGRAM_VERSION}; Git identification is unavailable")


def testall():
    test_get_git_build_identification_returns_description()
    test_get_git_build_identification_handles_missing_git()
    test_get_git_build_identification_handles_non_git_directory()
    test_get_git_build_identification_uses_frozen_build_information()
    test_get_version_information_text()
    test_log_version_information_with_git_build_identification()
    test_log_version_information_without_git_build_identification()


if __name__ == '__main__':
    testall()
