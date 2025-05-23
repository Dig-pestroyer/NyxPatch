"""
Configuration management for mod update checker.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional


class Config:
    """Configuration manager for mod update checker."""
    
    DEFAULT_CONFIG_FILE = "config.json"
    
    DEFAULT_CONFIG = {
        "mod_directories": ["../mods"],
        "minecraft_version": "1.20.4",
        "mod_loader": "fabric",
        "download_directory": "downloads",
        "ignore_mods": [],
        "default_mod_provider": "modrinth",
        "fallback_mod_provider": "curseforge",
        "curseforge_api_key": ""
    }
    
    def __init__(
        self,
        config_file: str = DEFAULT_CONFIG_FILE,
        mod_directories: Optional[List[str]] = None,
        minecraft_version: str = "1.20.4",
        mod_loader: str = "fabric",
        download_directory: str = "downloads",
        ignore_mods: Optional[List[str]] = None,
        default_mod_provider: str = "modrinth",
        fallback_mod_provider: str = "curseforge",
        curseforge_api_key: str = ""
    ):
        """
        Initialize configuration.
        
        Args:
            config_file: Path to configuration file
            mod_directories: List of directories containing mods
            minecraft_version: Minecraft version to check for
            mod_loader: Mod loader type (fabric, forge, quilt)
            download_directory: Directory to save downloaded mods
            ignore_mods: List of mod IDs to ignore
            default_mod_provider: Primary mod provider (modrinth, curseforge)
            fallback_mod_provider: Secondary mod provider
            curseforge_api_key: API key for CurseForge
        """
        self.config_file = config_file
        self.mod_directories = mod_directories or self.DEFAULT_CONFIG["mod_directories"]
        self.minecraft_version = minecraft_version
        self.mod_loader = mod_loader
        self.download_directory = download_directory
        self.ignore_mods = ignore_mods or self.DEFAULT_CONFIG["ignore_mods"]
        self.default_mod_provider = default_mod_provider
        self.fallback_mod_provider = fallback_mod_provider
        self.curseforge_api_key = curseforge_api_key
    
    @classmethod
    def load(cls, config_file: str = DEFAULT_CONFIG_FILE) -> 'Config':
        """
        Load configuration from file.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Config instance with loaded data or defaults
        """
        default_config = cls.DEFAULT_CONFIG.copy()
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    logging.info(f"Loaded configuration from {config_file}")
                    
                    # Validate and ensure all required fields exist
                    validated_config = default_config.copy()
                    validated_config.update({
                        k: v for k, v in config_data.items() 
                        if k in default_config
                    })
                    
                    # Special handling for lists to ensure they're the right type
                    if not isinstance(validated_config.get("mod_directories", []), list):
                        validated_config["mod_directories"] = default_config["mod_directories"]
                        
                    if not isinstance(validated_config.get("ignore_mods", []), list):
                        validated_config["ignore_mods"] = default_config["ignore_mods"]
                    
                    return cls(
                        config_file=config_file,
                        mod_directories=validated_config.get("mod_directories"),
                        minecraft_version=validated_config.get("minecraft_version"),
                        mod_loader=validated_config.get("mod_loader"),
                        download_directory=validated_config.get("download_directory"),
                        ignore_mods=validated_config.get("ignore_mods"),
                        default_mod_provider=validated_config.get("default_mod_provider"),
                        fallback_mod_provider=validated_config.get("fallback_mod_provider"),
                        curseforge_api_key=validated_config.get("curseforge_api_key")
                    )
            else:
                logging.warning(f"Configuration file {config_file} not found, using defaults")
                
                # Create a default config
                config = cls(config_file=config_file)
                
                # Ask if the user wants to set up interactively
                print(f"No configuration file found at: {config_file}")
                setup_choice = input("Would you like to set up configuration interactively? (Y/n): ").strip().lower()
                
                if setup_choice == "n":
                    # Create default config file
                    config.save()
                    print(f"Created default configuration file: {config_file}")
                    return config
                else:
                    # Interactive setup
                    return cls.create_interactive_config(config_file)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Error loading configuration: {str(e)}")
            return cls(config_file=config_file)
    
    def save(self) -> bool:
        """
        Save configuration to file.
        
        Returns:
            True if save was successful, False otherwise
        """
        try:
            config_data = {
                "mod_directories": self.mod_directories,
                "minecraft_version": self.minecraft_version,
                "mod_loader": self.mod_loader,
                "download_directory": self.download_directory,
                "ignore_mods": self.ignore_mods,
                "default_mod_provider": self.default_mod_provider,
                "fallback_mod_provider": self.fallback_mod_provider,
                "curseforge_api_key": self.curseforge_api_key
            }
            
            # Write to a temporary file first
            temp_file = f"{self.config_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            # Replace the original file with the temp file
            if os.path.exists(self.config_file):
                os.replace(temp_file, self.config_file)
            else:
                os.rename(temp_file, self.config_file)
                
            logging.info(f"Configuration saved to {self.config_file}")
            return True
        except IOError as e:
            logging.error(f"Error saving configuration: {str(e)}")
            return False
    
    def validate_mod_directories(self) -> List[str]:
        """
        Validate mod directories and return only those that exist.
        
        Returns:
            List of valid directory paths
        """
        valid_dirs = []
        
        for mod_dir in self.mod_directories:
            abs_path = os.path.abspath(mod_dir)
            if os.path.isdir(abs_path):
                valid_dirs.append(abs_path)
            else:
                logging.warning(f"Invalid mod directory: {abs_path}")
        
        if not valid_dirs:
            logging.warning("No valid mod directories found in configuration")
            
        return valid_dirs
    
    def get_absolute_download_directory(self) -> str:
        """
        Get the absolute path to the download directory.
        
        Returns:
            Absolute path to download directory
        """
        if os.path.isabs(self.download_directory):
            return self.download_directory
        
        # Make path absolute relative to script location
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(script_dir, self.download_directory)
    
    def create_download_directory(self) -> bool:
        """
        Create the download directory if it doesn't exist.
        
        Returns:
            True if directory exists or was created successfully, False otherwise
        """
        download_dir = self.get_absolute_download_directory()
        
        if os.path.exists(download_dir):
            return True
            
        try:
            os.makedirs(download_dir)
            logging.info(f"Created download directory: {download_dir}")
            return True
        except OSError as e:
            logging.error(f"Error creating download directory: {str(e)}")
            return False
    
    def get_normalized_mod_loader(self) -> str:
        """
        Get normalized mod loader name.
        
        Returns:
            Normalized mod loader name
        """
        loader = self.mod_loader.lower()
        
        if loader in ['fabric', 'forge', 'quilt']:
            return loader
        
        # Default to fabric if invalid
        logging.warning(f"Invalid mod loader: {loader}, defaulting to fabric")
        return 'fabric'
    
    @classmethod
    def create_interactive_config(cls, config_file: str = DEFAULT_CONFIG_FILE) -> 'Config':
        """
        Create a configuration interactively by prompting the user for input.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Config instance with user-provided values
        """
        print("\n==== Mod Update Checker Configuration Setup ====\n")
        print("Let's set up your configuration for checking mod updates.")
        
        # Get mod provider preference
        print("\nSelect your preferred mod provider:")
        print("1. Modrinth (default)")
        print("2. CurseForge")
        
        provider_input = input("Enter your choice (1-2): ").strip()
        default_mod_provider = "modrinth"  # Default
        fallback_mod_provider = "curseforge"
        
        if provider_input == "2":
            default_mod_provider = "curseforge"
            fallback_mod_provider = "modrinth"
        
        # Get CurseForge API key if needed
        curseforge_api_key = ""
        if default_mod_provider == "curseforge" or fallback_mod_provider == "curseforge":
            print("\nCurseForge API key is required to check for updates on CurseForge.")
            print("You can get an API key from https://console.curseforge.com/")
            curseforge_api_key = input("Enter your CurseForge API key (leave empty to skip CurseForge): ").strip()
        
        # Get mod directories
        mod_directories = []
        print("\nEnter the directories containing your mods.")
        print("You can add multiple directories. Enter an empty line when done.")
        print("(Default: ../mods)")
        
        i = 1
        while True:
            dir_input = input(f"Directory #{i} (or press Enter to finish): ").strip()
            if not dir_input:
                if not mod_directories:  # No directories added, use default
                    mod_directories = ["../mods"]
                    print(f"Using default directory: {mod_directories[0]}")
                break
                
            # Validate the directory exists
            abs_path = os.path.abspath(dir_input)
            if os.path.isdir(abs_path):
                mod_directories.append(abs_path)
                print(f"Added directory: {abs_path}")
                i += 1
            else:
                print(f"Warning: '{abs_path}' is not a valid directory. Please try again.")
        
        # Get Minecraft version
        default_version = "1.20.4"
        version_input = input(f"\nEnter the Minecraft version (default: {default_version}): ").strip()
        minecraft_version = version_input if version_input else default_version
        
        # Get mod loader
        print("\nSelect the mod loader:")
        print("1. Fabric (default)")
        print("2. Forge")
        print("3. Quilt")
        
        loader_input = input("Enter your choice (1-3): ").strip()
        mod_loader = "fabric"  # Default
        
        if loader_input == "2":
            mod_loader = "forge"
        elif loader_input == "3":
            mod_loader = "quilt"
        
        # Get download directory
        default_download_dir = "downloads"
        print("\nEnter the directory where updated mods should be downloaded.")
        print(f"(Default: {default_download_dir} - will be created in the script directory)")
        download_dir_input = input("Download directory: ").strip()
        
        download_directory = download_dir_input if download_dir_input else default_download_dir
        
        # Validate and normalize the download path
        if not os.path.isabs(download_directory):
            # Make relative path absolute relative to script location
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            download_directory = os.path.join(script_dir, download_directory)
        
        print(f"Download directory set to: {download_directory}")
        
        # Get ignore list
        ignore_mods = []
        print("\nOptionally, enter mod IDs to ignore when checking for updates.")
        print("You can add multiple mod IDs. Enter an empty line when done.")
        
        i = 1
        while True:
            mod_input = input(f"Mod ID #{i} to ignore (or press Enter to finish): ").strip()
            if not mod_input:
                break
                
            ignore_mods.append(mod_input)
            print(f"Will ignore mod: {mod_input}")
            i += 1
        
        # Create config
        config = cls(
            config_file=config_file,
            mod_directories=mod_directories,
            minecraft_version=minecraft_version,
            mod_loader=mod_loader,
            download_directory=download_directory,
            ignore_mods=ignore_mods,
            default_mod_provider=default_mod_provider,
            fallback_mod_provider=fallback_mod_provider,
            curseforge_api_key=curseforge_api_key
        )
        
        # Save config
        config.save()
        
        print(f"\nConfiguration saved to {config_file}")
        print("You can edit this file directly in the future to change settings.")
        
        return config

