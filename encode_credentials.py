#!/usr/bin/env python3
"""
Script to properly encode GCP credentials for Streamlit secrets.
Run this script in the same directory as your credentials.json file.
"""

import json
import base64
import os

def encode_credentials():
    # Check if credentials.json exists
    if not os.path.exists("credentials.json"):
        print("❌ credentials.json not found in current directory")
        print("Please run this script in the same directory as your credentials.json file")
        return
    
    try:
        # Read the credentials file
        with open("credentials.json", "r") as f:
            creds_data = f.read()
        
        print(f"✅ Read credentials.json ({len(creds_data)} characters)")
        
        # Validate it's valid JSON
        try:
            json.loads(creds_data)
            print("✅ JSON validation successful")
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in credentials.json: {e}")
            return
        
        # Encode to base64
        encoded = base64.b64encode(creds_data.encode('utf-8')).decode('utf-8')
        print(f"✅ Base64 encoding successful ({len(encoded)} characters)")
        
        # Save to file
        with open("encoded_credentials.txt", "w") as f:
            f.write(encoded)
        
        print("\n🎉 Success!")
        print("📄 Encoded credentials saved to: encoded_credentials.txt")
        print("\n📋 Next steps:")
        print("1. Copy the ENTIRE content of encoded_credentials.txt")
        print("2. In your Streamlit Cloud app settings, set the secret:")
        print("   gcp_creds = \"paste-the-entire-encoded-string-here\"")
        print("3. Make sure you copy the COMPLETE string (no truncation)")
        
        # Show first/last chars for verification
        print(f"\n🔍 Verification:")
        print(f"First 50 chars: {encoded[:50]}")
        print(f"Last 50 chars:  {encoded[-50:]}")
        print(f"Total length: {len(encoded)} characters")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    encode_credentials() 