"""
File handling utilities for mod update checker.

This module provides utilities for handling file operations related to mods,
including downloading, hash computation, metadata extraction, and path management.
"""

import os
import re
import shutil
import logging
import hashlib
import zipfile
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Tuple
from contextlib import contextmanager


# Constants
BUFFER_SIZE = 65536  # 64KB chunks for file reading
TEMP_SUFFIX = ".download.tmp"
BACKUP_SUFFIX = ".backup"
from data.__version__ import get_user_agent_string
USER_AGENT = get_user_agent_string()
MOD_EXTENSIONS = {".jar", ".zip"}
META_INF_PATH = "META-INF/mods.toml"
FABRIC_MOD_JSON = "fabric.mod.json"
FORGE_TOML = "META-INF/mods.toml"
QUILT_JSON = "quilt.mod.json"


def download_file(url: str, output_path: str, timeout: int = 30) -> bool:
    """
    Download a file from a URL to the specified path using temp files for safety.
    
    Args:
        url: URL to download from
        output_path: Path where the file should be saved
        timeout: Connection timeout in seconds
        
    Returns:
        True if download was successful, False otherwise
    """
    logger = logging.getLogger(__name__)
    temp_path = f"{output_path}{TEMP_SUFFIX}"
    
    # Ensure directory exists
    if not ensure_directory(os.path.dirname(output_path)):
        logger.error(f"Failed to create directory for {output_path}")
        return False
        
    try:
        # Set up request with proper headers
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT}
        )
        
        # Download to temp file first
        with urllib.request.urlopen(request, timeout=timeout) as response:
            with open(temp_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
                
        # Safely replace existing file if any
        if os.path.exists(output_path):
            backup_path = f"{output_path}{BACKUP_SUFFIX}"
            
            # Create backup first
            try:
                shutil.copy2(output_path, backup_path)
            except (IOError, OSError) as e:
                logger.warning(f"Failed to create backup of {output_path}: {e}")
                
            # Replace with atomic operation if possible
            try:
                os.replace(temp_path, output_path)
            except OSError:
                # Fallback if atomic replacement fails
                os.remove(output_path)
                os.rename(temp_path, output_path)
                
            # Remove backup if successful
            if os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                except OSError:
                    pass
        else:
            # No existing file, just rename
            os.rename(temp_path, output_path)
            
        logger.info(f"Successfully downloaded {url} to {output_path}")
        return True
        
    except urllib.error.URLError as e:
        logger.error(f"URL error downloading {url}: {e}")
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP error downloading {url}: {e.code} {e.reason}")
    except TimeoutError:
        logger.error(f"Connection timeout downloading {url}")
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {str(e)}")
    
    # Clean up temp file if download failed
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except OSError:
            pass
            
    return False


def compute_file_hash(file_path: str, algorithm: str = "sha1") -> Optional[str]:
    """
    Compute the hash of a file.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use (sha1, md5, etc.)
        
    Returns:
        Hexadecimal hash string or None if file doesn't exist/can't be read
    """
    if not os.path.isfile(file_path):
        return None
        
    try:
        if algorithm.lower() == "sha1":
            hash_obj = hashlib.sha1()
        elif algorithm.lower() == "md5":
            hash_obj = hashlib.md5()
        elif algorithm.lower() == "sha256":
            hash_obj = hashlib.sha256()
        else:
            hash_obj = hashlib.sha1()  # Default to SHA-1
            
        with open(file_path, 'rb') as f:
            # Read and update hash in chunks to handle large files
            for byte_block in iter(lambda: f.read(BUFFER_SIZE), b""):
                hash_obj.update(byte_block)
                
        return hash_obj.hexdigest()
        
    except IOError as e:
        logging.error(f"Error reading file for hash calculation: {e}")
        return None


def get_mod_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract metadata from a mod file.
    
    Args:
        file_path: Path to the mod file
        
    Returns:
        Dictionary containing metadata
    """
    logger = logging.getLogger(__name__)
    result = {
        "file_name": os.path.basename(file_path),
        "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
        "file_hash": compute_file_hash(file_path),
        "mod_id": None,
        "mod_name": None,
        "version": None,
        "mc_version": None,
        "mod_loader": None,
        "authors": None,
        "description": None
    }
    
    if not is_valid_mod_file(file_path):
        return result
        
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # Try to detect mod loader and extract metadata
            mod_info = None
            
            # Check for Fabric mod
            if FABRIC_MOD_JSON in zip_ref.namelist():
                with zip_ref.open(FABRIC_MOD_JSON) as f:
                    mod_info = json.load(f)
                result["mod_loader"] = "fabric"
                
                if mod_info:
                    result["mod_id"] = mod_info.get("id")
                    result["mod_name"] = mod_info.get("name")
                    result["version"] = mod_info.get("version")
                    result["description"] = mod_info.get("description")
                    
                    # Handle different author formats in fabric.mod.json
                    if "authors" in mod_info:
                        if isinstance(mod_info["authors"], list):
                            result["authors"] = ", ".join(mod_info["authors"])
                        else:
                            result["authors"] = str(mod_info["authors"])
                            
                    # Extract MC version from depends.minecraft
                    depends = mod_info.get("depends", {})
                    if isinstance(depends, dict) and "minecraft" in depends:
                        result["mc_version"] = depends["minecraft"]
            
            # Check for Forge mod
            elif FORGE_TOML in zip_ref.namelist():
                result["mod_loader"] = "forge"
                
                # Parse TOML file manually since toml module might not be available
                with zip_ref.open(FORGE_TOML) as f:
                    content = f.read().decode('utf-8', errors='ignore')
                    
                    # Extract mod_id
                    mod_id_match = re.search(r'modId\s*=\s*"([^"]+)"', content)
                    if mod_id_match:
                        result["mod_id"] = mod_id_match.group(1)
                        
                    # Extract name
                    name_match = re.search(r'displayName\s*=\s*"([^"]+)"', content)
                    if name_match:
                        result["mod_name"] = name_match.group(1)
                        
                    # Extract version
                    version_match = re.search(r'version\s*=\s*"([^"]+)"', content)
                    if version_match:
                        result["version"] = version_match.group(1)
                        
                    # Extract description
                    desc_match = re.search(r'description\s*=\s*"""(.*?)"""', content, re.DOTALL)
                    if desc_match:
                        result["description"] = desc_match.group(1).strip()
                    else:
                        # Try single-line description
                        desc_match = re.search(r'description\s*=\s*"([^"]+)"', content)
                        if desc_match:
                            result["description"] = desc_match.group(1)
                            
                    # Extract authors
                    authors_match = re.search(r'authors\s*=\s*"([^"]+)"', content)
                    if authors_match:
                        result["authors"] = authors_match.group(1)
                        
                    # Try to find MC version
                    mc_version_match = re.search(r'minecraft\s*=\s*\[\s*"([^"]+)"', content)
                    if mc_version_match:
                        result["mc_version"] = mc_version_match.group(1)
                        
            # Check for Quilt mod
            elif QUILT_JSON in zip_ref.namelist():
                with zip_ref.open(QUILT_JSON) as f:
                    mod_info = json.load(f)
                result["mod_loader"] = "quilt"
                
                if mod_info:
                    result["mod_id"] = mod_info.get("id")
                    result["mod_name"] = mod_info.get("name")
                    result["version"] = mod_info.get("version")
                    result["description"] = mod_info.get("description")
                    
                    # Handle authors
                    if "contributors" in mod_info:
                        authors = []
                        for role, names in mod_info["contributors"].items():
                            if isinstance(names, list):
                                authors.extend(names)
                            else:
                                authors.append(names)
                        result["authors"] = ", ".join(authors)
                        
                    # Extract MC version from depends.minecraft
                    depends = mod_info.get("depends", [])
                    for dep in depends:
                        if isinstance(dep, dict) and dep.get("id") == "minecraft":
                            result["mc_version"] = dep.get("versions", [])[0] if dep.get("versions") else None
                            break
            
            # If metadata extraction failed but the file exists, set defaults
            if not result["mod_id"] and result["file_name"]:
                # Use filename as fallback for mod_id
                base_name = os.path.splitext(result["file_name"])[0]
                result["mod_id"] = base_name
                
                if not result["mod_name"]:
                    result["mod_name"] = base_name
                
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning(f"Error extracting metadata from {file_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error processing {file_path}: {e}")
        
    return result


def ensure_directory(directory: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Path to the directory
        
    Returns:
        True if directory exists or was created successfully, False otherwise
    """
    if not directory:
        return False
        
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except OSError as e:
        logging.error(f"Error creating directory {directory}: {e}")
        return False


def is_valid_mod_file(file_path: str) -> bool:
    """
    Check if a file is a valid mod file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if file is a valid mod file, False otherwise
    """
    if not os.path.isfile(file_path):
        return False
        
    # Check file extension
    file_ext = os.path.splitext(file_path.lower())[1]
    if file_ext not in MOD_EXTENSIONS:
        return False
        
    # Check if file is a valid ZIP file (all mods are ZIP-based)
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # Check for mod identifier files
            file_list = zip_ref.namelist()
            return any(id_file in file_list for id_file in [
                FABRIC_MOD_JSON, 
                FORGE_TOML, 
                QUILT_JSON
            ])
    except zipfile.BadZipFile:
        return False
    except Exception as e:
        logging.error(f"Error validating mod file {file_path}: {e}")
        return False


def normalize_path(path: str) -> str:
    """
    Normalize a file path for consistent use across different operating systems.
    
    Args:
        path: File path to normalize
        
    Returns:
        Normalized path string
    """
    if not path:
        return ""
        
    # Convert to absolute path
    abs_path = os.path.abspath(path)
    
    # Use forward slashes for consistency
    norm_path = abs_path.replace('\\', '/')
    
    return norm_path


def find_mod_files(directory: str, recursive: bool = True) -> List[str]:
    """
    Find all mod files in a directory.
    
    Args:
        directory: Directory to search in
        recursive: Whether to search recursively
        
    Returns:
        List of paths to mod files
    """
    if not os.path.isdir(directory):
        return []
        
    mod_files = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if is_valid_mod_file(file_path):
                mod_files.append(file_path)
                
        if not recursive:
            break
            
    return mod_files


def check_file_permissions(file_path: str) -> Tuple[bool, bool, bool]:
    """
    Check read, write, and execute permissions for a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Tuple of (readable, writable, executable)
    """
    if not os.path.exists(file_path):
        return False, False, False
        
    readable = os.access(file_path, os.R_OK)
    writable = os.access(file_path, os.W_OK)
    executable = os.access(file_path, os.X_OK)
    
    return readable, writable, executable


def backup_file(file_path: str, backup_suffix: str = BACKUP_SUFFIX) -> Optional[str]:
    """
    Create a backup of a file.
    
    Args:
        file_path: Path to the file to backup
        backup_suffix: Suffix to append to the backup file name
        
    Returns:
        Path to the backup file or None if backup failed
    """
    if not os.path.isfile(file_path):
        return None
        
    backup_path = f"{file_path}{backup_suffix}"
    
    try:
        shutil.copy2(file_path, backup_path)
        return backup_path
    except (IOError, OSError) as e:
        logging.error(f"Failed to create backup of {file_path}: {e}")
        return None


def compare_files(file1: str, file2: str) -> bool:
    """
    Compare two files to check if they have the same content.
    
    Args:
        file1: Path to first file
        file2: Path to second file
        
    Returns:
        True if files have the same content, False otherwise
    """
    if not (os.path.isfile(file1) and os.path.isfile(file2)):
        return False
        
    # Quick check: if file sizes differ, files are different
    if os.path.getsize(file1) != os.path.getsize(file2):
        return False
        
    # Compare file hashes
    hash1 = compute_file_hash(file1)
    hash2 = compute_file_hash(file2)
    
    return hash1 == hash2


def safe_delete(file_path: str) -> bool:
    """
    Safely delete a file with error handling.
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        True if the file was deleted successfully, False otherwise
    """
    if not os.path.exists(file_path):
        return True  # File doesn't exist, so deletion "succeeded"
        
    try:
        os.remove(file_path)
        return True
    except OSError as e:
        logging.error(f"Error deleting file {file_path}: {e}")
        return False


@contextmanager
def atomic_write(file_path: str, mode: str = 'w', **kwargs) -> None:
    """
    Context manager for atomic file writes.
    
    Args:
        file_path: Path to the file to write
        mode: File open mode
        **kwargs: Additional arguments to pass to open()
    """
    temp_path = f"{file_path}{TEMP_SUFFIX}"
    
    # Ensure directory exists
    ensure_directory(os.path.dirname(file_path))
    
    try:
        # Write to temp file
        with open(temp_path, mode, **kwargs) as f:
            yield f
            
        # Atomic replace
        if os.path.exists(file_path):
            # Try atomic replacement
            try:
                os.replace(temp_path, file_path)
            except OSError:
                # Fallback to non-atomic replacement
                backup_path = backup_file(file_path)
                try:
                    os.remove(file_path)
                    os.rename(temp_path, file_path)
                except OSError as e:
                    # If rename fails and we have a backup, try to restore it
                    if backup_path and os.path.exists(backup_path):
                        try:
                            os.rename(backup_path, file_path)
                        except OSError:
                            pass  # Can't do much if this fails too
                    raise e
                
                # Clean up backup if everything succeeded
                if backup_path and os.path.exists(backup_path):
                    safe_delete(backup_path)
        else:
            # No existing file, just rename
            os.rename(temp_path, file_path)
    finally:
        # Clean up temp file if it still exists
        if os.path.exists(temp_path):
            safe_delete(temp_path)
