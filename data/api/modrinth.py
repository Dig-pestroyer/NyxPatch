"""
Modrinth API provider implementation.
"""

import json
import logging
import requests
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from tqdm import tqdm

from data.api.base import BaseProvider

# Modrinth API constants
MODRINTH_API_BASE = "https://api.modrinth.com/v2"
MODRINTH_USER_AGENT = "minecraft-mod-updater/1.0"


class ModrinthProvider(BaseProvider):
    """Provider for interacting with the Modrinth API."""
    
    def __init__(self):
        """Initialize the Modrinth provider."""
        self.headers = {
            "User-Agent": MODRINTH_USER_AGENT
        }
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.logger = logging.getLogger(__name__)
        
    def get_project_id(self, mod_id: str) -> Optional[str]:
        """
        Get the Modrinth project ID for a mod.
        
        Args:
            mod_id: The mod ID to look up
            
        Returns:
            Modrinth project ID or None if not found
        """
        try:
            url = f"{MODRINTH_API_BASE}/search"
            params = {
                "query": mod_id,
                "facets": json.dumps([["project_type:mod"]]),
                "limit": 5
            }
            
            response = self._make_request("GET", url, params=params)
            if not response:
                return None
                
            data = response.json()
            hits = data.get('hits', [])
            
            # Try to find an exact match first
            for hit in hits:
                if hit.get('slug') == mod_id or hit.get('title').lower() == mod_id.lower():
                    self.logger.info(f"Found exact match for mod {mod_id} on Modrinth: {hit.get('project_id')}")
                    return hit.get('project_id')
            
            # If no exact match, use the first result if available
            if hits:
                self.logger.info(f"Using best match for mod {mod_id} on Modrinth: {hits[0].get('project_id')}")
                return hits[0].get('project_id')
            
            self.logger.warning(f"No results found for mod {mod_id} on Modrinth")
            return None
        except Exception as e:
            self.logger.error(f"Error searching for mod {mod_id} on Modrinth: {str(e)}")
            return None
    
    def get_latest_version(
        self, 
        project_id: str, 
        game_version: str, 
        mod_loader: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest version of a mod from Modrinth.
        
        Args:
            project_id: Modrinth project ID
            game_version: Minecraft game version to filter by
            mod_loader: Mod loader to filter by (fabric, forge, quilt)
            
        Returns:
            Dictionary containing version info or None if not found
        """
        try:
            url = f"{MODRINTH_API_BASE}/project/{project_id}/version"
            params = {
                "game_versions": f"[\"{game_version}\"]",
                "loaders": f"[\"{mod_loader}\"]"
            }
            
            response = self._make_request("GET", url, params=params)
            if not response:
                return None
                
            versions = response.json()
            if not versions:
                self.logger.warning(f"No versions found for Modrinth project {project_id}")
                return None
                
            # Strictly filter for versions matching our loader and game version
            filtered_versions = [
                v for v in versions 
                if mod_loader in v.get('loaders', []) 
                and game_version in v.get('game_versions', [])
            ]
            
            if filtered_versions:
                # Add the provider name to the version info
                version_info = filtered_versions[0]
                version_info['provider'] = 'modrinth'
                self.logger.info(f"Found latest version for Modrinth project {project_id}: {version_info.get('version_number')}")
                return version_info
            
            # If no match found, log it and return None
            self.logger.warning(
                f"No {mod_loader} version found for Modrinth project {project_id} "
                f"compatible with Minecraft {game_version}"
            )
            return None
        except Exception as e:
            self.logger.error(f"Error getting versions for Modrinth project {project_id}: {str(e)}")
            return None
    
    def download_mod(
        self, 
        version_info: Dict[str, Any], 
        output_path: str
    ) -> bool:
        """
        Download a mod version to the specified path.
        
        Args:
            version_info: Version information dictionary from get_latest_version
            output_path: Path where the file should be saved
            
        Returns:
            True if download was successful, False otherwise
        """
        try:
            # Get download URL from version info
            files = version_info.get('files', [])
            if not files:
                self.logger.warning("No download files available in version info")
                return False
                
            # Use the primary file (first in the list)
            download_url = files[0].get('url')
            if not download_url:
                self.logger.warning("No download URL available in version info")
                return False
            
            # Download the file
            response = self._make_request("GET", download_url, stream=True)
            if not response:
                return False
                
            # Get file size for progress bar
            total_size = int(response.headers.get('content-length', 0))
            
            # Ensure directory exists
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Download with progress bar
            with open(output_path, 'wb') as f:
                with tqdm(
                    total=total_size,
                    unit='B',
                    unit_scale=True,
                    desc=Path(output_path).name,
                    leave=False
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            
            self.logger.info(f"Successfully downloaded mod to {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error downloading mod: {str(e)}")
            return False
    
    def _make_request(
        self, 
        method: str, 
        url: str, 
        params: Optional[Dict[str, Any]] = None, 
        stream: bool = False
    ) -> Optional[requests.Response]:
        """
        Make an HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request
            params: Query parameters
            stream: Whether to stream the response
            
        Returns:
            Response object or None if request failed
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method, 
                    url, 
                    params=params, 
                    headers=self.headers,
                    stream=stream
                )
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                self.logger.warning(
                    f"Request failed (attempt {attempt+1}/{self.max_retries}): {str(e)}"
                )
                
                # Check if we should retry
                if attempt < self.max_retries - 1:
                    # Implement exponential backoff
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.info(f"Waiting {wait_time}s before retrying...")
                    time.sleep(wait_time)
                else:
                    # Last attempt failed
                    self.logger.error(f"All {self.max_retries} requests failed: {str(e)}")
                    return None
        
        return None  # This should never be reached due to the return in the exception handler

