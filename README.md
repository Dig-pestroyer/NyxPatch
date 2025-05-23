# NyxPatcher

A command-line tool for checking and updating Minecraft mods from both Modrinth and CurseForge repositories. This tool helps server administrators and players keep their mods up to date across multiple mod directories.

## Features

- **Multi-Platform Support**: Checks for updates on both Modrinth and CurseForge
- **Smart Version Management**: Handles semantic versioning for accurate update detection
- **Mod Loader Support**: Works with Fabric, Forge, and Quilt mods
- **Automatic Mod Detection**: Extracts metadata from mod JAR files to identify mods
- **Version Filtering**: Ensures updates are compatible with your Minecraft version
- **Interactive Mode**: Select which mods to update with an easy-to-use interface
- **Batch Mode**: Option to automatically download all updates without prompts
- **Safe Downloads**: Uses temporary files and checksums for reliable downloads
- **Caching**: Stores information to reduce API calls and improve performance
- **Detailed Reporting**: Generates comprehensive update reports

## Requirements

- Python 3.7 or higher
- Internet connection
- CurseForge API key (only if using CurseForge as a provider)

## Installation

1. Clone this repository or download the source code:
   ```
   git clone https://github.com/yourusername/nyxpatcher.git
   cd nyxpatcher
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the tool:
   ```
   python -m nyxpatcher
   ```

## Configuration

On first run, the tool will guide you through an interactive setup process to create a configuration file. You can also manually create or edit the `config.json` file with the following options:

```json
{
    "mod_directories": ["../mods"],
    "minecraft_version": "1.20.4",
    "mod_loader": "fabric",
    "download_directory": "downloads",
    "ignore_mods": [],
    "default_mod_provider": "modrinth",
    "fallback_mod_provider": "curseforge",
    "curseforge_api_key": ""
}
```

### Configuration Options

| Option | Description |
|--------|-------------|
| `mod_directories` | List of directories containing mod files to check |
| `minecraft_version` | Target Minecraft version for compatibility (e.g., "1.20.4") |
| `mod_loader` | Mod loader type: "fabric", "forge", or "quilt" |
| `download_directory` | Directory where updated mods will be saved |
| `ignore_mods` | List of mod IDs to skip when checking for updates |
| `default_mod_provider` | Primary mod repository ("modrinth" or "curseforge") |
| `fallback_mod_provider` | Secondary mod repository to check if primary fails |
| `curseforge_api_key` | API key for CurseForge (required for CurseForge access) |

## Usage

### Basic Usage

Check for mod updates with interactive prompts:
```
python -m nyxpatcher
```

### Command-line Options

| Option | Description |
|--------|-------------|
| `--debug` | Enable detailed debug output |
| `--force` | Force update check, ignoring cache |
| `--dry-run` | Simulate update process without downloading |
| `--config FILE` | Specify custom config file (default: config.json) |
| `--no-interaction` | Run without interactive prompts |
| `--download-all` | Automatically download all available updates |

### Examples

Check for updates with default settings:
```
python -m nyxpatcher
```

Force refresh and automatically download all updates:
```
python -m nyxpatcher --force --download-all
```

Perform a dry run to see what would be updated:
```
python -m nyxpatcher --dry-run
```

Use a custom configuration file:
```
python -m nyxpatcher --config server_config.json
```

## Supported Mod Platforms

### Modrinth

[Modrinth](https://modrinth.com/) is an open-source mod platform for Minecraft with a focus on providing a clean, modern interface and a fair revenue sharing model for creators. NyxPatcher uses Modrinth's API to search for and download mod updates.

Key benefits of Modrinth:
- No API key required
- Fast and reliable API
- Usually provides direct download links
- Support for modern mod versions

### CurseForge

[CurseForge](https://www.curseforge.com/minecraft) is the largest and most established mod repository for Minecraft, hosting thousands of mods, resource packs, and other content. To use CurseForge with NyxPatcher, you'll need a CurseForge API key, which can be obtained from [https://console.curseforge.com/](https://console.curseforge.com/).

Key benefits of CurseForge:
- Largest collection of mods available
- Long history with extensive mod version archives
- Support for older Minecraft versions
- Detailed mod metadata

## How It Works

1. The tool scans your mod directories and extracts metadata from each mod
2. It checks mod repositories for newer versions compatible with your Minecraft version
3. A summary of available updates is displayed
4. In interactive mode, you can select which mods to update
5. Selected mod updates are downloaded to your configured download directory
6. A detailed report is generated showing all mod statuses

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
