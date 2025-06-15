import gspread
from oauth2client.service_account import ServiceAccountCredentials

def test_connection():
    print("Testing Google Sheets connection...")
    try:
        # Set up credentials
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
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

if __name__ == "__main__":
    test_connection() 