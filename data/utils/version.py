"""
Version comparison utilities for mod update checker.

This module provides utilities for parsing, normalizing, and comparing version strings
to determine if updates are available for mods.
"""

import re
import logging
from typing import List, Tuple, Optional, Union


class Version:
    """Class representing a parsed version."""
    
    def __init__(self, version_string: str):
        """
        Initialize a Version object.
        
        Args:
            version_string: Version string to parse
        """
        self.original = version_string
        self.normalized = normalize_version(version_string)
        
        # Parse the normalized version into components
        self.components = parse_version(self.normalized)
        
        # Extract pre-release and build info
        self.prerelease, self.build = extract_prerelease_and_build(self.normalized)
    
    def __str__(self) -> str:
        return self.original
    
    def __repr__(self) -> str:
        return f"Version('{self.original}')"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        
        return (self.components == other.components and
                self.prerelease == other.prerelease and
                self.build == other.build)
    
    def __lt__(self, other) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        
        # Compare the numeric components first
        if self.components != other.components:
            return self.components < other.components
        
        # If components are equal, a version with prerelease info is LESS than one without
        if self.prerelease and not other.prerelease:
            return True
        
        if not self.prerelease and other.prerelease:
            return False
        
        # If both have prerelease info, compare them
        if self.prerelease and other.prerelease:
            return self.prerelease < other.prerelease
        
        # If we get here, the versions are equal (ignoring build metadata)
        return False
    
    def __gt__(self, other) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        
        return other < self
    
    def __le__(self, other) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        
        return self < other or self == other
    
    def __ge__(self, other) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        
        return self > other or self == other


def normalize_version(version: str) -> str:
    """
    Normalize a version string for consistent comparison.
    
    Args:
        version: Version string to normalize
        
    Returns:
        Normalized version string
    """
    # Remove any 'v' prefix
    if version.lower().startswith('v'):
        version = version[1:]
    
    # Handle specific patterns:
    # MC version patterns like "MC1.19.2-1.0.0" -> "1.0.0"
    mc_pattern = re.search(r'MC\d+\.\d+(\.\d+)?-([0-9.]+)', version)
    if mc_pattern:
        version = mc_pattern.group(2)
    
    # Handle patterns like "mod-1.2.3" -> "1.2.3"
    dash_pattern = re.search(r'[a-zA-Z]+-(\d+\.\d+(\.\d+)?)', version)
    if dash_pattern:
        version = dash_pattern.group(1)
    
    # Trim whitespace
    version = version.strip()
    
    return version


def parse_version(version: str) -> List[int]:
    """
    Parse a version string into numeric components.
    
    Args:
        version: Normalized version string
        
    Returns:
        List of integer version components
    """
    # Split on non-numeric characters, but stop at prerelease or build indicators
    prerelease_index = version.find('-')
    build_index = version.find('+')
    
    # Find where to stop parsing numeric components
    end_index = len(version)
    if prerelease_index != -1:
        end_index = min(end_index, prerelease_index)
    if build_index != -1:
        end_index = min(end_index, build_index)
    
    # Extract and parse the numeric part
    numeric_part = version[:end_index]
    
    # Split on non-numeric characters
    version_parts = re.split(r'[^0-9]+', numeric_part)
    
    # Convert to integers, ignoring empty parts
    components = []
    for part in version_parts:
        if part:
            try:
                components.append(int(part))
            except ValueError:
                continue  # Skip non-numeric parts
    
    # If no components, add a 0 to avoid empty lists
    if not components:
        components = [0]
    
    return components


def extract_prerelease_and_build(version: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract prerelease and build metadata from a version string.
    
    Args:
        version: Normalized version string
        
    Returns:
        Tuple of (prerelease string or None, build string or None)
    """
    prerelease = None
    build = None
    
    # Check for semver style prerelease: 1.2.3-alpha.1
    prerelease_match = re.search(r'-([a-zA-Z0-9.-]+)(?:\+|$)', version)
    if prerelease_match:
        prerelease = prerelease_match.group(1)
    
    # Check for semver style build metadata: 1.2.3+build.5
    build_match = re.search(r'\+([a-zA-Z0-9.-]+)$', version)
    if build_match:
        build = build_match.group(1)
    
    # Also check for other common patterns:
    if not prerelease:
        # Check for patterns like "1.2.3_alpha1"
        alt_match = re.search(r'[._-](alpha|beta|pre|rc|snapshot)[._-]?(\d*)', version, re.IGNORECASE)
        if alt_match:
            type_str = alt_match.group(1).lower()
            num_str = alt_match.group(2) or '0'
            prerelease = f"{type_str}.{num_str}"
    
    return prerelease, build


def compare_versions(current_version: str, latest_version: str) -> bool:
    """
    Compare version strings to determine if an update is available.
    
    Args:
        current_version: Current version string
        latest_version: Latest version string
        
    Returns:
        True if an update is available, False otherwise
    """
    try:
        current = Version(current_version)
        latest = Version(latest_version)
        
        # If the latest version is greater than the current version, an update is available
        return latest > current
    except Exception as e:
        logging.warning(f"Error comparing versions {current_version} and {latest_version}: {str(e)}")
        
        # Fall back to simple string comparison if parsing fails
        return _simple_version_compare(current_version, latest_version)


def _simple_version_compare(current_version: str, latest_version: str) -> bool:
    """
    Simple fallback version comparison.
    
    Args:
        current_version: Current version string
        latest_version: Latest version string
        
    Returns:
        True if versions are different, False if they are the same
    """
    # Normalize both versions
    current = normalize_version(current_version)
    latest = normalize_version(latest_version)
    
    # If versions are the same, no update is needed
    if current == latest:
        return False
    
    # Try to extract numeric parts and compare
    try:
        current_parts = parse_version(current)
        latest_parts = parse_version(latest)
        
        # Compare each component
        for i in range(max(len(current_parts), len(latest_parts))):
            current_part = current_parts[i] if i < len(current_parts) else 0
            latest_part = latest_parts[i] if i < len(latest_parts) else 0
            
            if latest_part > current_part:
                return True
            elif latest_part < current_part:
                return False
        
        # All components are equal
        return False
    except Exception:
        # If parsing fails, just do a string comparison
        # This is very simplistic and might not be accurate
        return current != latest


def is_valid_version(version: str) -> bool:
    """
    Check if a string is a valid version.
    
    Args:
        version: Version string to validate
        
    Returns:
        True if the version is valid, False otherwise
    """
    if not version:
        return False
    
    normalized = normalize_version(version)
    
    # A valid version should have at least one numeric component
    return len(parse_version(normalized)) > 0 and any(c.isdigit() for c in normalized)

