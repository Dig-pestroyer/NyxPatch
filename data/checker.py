"""
Module for checking and updating Minecraft mods.

This module provides the main functionality for scanning mod directories,
checking for updates, and downloading newer versions.
"""

import os
import json
import logging
import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from tqdm import tqdm

from data.api.modrinth import ModrinthProvider
from data.api.curseforge import CurseForgeProvider
from data.utils.file import (
    get_mod_metadata, 
    find_mod_files, 
    ensure_directory,
    download_file,
    normalize_path
)
from data.utils.version import compare_versions
from data.config import Config
from data.cache.manager import ModCache
from data.__version__ import (
    __version__,
    __release_date__,
    __author__,
    __license__,
    PACKAGE_NAME,
    REPOSITORY_URL
)


class ModUpdateChecker:
    """
    Main class for checking and updating Minecraft mods.
    
    This class handles scanning mod directories, checking for updates,
    and downloading updated mods.
    """
    
    def __init__(
        self,
        config: Config,
        cache: ModCache,
        force_update: bool = False
    ):
        """
        Initialize the mod update checker.
        
        Args:
            config: Configuration object
            cache: Cache manager object
            force_update: Whether to force update checks, ignoring cache
        """
        self.config = config
        self.cache = cache
        self.force_update = force_update
        self.logger = logging.getLogger(__name__)
        
        # Initialize API providers
        self.providers = {}
        self._init_providers()
        
    def _init_providers(self) -> None:
        """Initialize API providers based on configuration."""
        # Initialize Modrinth provider (always available)
        self.providers["modrinth"] = ModrinthProvider()
        
        # Initialize CurseForge provider if API key is available
        if self.config.curseforge_api_key:
            self.providers["curseforge"] = CurseForgeProvider(
                api_key=self.config.curseforge_api_key
            )
        else:
            self.logger.warning(
                "CurseForge API key not set. CurseForge provider will not be available."
            )
    
    def check_updates(self) -> List[Dict[str, Any]]:
        """
        Check for updates to mods.
        
        Returns:
            List of dictionaries containing update information
        """
        # Validate mod directories
        mod_dirs = self.config.validate_mod_directories()
        if not mod_dirs:
            self.logger.error("No valid mod directories found")
            return []
            
        # Scan for mod files
        mod_files = []
        total_mods = 0
        
        # Create a scanning progress bar with status information
        scan_bar = tqdm(
            desc="📁 Scanning directories", 
            total=len(mod_dirs),
            unit="dir", 
            bar_format="{desc}: {percentage:3.0f}% |{bar}| {n_fmt}/{total_fmt} dirs [{elapsed}<{remaining}]",
            position=0,
            leave=True
        )
        
        # Scan each directory
        for mod_dir in mod_dirs:
            self.logger.debug(f"Scanning directory: {mod_dir}")
            found_files = find_mod_files(mod_dir)
            mod_files.extend(found_files)
            total_mods += len(found_files)
            
            # Update the description to show progress
            scan_bar.set_description(f"📁 Scanning directories ({total_mods} mods found)")
            scan_bar.update(1)
            
        scan_bar.close()
            
        # No mods found
        if not mod_files:
            self.logger.warning("No mod files found in configured directories")
            print("No mod files found in the configured directories.")
            return []
            
        # Track processed files for cache cleanup
        processed_files = set()
        
        # Find updates
        updates = []
        
        # Create a processing progress bar with update counter
        process_bar = tqdm(
            mod_files,
            desc=f"🔍 Checking {total_mods} mods for updates (0 found)",
            unit="mod",
            bar_format="{desc}: {percentage:3.0f}% |{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            position=0,
            leave=True
        )
        
        # Process each mod file
        for file_path in process_bar:
            normalized_path = normalize_path(file_path)
            processed_files.add(normalized_path)
            
            try:
                # Extract metadata from the mod file
                mod_metadata = self._get_mod_metadata(normalized_path)
                
                # Skip files without a mod ID
                if not mod_metadata["mod_id"]:
                    self.logger.warning(f"Could not determine mod ID for {file_path}")
                    continue
                    
                # Skip ignored mods
                if mod_metadata["mod_id"] in self.config.ignore_mods:
                    self.logger.info(f"Skipping ignored mod: {mod_metadata['mod_id']}")
                    continue
                    
                # Get project IDs from providers
                project_ids = self._get_project_ids(mod_metadata)
                
                # Check for updates from providers
                update_info = self._check_for_update(mod_metadata, project_ids)
                
                # If an update is available, add it to the list
                if update_info and update_info.get("update_available"):
                    updates.append(update_info)
                    # Update the progress bar description with the count
                    process_bar.set_description(
                        f"🔍 Checking {total_mods} mods for updates ({len(updates)} found)"
                    )
            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {str(e)}")
        
        # Clean up cache if needed
        self.cache.clean_up(processed_files)
        self.cache.save()
        
        # Print a summary of the update check
        update_count = len(updates)
        if update_count > 0:
            print(f"✅ Found {update_count} mod{'' if update_count == 1 else 's'} with available updates")
        else:
            print("✅ All mods are up to date")
        
        return updates
    
    def _get_mod_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Get metadata for a mod file, either from cache or by parsing the file.
        
        Args:
            file_path: Path to the mod file
            
        Returns:
            Dictionary containing mod metadata
        """
        # Check if we have cached metadata
        cached_info = None
        if not self.force_update:
            cached_info = self.cache.get_mod_file_info(file_path)
            
        if cached_info:
            self.logger.debug(f"Using cached metadata for {file_path}")
            return cached_info
            
        # Extract metadata from the file
        self.logger.debug(f"Extracting metadata from {file_path}")
        metadata = get_mod_metadata(file_path)
        
        # Store in cache for future use
        self.cache.set_mod_file_info(file_path, metadata)
        
        return metadata
    
    def _get_project_ids(self, mod_metadata: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        Get project IDs for a mod from various providers.
        
        Args:
            mod_metadata: Mod metadata dictionary
            
        Returns:
            Dictionary with provider names as keys and project IDs as values
        """
        mod_id = mod_metadata["mod_id"]
        
        # Check cache first
        cached_ids = self.cache.get_project_ids(mod_id)
        if not self.force_update and all(cached_ids.values()):
            return cached_ids
            
        # Update project IDs from providers
        updated_ids = {}
        
        # Try primary provider first
        primary = self.config.default_mod_provider
        if primary in self.providers and not cached_ids.get(primary):
            project_id = self.providers[primary].get_project_id(mod_id)
            updated_ids[primary] = project_id
            
        # Then try fallback provider
        fallback = self.config.fallback_mod_provider
        if fallback in self.providers and not cached_ids.get(fallback):
            project_id = self.providers[fallback].get_project_id(mod_id)
            updated_ids[fallback] = project_id
            
        # Update cache with new values
        if updated_ids:
            self.cache.set_project_ids(
                mod_id,
                modrinth_id=updated_ids.get("modrinth", cached_ids.get("modrinth")),
                curseforge_id=updated_ids.get("curseforge", cached_ids.get("curseforge"))
            )
            
        # Merge cached and updated values
        result = cached_ids.copy()
        result.update({k: v for k, v in updated_ids.items() if v is not None})
        
        return result
    
    def _check_for_update(
        self, 
        mod_metadata: Dict[str, Any], 
        project_ids: Dict[str, Optional[str]]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if an update is available for a mod.
        
        Args:
            mod_metadata: Mod metadata dictionary
            project_ids: Dictionary of project IDs by provider
            
        Returns:
            Update information dictionary or None if no update available
        """
        mod_id = mod_metadata["mod_id"]
        current_version = mod_metadata.get("version")
        
        if not current_version:
            self.logger.warning(f"Could not determine current version for {mod_id}")
            return None
            
        self.logger.debug(f"Checking updates for {mod_id} (current: {current_version})")
        
        # Get the latest version from providers
        latest_version_info = self._get_latest_version(
            project_ids,
            self.config.minecraft_version,
            self.config.get_normalized_mod_loader()
        )
        
        if not latest_version_info:
            self.logger.info(f"No update information found for {mod_id}")
            return None
            
        latest_version = latest_version_info.get("version_number")
        if not latest_version:
            self.logger.warning(f"No version number in update info for {mod_id}")
            return None
            
        # Check if update is available
        update_available = compare_versions(current_version, latest_version)
        
        if update_available:
            self.logger.debug(f"Update available for {mod_id}: {current_version} -> {latest_version}")
        else:
            self.logger.debug(f"No update needed for {mod_id} (current: {current_version}, latest: {latest_version})")
            
        # Prepare update information
        update_info = {
            "mod_id": mod_id,
            "mod_name": mod_metadata.get("mod_name", mod_id),
            "current_file": mod_metadata.get("file_name", ""),
            "current_version": current_version,
            "latest_version": latest_version,
            "update_available": update_available,
            "version_info": latest_version_info,
            "provider": latest_version_info.get("provider"),
            "metadata": mod_metadata
        }
        
        return update_info
    
    def _get_latest_version(
        self,
        project_ids: Dict[str, Optional[str]],
        game_version: str,
        mod_loader: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest version information for a mod.
        
        Args:
            project_ids: Dictionary of project IDs by provider
            game_version: Minecraft version to filter by
            mod_loader: Mod loader to filter by
            
        Returns:
            Dictionary containing version information or None if not found
        """
        # Try to get from cache first
        cached_versions = {}
        for provider, project_id in project_ids.items():
            if not project_id:
                continue
                
            if not self.force_update:
                cached_info = self.cache.get_version_info(
                    provider, project_id, game_version, mod_loader
                )
                if cached_info:
                    cached_versions[provider] = cached_info
        
        # If we have cached versions, use them
        if cached_versions:
            # Sort by provider preference
            primary = self.config.default_mod_provider
            fallback = self.config.fallback_mod_provider
            
            if primary in cached_versions:
                return cached_versions[primary]
            elif fallback in cached_versions:
                return cached_versions[fallback]
        
        # Otherwise, query providers
        versions = {}
        
        # Try providers in order of preference
        primary = self.config.default_mod_provider
        fallback = self.config.fallback_mod_provider
        
        for provider_name in [primary, fallback]:
            if provider_name in self.providers and project_ids.get(provider_name):
                provider = self.providers[provider_name]
                project_id = project_ids[provider_name]
                
                version_info = provider.get_latest_version(
                    project_id, game_version, mod_loader
                )
                
                if version_info:
                    # Store in cache
                    self.cache.set_version_info(
                        provider_name, project_id, game_version, mod_loader, version_info
                    )
                    versions[provider_name] = version_info
        
        # Return based on preference
        if primary in versions:
            return versions[primary]
        elif fallback in versions:
            return versions[fallback]
            
        return None
    
    def download_updates(
        self, 
        updates: List[Dict[str, Any]], 
        dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Download updates for mods.
        
        Args:
            updates: List of update information dictionaries
            dry_run: If True, only simulate downloads
            
        Returns:
            List of successfully downloaded updates
        """
        if not updates:
            return []
            
        # Ensure download directory exists
        download_dir = self.config.get_absolute_download_directory()
        if not dry_run and not self.config.create_download_directory():
            self.logger.error(f"Failed to create download directory: {download_dir}")
            return []
            
        successful_downloads = []
        
        print(f"Downloading {len(updates)} mod updates...")
        for update in tqdm(updates, desc="Downloading updates", unit="mod"):
            mod_id = update["mod_id"]
            mod_name = update["mod_name"]
            provider = update["provider"]
            version_info = update["version_info"]
            latest_version = update["latest_version"]
            
            if provider not in self.providers:
                self.logger.error(f"Provider {provider} not available for {mod_id}")
                continue
                
            # Generate output filename
            output_filename = self._generate_output_filename(mod_id, mod_name, latest_version)
            output_path = os.path.join(download_dir, output_filename)
            
            self.logger.debug(f"Downloading {mod_id} v{latest_version} to {output_path}")
            
            if dry_run:
                self.logger.info(f"[DRY RUN] Would download {mod_id} v{latest_version}")
                successful_downloads.append(update)
                continue
                
            # Perform the download
            success = self.providers[provider].download_mod(version_info, output_path)
            
            if success:
                self.logger.debug(f"Successfully downloaded {mod_id} v{latest_version}")
                successful_downloads.append(update)
            else:
                self.logger.error(f"Failed to download {mod_id} v{latest_version}")
                
        return successful_downloads
    
    def _generate_output_filename(
        self, 
        mod_id: str, 
        mod_name: str, 
        version: str
    ) -> str:
        """
        Generate an output filename for a downloaded mod.
        
        Args:
            mod_id: Mod ID
            mod_name: Mod name
            version: Version string
            
        Returns:
            Output filename
        """
        # Use mod name if available, fallback to mod ID
        base_name = mod_name.replace(" ", "_") if mod_name else mod_id
        
        # Sanitize filename
        base_name = "".join(c for c in base_name if c.isalnum() or c in "_-")
        
        # Create filename with version
        filename = f"{base_name}-{version}.jar"
        
        return filename
        
    def write_update_report(self, updates: List[Dict[str, Any]]) -> Optional[str]:
        """
        Write a report of available updates to a file.
        
        Args:
            updates: List of update information dictionaries
            
        Returns:
            Path to the report file or None if writing failed
        """
        if not updates:
            self.logger.info("No updates to report")
            return None
            
        try:
            # Create reports directory if needed
            report_dir = os.path.join(os.path.dirname(self.config.config_file), "reports")
            if not ensure_directory(report_dir):
                self.logger.error(f"Failed to create reports directory: {report_dir}")
                return None
                
            # Generate report filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(report_dir, f"update_report_{timestamp}.txt")
            
            # Write report
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(f"=== {PACKAGE_NAME} Mod Update Report ===\n")
                f.write(f"{PACKAGE_NAME} Version: {__version__} (Released: {__release_date__})\n")
                f.write(f"Report Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Minecraft Version: {self.config.minecraft_version}\n")
                f.write(f"Mod Loader: {self.config.mod_loader}\n")
                f.write(f"Repository: {REPOSITORY_URL}\n")
                f.write(f"License: {__license__}\n")
                f.write("\n")
                
                f.write(f"Found {len(updates)} mods with available updates:\n\n")
                
                for i, update in enumerate(updates, 1):
                    mod_id = update["mod_id"]
                    mod_name = update["mod_name"]
                    current_version = update["current_version"]
                    latest_version = update["latest_version"]
                    provider = update["provider"]
                    version_info = update.get("version_info", {})
                    
                    f.write(f"{i}. {mod_name} ({mod_id})\n")
                    f.write(f"   Current Version: {current_version}\n")
                    f.write(f"   Latest Version: {latest_version}\n")
                    f.write(f"   Provider: {provider}\n")
                    
                    # Get and write mod page URL with fallbacks
                    mod_page_url = version_info.get("mod_page_url")
                    project_id = version_info.get("project_id")
                    
                    # Provider-specific fallback URLs for mod page
                    if not mod_page_url:
                        if provider == "modrinth" and project_id:
                            mod_page_url = f"https://modrinth.com/mod/{project_id}"
                        elif provider == "curseforge" and project_id:
                            mod_page_url = f"https://www.curseforge.com/minecraft/mc-mods/{project_id}"
                        # Additional fallback for CurseForge using slug if available
                        elif provider == "curseforge" and version_info.get("slug"):
                            mod_page_url = f"https://www.curseforge.com/minecraft/mc-mods/{version_info['slug']}"
                        # Final fallback using mod_id
                        else:
                            # Try to construct a generic URL based on provider
                            if provider == "modrinth":
                                mod_page_url = f"https://modrinth.com/mod/{mod_id}"
                            elif provider == "curseforge":
                                mod_page_url = f"https://www.curseforge.com/minecraft/mc-mods/{mod_id}"
                    
                    # Get download URL with comprehensive fallbacks
                    download_url = None
                    direct_jar_url = None
                    
                    # Try to get URL from files array first (most reliable)
                    if "files" in version_info and version_info["files"]:
                        # First try to find a direct .jar URL
                        for file_info in version_info["files"]:
                            if "download_url" in file_info and file_info["download_url"].lower().endswith('.jar'):
                                direct_jar_url = file_info["download_url"]
                                download_url = direct_jar_url
                                break
                        
                        # If no direct .jar URL found, use the first available download URL
                        if not download_url:
                            for file_info in version_info["files"]:
                                if "download_url" in file_info:
                                    download_url = file_info["download_url"]
                                    break
                    
                    # Fall back to direct download_url if available
                    if not download_url and "download_url" in version_info:
                        download_url = version_info["download_url"]
                        # Check if this is a direct .jar URL
                        if download_url and download_url.lower().endswith('.jar'):
                            direct_jar_url = download_url
                    
                    # Provider-specific fallback download URLs
                    if not download_url:
                        if provider == "modrinth" and project_id and version_info.get("version_id"):
                            download_url = f"https://modrinth.com/mod/{project_id}/version/{version_info['version_id']}"
                        elif provider == "curseforge" and version_info.get("file_id"):
                            download_url = f"https://www.curseforge.com/minecraft/mc-mods/{project_id}/files/{version_info['file_id']}"
                        # Final fallback using project_id and latest_version
                        elif provider == "modrinth" and project_id:
                            download_url = f"https://modrinth.com/mod/{project_id}/versions"
                        elif provider == "curseforge" and project_id:
                            download_url = f"https://www.curseforge.com/minecraft/mc-mods/{project_id}/files/all"
                    
                    # Write links section with clear formatting
                    f.write("   === MOD LINKS ===\n")
                    
                    # Always write mod page URL (we should have at least a fallback)
                    if mod_page_url:
                        f.write(f"   MOD PAGE:   {mod_page_url}\n")
                        f.write(f"   • View mod details, documentation, and issues\n")
                    else:
                        f.write(f"   MOD PAGE:   Not available for {provider}\n")
                    
                    # Prioritize direct .jar URL if available, otherwise use regular download URL
                    if direct_jar_url:
                        f.write(f"   DOWNLOAD:   {direct_jar_url}\n")
                        f.write(f"   • Direct .jar download for version {latest_version}\n")
                    elif download_url:
                        f.write(f"   DOWNLOAD:   {download_url}\n")
                        f.write(f"   • Use this URL to manually download version {latest_version}\n")
                    else:
                        f.write(f"   DOWNLOAD:   Not available for {provider}\n")
                    
                    # Add changelog URL if available
                    if "changelog_url" in version_info:
                        f.write(f"   Changelog: {version_info['changelog_url']}\n")
                        
                    if "date_published" in version_info:
                        f.write(f"   Published: {version_info['date_published']}\n")
                    
                    # Additional mod info section
                    f.write("   -----------------------------------------\n")
                    
                    f.write("\n")
                    
            self.logger.info(f"Update report written to {report_file}")
            return report_file
            
        except IOError as e:
            self.logger.error(f"Error writing update report: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error writing report: {str(e)}")
            return None
    
    def interactive_download_menu(self, updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Display an interactive menu for selecting mods to update.
        
        Args:
            updates: List of update information dictionaries
            
        Returns:
            List of selected updates
        """
        if not updates:
            return []
            
        try:
            print("\n=== Available Mod Updates ===\n")
            print(f"Found {len(updates)} mods with available updates:\n")
            
            # Display updates in a more concise format
            for i, update in enumerate(updates, 1):
                mod_name = update["mod_name"]
                current_version = update["current_version"]
                latest_version = update["latest_version"]
                
                print(f"{i}. {mod_name} [{current_version} → {latest_version}]")
                
            # Menu options
            print("\nOptions:")
            print("a - Download all updates")
            print("n - Download none")
            print("s - Select specific updates (comma-separated numbers)")
            
            # Get user input
            while True:
                choice = input("\nEnter your choice: ").strip().lower()
                
                if choice == 'a':
                    print(f"Selected all {len(updates)} updates for download")
                    return updates
                elif choice == 'n':
                    print("No updates selected")
                    return []
                elif choice == 's':
                    # Get selection numbers
                    while True:
                        selection = input("Enter update numbers (comma-separated): ").strip()
                        try:
                            # Parse selection numbers
                            if not selection:
                                print("No updates selected")
                                return []
                                
                            selected_indices = []
                            for part in selection.split(','):
                                part = part.strip()
                                if not part:
                                    continue
                                    
                                num = int(part)
                                if 1 <= num <= len(updates):
                                    selected_indices.append(num - 1)  # Convert to zero-based index
                                else:
                                    raise ValueError(f"Invalid selection: {num}")
                                    
                            # Create list of selected updates
                            selected_updates = [updates[i] for i in selected_indices]
                            
                            if not selected_updates:
                                print("No updates selected")
                            else:
                                print(f"Selected {len(selected_updates)} updates for download")
                                
                            return selected_updates
                            
                        except ValueError as e:
                            print(f"Invalid input: {str(e)}")
                else:
                    print("Invalid choice, please try again")
        except Exception as e:
            self.logger.error(f"Error in interactive menu: {str(e)}")
            print("\nError displaying interactive menu. No updates will be downloaded.")
            return []
