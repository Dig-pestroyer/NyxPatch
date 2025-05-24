"""
Version information for NyxPatcher.

This module provides version information and metadata for the NyxPatcher application.
"""

import datetime
from typing import Dict, Any, Tuple

# Version information
__version__ = "1.0.0"
__release_date__ = "2025-05-23"
__author__ = "Minecraft Mod Update Checker Team"
__license__ = "MIT"
__description__ = "A tool for checking and updating Minecraft mods from Modrinth and CurseForge."

# Package information
PACKAGE_NAME = "NyxPatcher"
REPOSITORY_URL = "https://github.com/Dig-pestroyer/nyxpatcher"

# Version components
VERSION_PARTS = __version__.split(".")
VERSION_MAJOR = int(VERSION_PARTS[0])
VERSION_MINOR = int(VERSION_PARTS[1])
VERSION_PATCH = int(VERSION_PARTS[2])

# Build information
BUILD_DATE = __release_date__
BUILD_TIMESTAMP = datetime.datetime.now().isoformat()

# Version info dictionary with metadata
VERSION_INFO = {
    "version": __version__,
    "major": VERSION_MAJOR,
    "minor": VERSION_MINOR,
    "patch": VERSION_PATCH,
    "release_date": __release_date__,
    "build_date": BUILD_DATE,
    "build_timestamp": BUILD_TIMESTAMP,
    "author": __author__,
    "license": __license__,
    "description": __description__,
    "name": PACKAGE_NAME,
    "repository": REPOSITORY_URL
}


def get_version_string() -> str:
    """
    Get the version as a string.
    
    Returns:
        Formatted version string
    """
    return __version__


def get_version_tuple() -> Tuple[int, int, int]:
    """
    Get the version as a tuple.
    
    Returns:
        Tuple of (major, minor, patch)
    """
    return (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)


def get_version_info() -> Dict[str, Any]:
    """
    Get the complete version information dictionary.
    
    Returns:
        Dictionary containing version information and metadata
    """
    return VERSION_INFO.copy()


def get_user_agent_string() -> str:
    """
    Get a formatted User-Agent string including the version.
    
    Returns:
        User-Agent string for HTTP requests
    """
    return f"{PACKAGE_NAME}/{__version__} (+{REPOSITORY_URL})"

