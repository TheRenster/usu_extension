"""
Script to download the accurate Utah counties SVG from Wikimedia Commons.
Run this script to get the CC0-licensed accurate SVG map.
"""
import urllib.request
import sys

url = "https://upload.wikimedia.org/wikipedia/commons/2/25/Utah_county_map%2C_cb_500k.svg"
output_file = "chat/static/chat/utah_counties_accurate.svg"

try:
    print(f"Downloading Utah counties SVG from Wikimedia Commons...")
    urllib.request.urlretrieve(url, output_file)
    print(f"Successfully downloaded to {output_file}")
    print("This SVG is CC0 (public domain) and contains accurate county boundaries.")
except Exception as e:
    print(f"Error downloading SVG: {e}")
    print("\nAlternative: You can manually download from:")
    print("https://commons.wikimedia.org/wiki/File:Utah_county_map,_cb_500k.svg")
    sys.exit(1)
