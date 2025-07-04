import gspread
import streamlit as st
from google.oauth2 import service_account

def test_connection():
    print("Testing Google Sheets connection...")
    try:
        # Set up credentials
        print("🔐 Loading credentials from Streamlit secrets...")
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
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