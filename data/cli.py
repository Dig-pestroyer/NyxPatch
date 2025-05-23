"""
Command-line interface for the mod update checker.
"""

import os
import sys
import argparse
import logging
from typing import List, Dict, Any, Optional

from data.config import Config
from data.cache.manager import ModCache
from data.checker import ModUpdateChecker
from data.utils.logging import setup_logging, get_logger


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Check Minecraft mods for updates",
        epilog="Use --help for more information."
    )
    
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug output"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Force update check, ignoring cache"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Simulate the update check and download process without performing actual downloads"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        default="config.json", 
        help="Path to configuration file (default: config.json)"
    )
    parser.add_argument(
        "--no-interaction", 
        action="store_true", 
        help="Run without interactive prompts, skipping downloads"
    )
    parser.add_argument(
        "--download-all", 
        action="store_true", 
        help="Automatically download all available updates without prompting"
    )
    
    return parser.parse_args()


def run() -> int:
    """
    Main entry point for the mod update checker.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Parse command-line arguments
    args = parse_args()
    
    # Setup logging
    setup_logging(debug_mode=args.debug)
    logger = get_logger(__name__)
    
    logger.info("Mod Update Checker starting...")
    
    try:
        # Load configuration
        config = Config.load(args.config)
        if not config:
            logger.error("Failed to load configuration")
            return 1
            
        # Initialize cache
        cache = ModCache.load()
        
        # Initialize checker
        checker = ModUpdateChecker(
            config=config,
            cache=cache,
            force_update=args.force
        )
        
        # Check for updates
        logger.info("Checking for updates...")
        updates = checker.check_updates()
        
        # Display results
        if updates:
            print(f"\nCheck complete: Found {len(updates)} mods with available updates")
            
            # Generate update report
            report_file = checker.write_update_report(updates)
            if report_file:
                print(f"Detailed report saved to: {report_file}")
            
            # Handle downloads
            if args.no_interaction:
                logger.info("Skipping downloads (--no-interaction specified)")
            elif args.download_all:
                logger.info("Automatically downloading all updates (--download-all specified)")
                checker.download_updates(updates, dry_run=args.dry_run)
            else:
                # Interactive download menu
                selected_updates = checker.interactive_download_menu(updates)
                if selected_updates:
                    checker.download_updates(selected_updates, dry_run=args.dry_run)
                else:
                    logger.info("No updates selected for download")
        else:
            print("\nCheck complete: All mods are up to date!")
        
        return 0
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        return 1


def main() -> None:
    """
    Entry point for the command-line script.
    """
    exit_code = run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

