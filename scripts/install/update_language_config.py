#!/usr/bin/env python3
"""
Helper script to update language configuration in config.ini
Called by install.sh during installation
PRESERVES ALL COMMENTS IN config.ini
"""
import sys
from pathlib import Path


def update_language_config(language: str) -> bool:
    """
    Update config.ini with the specified language while preserving all comments.
    
    Args:
        language: Language code ('fr' or 'en')
    
    Returns:
        True if successful, False otherwise
    """
    config_path = Path("config.ini")
    
    if not config_path.exists():
        print("❌ config.ini not found!")
        return False
    
    # Validate language
    if language not in ("fr", "en"):
        print(f"⚠️  Invalid language '{language}', defaulting to 'fr'")
        language = "fr"
    
    try:
        # Read entire file preserving comments
        with open(config_path, "r") as f:
            lines = f.readlines()
        
        # Find and update the language default line
        updated = False
        in_language_section = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Detect [language] section
            if stripped == "[language]":
                in_language_section = True
                continue
            
            # Detect next section
            if stripped.startswith("[") and stripped != "[language]":
                in_language_section = False
            
            # Update default = ... line in language section
            if in_language_section and stripped.startswith("default"):
                # Preserve indentation and comments
                parts = line.split("=")
                if len(parts) >= 2:
                    # Keep everything before = and any inline comments
                    prefix = parts[0]
                    # Check for inline comment
                    comment = ""
                    if "#" in parts[1]:
                        value_part, comment = parts[1].split("#", 1)
                        comment = " #" + comment.rstrip()
                    
                    lines[i] = f"{prefix}= {language}{comment}\n"
                    updated = True
                    break
        
        if not updated:
            print("⚠️  Could not find 'default' in [language] section")
            return False
        
        # Write back preserving all comments
        with open(config_path, "w") as f:
            f.writelines(lines)
        
        print(f"✅ config.ini updated: language = {language} (comments preserved)")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update config.ini: {e}")
        return False


def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: update_language_config.py <language>")
        print("  language: 'fr' or 'en'")
        sys.exit(1)
    
    language = sys.argv[1]
    success = update_language_config(language)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
