#!/usr/bin/env python3
"""
Script to download and update the current A2A specifications.
This should be run after fixing issues identified in spec analysis reports
to bump the baseline specification version.
"""

import argparse
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from spec_tracker.spec_downloader import SpecDownloader

logger = logging.getLogger(__name__)

def create_version_info(old_version: str = None, new_version: str = None) -> dict:
    """Create version info metadata."""
    return {
        "updated_at": datetime.now().isoformat(),
        "old_version": old_version,
        "new_version": new_version,
        "source": "GitHub A2A main branch"
    }

def backup_current_specs(current_spec_dir: Path, backup_dir: Path) -> bool:
    """Backup current specifications before updating."""
    try:
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy existing specs if they exist
        md_file = current_spec_dir / "A2A_SPECIFICATION.md"
        json_file = current_spec_dir / "a2a_schema.json"
        
        if md_file.exists():
            shutil.copy2(md_file, backup_dir / "A2A_SPECIFICATION.md")
            logger.info(f"✅ Backed up {md_file} to {backup_dir}")
        
        if json_file.exists():
            shutil.copy2(json_file, backup_dir / "a2a_schema.json")
            logger.info(f"✅ Backed up {json_file} to {backup_dir}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to backup current specs: {e}")
        return False

def update_current_specs(current_spec_dir: Path, 
                        json_data: dict, 
                        md_content: str,
                        version_info: dict) -> bool:
    """Update current specifications with new data."""
    try:
        current_spec_dir.mkdir(parents=True, exist_ok=True)
        
        # Write JSON schema
        json_file = current_spec_dir / "a2a_schema.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        logger.info(f"✅ Updated {json_file}")
        
        # Write Markdown specification
        md_file = current_spec_dir / "A2A_SPECIFICATION.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        logger.info(f"✅ Updated {md_file}")
        
        # Write version info
        version_file = current_spec_dir / "version_info.json"
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(version_info, f, indent=2)
        logger.info(f"✅ Created {version_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to update current specs: {e}")
        return False

def main():
    """Main entry point for updating current specifications."""
    parser = argparse.ArgumentParser(
        description="Download and update current A2A specifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Update with latest from GitHub
  %(prog)s --version "v1.2.0"                # Tag the update with version
  %(prog)s --backup-dir custom_backup        # Use custom backup directory
  %(prog)s --dry-run                         # Show what would be updated
        """
    )
    parser.add_argument(
        '--json-url',
        help='URL for JSON schema (default: GitHub main branch)',
        default=SpecDownloader.DEFAULT_JSON_URL
    )
    parser.add_argument(
        '--md-url', 
        help='URL for Markdown spec (default: GitHub main branch)',
        default=SpecDownloader.DEFAULT_MD_URL
    )
    parser.add_argument(
        '--current-spec-dir',
        help='Directory containing current specifications (default: current_spec)',
        default='current_spec',
        type=Path
    )
    parser.add_argument(
        '--backup-dir',
        help='Directory for backing up old specs (default: current_spec_backup)',
        default='current_spec_backup',
        type=Path
    )
    parser.add_argument(
        '--version',
        help='Version tag for this update (e.g., v1.2.0)'
    )
    parser.add_argument(
        '--old-version',
        help='Previous version tag (will try to read from existing version_info.json if not provided)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force update even if no changes detected'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        logger.info("🚀 Starting A2A Specification Update")
        
        # Read existing version info if available
        existing_version = None
        version_info_file = args.current_spec_dir / "version_info.json"
        if version_info_file.exists() and not args.old_version:
            try:
                with open(version_info_file, 'r') as f:
                    existing_info = json.load(f)
                    existing_version = existing_info.get('new_version')
                    logger.info(f"📋 Found existing version: {existing_version}")
            except Exception as e:
                logger.warning(f"⚠️  Could not read existing version info: {e}")
        
        old_version = args.old_version or existing_version or "unknown"
        
        # Step 1: Download latest specifications
        logger.info("📥 Downloading latest specifications...")
        downloader = SpecDownloader()
        
        try:
            new_json, new_md = downloader.download_spec(args.json_url, args.md_url)
            logger.info(f"✅ Downloaded: {len(new_json)} JSON definitions, {len(new_md)} chars markdown")
        except Exception as e:
            logger.error(f"❌ Failed to download specifications: {e}")
            return 1
        
        # Step 2: Check if there are changes (unless forced)
        if not args.force:
            current_md_file = args.current_spec_dir / "A2A_SPECIFICATION.md"
            current_json_file = args.current_spec_dir / "a2a_schema.json"
            
            changes_detected = False
            
            if current_md_file.exists():
                with open(current_md_file, 'r', encoding='utf-8') as f:
                    current_md = f.read()
                if current_md != new_md:
                    changes_detected = True
                    logger.info("📝 Markdown specification changes detected")
            else:
                changes_detected = True
                logger.info("📝 No existing markdown specification found")
            
            if current_json_file.exists():
                with open(current_json_file, 'r', encoding='utf-8') as f:
                    current_json = json.load(f)
                if current_json != new_json:
                    changes_detected = True
                    logger.info("🔧 JSON schema changes detected")
            else:
                changes_detected = True
                logger.info("🔧 No existing JSON schema found")
            
            if not changes_detected:
                logger.info("✅ No changes detected - specifications are up to date")
                if not args.dry_run:
                    return 0
        
        # Step 3: Create version info
        version_info = create_version_info(old_version, args.version or "latest")
        
        if args.dry_run:
            logger.info("🔍 DRY RUN - Would perform the following actions:")
            logger.info(f"  📦 Backup current specs to: {args.backup_dir}")
            logger.info(f"  📥 Update specifications in: {args.current_spec_dir}")
            logger.info(f"  🏷️  Version: {old_version} → {args.version or 'latest'}")
            logger.info(f"  📋 JSON definitions: {len(new_json)}")
            logger.info(f"  📄 Markdown content: {len(new_md)} characters")
            return 0
        
        # Step 4: Backup current specifications
        logger.info(f"📦 Backing up current specifications to {args.backup_dir}...")
        if not backup_current_specs(args.current_spec_dir, args.backup_dir):
            logger.error("❌ Backup failed - aborting update")
            return 1
        
        # Step 5: Update current specifications
        logger.info(f"📥 Updating current specifications in {args.current_spec_dir}...")
        if not update_current_specs(args.current_spec_dir, new_json, new_md, version_info):
            logger.error("❌ Update failed")
            return 1
        
        # Step 6: Success summary
        logger.info("🎉 Specification update completed successfully!")
        logger.info(f"📍 Version: {old_version} → {args.version or 'latest'}")
        logger.info(f"📂 Current specs: {args.current_spec_dir}")
        logger.info(f"💾 Backup saved: {args.backup_dir}")
        
        if args.version:
            logger.info(f"💡 Next steps:")
            logger.info(f"  1. Review changes in {args.current_spec_dir}")
            logger.info(f"  2. Run spec analysis to identify test impacts")
            logger.info(f"  3. Update tests as needed")
            logger.info(f"  4. Commit changes with version {args.version}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("🛑 Update cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit(main()) 