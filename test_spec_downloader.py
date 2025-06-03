#!/usr/bin/env python3
"""
Test script for the spec downloader module.
"""

import logging
from spec_tracker.spec_downloader import SpecDownloader

# Setup logging to see the downloader activity
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def main():
    """Test the spec downloader functionality."""
    print("Testing A2A Specification Downloader...")
    
    try:
        # Create downloader instance
        downloader = SpecDownloader()
        
        # Download specs
        json_data, md_content = downloader.download_spec()
        
        # Verify downloads
        print(f"✅ Downloaded JSON with {len(json_data)} keys")
        print(f"✅ Downloaded MD with {len(md_content)} characters")
        
        # Show some sample data
        if 'definitions' in json_data:
            print(f"✅ JSON schema has {len(json_data['definitions'])} definitions")
        
        if md_content.startswith('#'):
            print("✅ Markdown content appears to be valid")
            
        print("\n🎉 Spec downloader test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main()) 