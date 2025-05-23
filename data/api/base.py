"""
Base classes for API providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class BaseProvider(ABC):
    """Base class for mod repository API providers."""

    @abstractmethod
    def get_project_id(self, mod_id: str) -> Optional[str]:
        """
        Get the project ID for a mod from this provider.
        
        Args:
            mod_id: The mod ID to look up
            
        Returns:
            Project ID string or None if not found
        """
        pass
    
    @abstractmethod
    def get_latest_version(
        self, 
        project_id: str, 
        game_version: str, 
        mod_loader: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest version info for a mod.
        
        Args:
            project_id: The provider-specific project ID
            game_version: Minecraft version to filter by (e.g. "1.20.4")
            mod_loader: Mod loader to filter by (e.g. "fabric", "forge", "quilt")
            
        Returns:
            Dictionary containing version information or None if not found
        """
        pass
    
    @abstractmethod
    def download_mod(
        self, 
        version_info: Dict[str, Any], 
        output_path: str
    ) -> bool:
        """
        Download a mod version to the specified path.
        
        Args:
            version_info: Version information dictionary
            output_path: Path where the file should be saved
            
        Returns:
            True if download was successful, False otherwise
        """
        pass

