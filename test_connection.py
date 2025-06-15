import gspread
import streamlit as st
import json
import base64
from google.oauth2 import service_account

def test_connection():
    print("Testing Google Sheets connection...")
    try:
        # Set up credentials
        print("🔐 Loading credentials from Streamlit secrets...")
        try:
            # Method 1: Try direct JSON from secrets (if stored as JSON object)
            if hasattr(st.secrets, "gcp_service_account"):
                print("Using direct JSON credentials from gcp_service_account")
                creds_dict = dict(st.secrets["gcp_service_account"])
            # Method 2: Try base64 decoded string
            elif "gcp_creds" in st.secrets:
                print("Using base64 encoded credentials from gcp_creds")
                # Try to decode the base64 string
                try:
                    decoded_creds = base64.b64decode(st.secrets["gcp_creds"])
                    # Convert bytes to string
                    creds_str = decoded_creds.decode('utf-8')
                    print(f"Decoded credentials length: {len(creds_str)} characters")
                except Exception as e:
                    raise Exception(f"Failed to decode base64 credentials: {str(e)}")
                
                # Try to parse the JSON
                try:
                    creds_dict = json.loads(creds_str)
                    print("JSON parsing successful")
                except json.JSONDecodeError as e:
                    print(f"JSON parsing failed: {str(e)}")
                    print(f"First 200 chars of decoded string: {creds_str[:200]}")
                    raise Exception(f"Failed to parse JSON credentials: {str(e)}")
            else:
                raise Exception("Neither 'gcp_service_account' nor 'gcp_creds' found in Streamlit secrets")
            
            # Create credentials object
            creds = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
            )
        except Exception as e:
            raise Exception(f"Credential loading failed: {str(e)}")
        client = gspread.authorize(creds)
        
        # Try to open the sheet
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1VJ7Ox1MNVkWx4nTaVW4ifoYWcKb4eq7GovgpLNX4wfo/edit")
        worksheet = sheet.get_worksheet(0)
        
        # Try to read data
        data = worksheet.get_all_records()
        print("✅ Connection successful!")
        print(f"Found {len(data)} rows of data")
        print("\nFirst row of data:")
        if data:
            print(data[0])
        
    except Exception as e:
        print("❌ Connection failed!")
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    test_connection() 