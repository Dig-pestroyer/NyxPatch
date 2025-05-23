"""
Cache management for mod update checker.

This module provides cache functionality to store and retrieve information about mods,
their versions, and download history to reduce API calls and improve performance.
"""

import os
import json
import logging
from typing import Dict, Optional, Any, Set
from datetime import datetime
from pathlib import Path


# Default cache settings
DEFAULT_CACHE_FILE = "mod_cache.json"
DEFAULT_CACHE_EXPIRY_HOURS = 168  # 7 days (1 week)


class ModCache:
    """
    Class for managing mod cache data and operations.
    
    This class handles storing and retrieving information about mods, including
    file metadata, project IDs, latest versions, and download history.
    """
    
    def __init__(
        self,
        cache_file: str = DEFAULT_CACHE_FILE,
        last_scan: Optional[str] = None,
        mod_files: Dict[str, Dict[str, Any]] = None,
        project_ids: Dict[str, Dict[str, Any]] = None,
        latest_versions: Dict[str, Dict[str, Any]] = None,
        downloaded_files: Dict[str, Dict[str, Any]] = None
    ):
        """
        Initialize the ModCache instance.
        
        Args:
            cache_file: Path to the cache file
            last_scan: ISO formatted datetime string of the last scan
            mod_files: Dictionary of mod file metadata
            project_ids: Dictionary of project IDs by provider
            latest_versions: Dictionary of latest version info
            downloaded_files: Dictionary of downloaded file info
        """
        self.cache_file = cache_file
        self.last_scan = last_scan
        self.mod_files = mod_files or {}
        self.project_ids = project_ids or {}
        self.latest_versions = latest_versions or {}
        self.downloaded_files = downloaded_files or {}
        self.logger = logging.getLogger(__name__)
    
    @classmethod
    def load(cls, cache_file: str = DEFAULT_CACHE_FILE) -> 'ModCache':
        """
        Load cache from file or return a new empty cache.
        
        Args:
            cache_file: Path to the cache file
            
        Returns:
            ModCache instance with loaded data or defaults
        """
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    logging.info(f"Loaded cache from {cache_file}")
                    
                    return cls(
                        cache_file=cache_file,
                        last_scan=data.get("last_scan"),
                        mod_files=data.get("mod_files", {}),
                        project_ids=data.get("project_ids", {}),
                        latest_versions=data.get("latest_versions", {}),
                        downloaded_files=data.get("downloaded_files", {})
                    )
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Error loading cache: {str(e)}")
            
            # If the file is corrupted, try to create a backup
            if os.path.exists(cache_file):
                backup_file = f"{cache_file}.bak"
                try:
                    os.rename(cache_file, backup_file)
                    logging.warning(f"Corrupted cache file renamed to {backup_file}")
                except OSError:
                    logging.error(f"Failed to create backup of corrupted cache file")
        
        # Return new cache if loading failed
        return cls(cache_file=cache_file)
    
    def save(self) -> bool:
        """
        Save cache to file.
        
        Returns:
            True if save was successful, False otherwise
        """
        try:
            # Update last scan timestamp
            self.last_scan = datetime.now().isoformat()
            
            # Prepare data for serialization
            data = {
                "last_scan": self.last_scan,
                "mod_files": self.mod_files,
                "project_ids": self.project_ids,
                "latest_versions": self.latest_versions,
                "downloaded_files": self.downloaded_files
            }
            
            # Write to a temporary file first for atomic operation
            temp_file = f"{self.cache_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=4)
            
            # Replace the original file with the temp file
            if os.path.exists(self.cache_file):
                os.replace(temp_file, self.cache_file)
            else:
                os.rename(temp_file, self.cache_file)
                
            self.logger.info(f"Cache saved to {self.cache_file}")
            return True
        except IOError as e:
            self.logger.error(f"Error saving cache: {str(e)}")
            return False
    
    def is_expired(self, expiry_hours: int = DEFAULT_CACHE_EXPIRY_HOURS) -> bool:
        """
        Check if the cache has expired.
        
        Args:
            expiry_hours: Number of hours after which cache is considered expired
            
        Returns:
            True if the cache has expired, False otherwise
        """
        if not self.last_scan:
            return True
            
        try:
            last_scan = datetime.fromisoformat(self.last_scan)
            now = datetime.now()
            
            # Check if cache has expired
            time_difference = now - last_scan
            if time_difference.total_seconds() > (expiry_hours * 3600):
                self.logger.info(f"Cache expired (age: {time_difference.total_seconds() / 3600:.1f} hours)")
                return True
                
            return False
        except (ValueError, TypeError):
            self.logger.warning("Invalid last_scan timestamp, considering cache expired")
            return True
    
    def get_project_ids(self, mod_id: str) -> Dict[str, Optional[str]]:
        """
        Get cached project IDs for a mod.
        
        Args:
            mod_id: The mod ID to lookup
            
        Returns:
            Dictionary containing provider project IDs or None
        """
        if mod_id in self.project_ids:
            return self.project_ids[mod_id]
        return {"modrinth": None, "curseforge": None}
    
    def set_project_ids(self, mod_id: str, modrinth_id: Optional[str] = None, curseforge_id: Optional[str] = None) -> None:
        """
        Store project IDs for a mod in the cache.
        
        Args:
            mod_id: The mod ID
            modrinth_id: Modrinth project ID
            curseforge_id: CurseForge project ID
        """
        if mod_id not in self.project_ids:
            self.project_ids[mod_id] = {}
            
        # Only update if the value is not None
        if modrinth_id is not None:
            self.project_ids[mod_id]["modrinth"] = modrinth_id
        if curseforge_id is not None:
            self.project_ids[mod_id]["curseforge"] = curseforge_id
    
    def get_mod_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get cached information about a mod file.
        
        Args:
            file_path: Absolute path to the mod file
            
        Returns:
            Dictionary containing file info or None if not in cache
        """
        return self.mod_files.get(file_path)
    
    def set_mod_file_info(self, file_path: str, info: Dict[str, Any]) -> None:
        """
        Store information about a mod file in the cache.
        
        Args:
            file_path: Absolute path to the mod file
            info: Dictionary containing file information
        """
        self.mod_files[file_path] = info
    
    def remove_mod_file(self, file_path: str) -> None:
        """
        Remove a mod file from the cache.
        
        Args:
            file_path: Absolute path to the mod file
        """
        if file_path in self.mod_files:
            del self.mod_files[file_path]
    
    def get_version_info(self, provider: str, project_id: str, game_version: str, mod_loader: str) -> Optional[Dict[str, Any]]:
        """
        Get cached version information for a mod.
        
        Args:
            provider: Provider name ('modrinth' or 'curseforge')
            project_id: Provider-specific project ID
            game_version: Minecraft version
            mod_loader: Mod loader type
            
        Returns:
            Dictionary containing version info or None if not in cache
        """
        cache_key = f"{provider}:{project_id}:{game_version}:{mod_loader}"
        return self.latest_versions.get(cache_key)
    
    def set_version_info(self, provider: str, project_id: str, game_version: str, mod_loader: str, version_info: Dict[str, Any]) -> None:
        """
        Store version information for a mod in the cache.
        
        Args:
            provider: Provider name ('modrinth' or 'curseforge')
            project_id: Provider-specific project ID
            game_version: Minecraft version
            mod_loader: Mod loader type
            version_info: Dictionary containing version information
        """
        cache_key = f"{provider}:{project_id}:{game_version}:{mod_loader}"
        self.latest_versions[cache_key] = version_info
    
    def get_download_info(self, mod_name: str, version: str) -> Optional[Dict[str, Any]]:
        """
        Get cached download information for a mod version.
        
        Args:
            mod_name: Name of the mod
            version: Version of the mod
            
        Returns:
            Dictionary containing download info or None if not in cache
        """
        cache_key = f"{mod_name}:{version}"
        return self.downloaded_files.get(cache_key)
    
    def set_download_info(self, mod_name: str, version: str, download_info: Dict[str, Any]) -> None:
        """
        Store download information for a mod version in the cache.
        
        Args:
            mod_name: Name of the mod
            version: Version of the mod
            download_info: Dictionary containing download information
        """
        cache_key = f"{mod_name}:{version}"
        self.downloaded_files[cache_key] = download_info
    
    def clean_up(self, processed_files: Optional[Set[str]] = None) -> None:
        """
        Clean up the cache by removing entries for files that no longer exist.
        
        Args:
            processed_files: Set of file paths that were processed in the current run
        """
        if processed_files:
            for file_path in list(self.mod_files.keys()):
                if file_path not in processed_files:
                    self.logger.info(f"Removing deleted file from cache: {file_path}")
                    self.remove_mod_file(file_path)
                    
    def prune_old_versions(self, max_age_days: int = 30) -> int:
        """
        Remove version information older than the specified age.
        
        Args:
            max_age_days: Maximum age in days for version information
            
        Returns:
            Number of pruned entries
        """
        if not self.latest_versions:
            return 0
            
        now = datetime.now()
        max_age_seconds = max_age_days * 24 * 3600
        pruned_count = 0
        
        for key in list(self.latest_versions.keys()):
            version_info = self.latest_versions[key]
            date_str = version_info.get('date_published')
            
            if not date_str:
                continue
                
            try:
                # Handle ISO format with Z for UTC
                if date_str.endswith('Z'):
                    date_str = date_str[:-1] + '+00:00'
                    
                pub_date = datetime.fromisoformat(date_str)
                age = now - pub_date
                
                if age.total_seconds() > max_age_seconds:
                    del self.latest_versions[key]
                    pruned_count += 1
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid date format: {date_str}")
        
        if pruned_count > 0:
            self.logger.info(f"Pruned {pruned_count} old version entries from cache")
            
        return pruned_count
