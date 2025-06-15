import streamlit as st
import json
import base64

st.title("🔍 Secrets Debugging Tool")

st.write("This tool helps debug your Streamlit secrets configuration.")

# Check what secrets are available
st.subheader("Available Secrets")
if hasattr(st, 'secrets'):
    available_secrets = list(st.secrets.keys())
    st.write(f"Found {len(available_secrets)} secret(s):")
    for secret in available_secrets:
        st.write(f"- {secret}")
else:
    st.error("No secrets found")

# Check gcp_creds specifically
st.subheader("GCP Credentials Check")

if "gcp_creds" in st.secrets:
    st.success("✅ gcp_creds found in secrets")
    
    try:
        # Try to decode
        raw_secret = st.secrets["gcp_creds"]
        st.write(f"Raw secret type: {type(raw_secret)}")
        st.write(f"Raw secret length: {len(str(raw_secret))}")
        
        # Show first 100 characters
        st.code(f"First 100 chars: {str(raw_secret)[:100]}...")
        
        # Try base64 decode
        try:
            decoded = base64.b64decode(raw_secret)
            decoded_str = decoded.decode('utf-8')
            st.success("✅ Base64 decoding successful")
            st.write(f"Decoded length: {len(decoded_str)} characters")
            
            # Try JSON parse
            try:
                parsed_json = json.loads(decoded_str)
                st.success("✅ JSON parsing successful")
                st.write(f"JSON has {len(parsed_json)} keys:")
                for key in parsed_json.keys():
                    st.write(f"- {key}")
                    
                # Check for required fields
                required_fields = ["type", "project_id", "private_key_id", "private_key", "client_email"]
                missing_fields = [field for field in required_fields if field not in parsed_json]
                
                if missing_fields:
                    st.error(f"❌ Missing required fields: {missing_fields}")
                else:
                    st.success("✅ All required fields present")
                    
            except json.JSONDecodeError as e:
                st.error(f"❌ JSON parsing failed: {str(e)}")
                st.write("First 200 characters of decoded string:")
                st.code(decoded_str[:200])
                
        except Exception as e:
            st.error(f"❌ Base64 decoding failed: {str(e)}")
            
    except Exception as e:
        st.error(f"❌ Error accessing gcp_creds: {str(e)}")
        
elif hasattr(st.secrets, "gcp_service_account"):
    st.success("✅ gcp_service_account found in secrets")
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        st.write(f"Direct JSON has {len(creds_dict)} keys:")
        for key in creds_dict.keys():
            st.write(f"- {key}")
    except Exception as e:
        st.error(f"❌ Error accessing gcp_service_account: {str(e)}")
else:
    st.error("❌ No GCP credentials found (neither gcp_creds nor gcp_service_account)")

st.subheader("💡 Recommendations")
st.write("""
**If you're seeing JSON parsing errors:**

1. **Check your credentials file format** - Make sure it's a valid JSON file
2. **Re-encode your credentials** - Try this process:
   ```bash
   # In your terminal, navigate to where your credentials.json file is
   base64 -i credentials.json -o encoded_creds.txt
   ```
3. **Copy the entire encoded string** from encoded_creds.txt to your Streamlit secrets
4. **Alternative**: Store credentials directly as JSON in secrets (use gcp_service_account section)

**Common issues:**
- Incomplete base64 encoding
- Invalid JSON structure (missing quotes, commas, etc.)
- Wrong file format (not a service account JSON file)
""") 