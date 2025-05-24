"""
Minecraft Mod Update Checker

A tool for checking and updating Minecraft mods from Modrinth and CurseForge.
"""

from data.__version__ import (
    __version__,
    __author__,
    __license__,
    __description__,
    __release_date__,
    get_version_string,
    get_version_info,
    get_version_tuple,
    get_user_agent_string,
    VERSION_INFO
)

# Make version information accessible at package level
__all__ = [
    '__version__',
    '__author__',
    '__license__',
    '__description__',
    '__release_date__',
    'get_version_string',
    'get_version_info',
    'get_version_tuple',
    'get_user_agent_string',
    'VERSION_INFO'
]

