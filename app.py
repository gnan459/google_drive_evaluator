import streamlit as st
import os
import pandas as pd
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Google Drive API scope
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']

# Path to your credentials.json (from Google Cloud Console)
CLIENT_SECRET_FILE = 'client_secret.json'

def authenticate_user():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    return creds

def list_subfolders(service, parent_folder_id):
    results = service.files().list(
        q=f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed = false",
        fields="files(id, name)").execute()
    return results.get('files', [])

def list_files_in_folder(service, folder_id):
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        fields="files(id, name, mimeType, modifiedTime, size)").execute()
    return results.get('files', [])

def main():
    st.set_page_config(page_title="Google Drive Student Evaluator", layout="wide")
    st.title("📂 Google Drive Student Evaluator")

    folder_id = st.text_input("Enter the Parent Folder ID (e.g., 'Students'):")

    if folder_id:
        try:
            creds = authenticate_user()
            service = build('drive', 'v3', credentials=creds)

            # List student folders
            st.info("Fetching student folders...")
            folders = list_subfolders(service, folder_id)

            if not folders:
                st.warning("No subfolders found under the given folder ID.")
                return

            folder_options = {f['name']: f['id'] for f in folders}
            student_name = st.selectbox("Select a student folder:", list(folder_options.keys()))

            if student_name:
                files = list_files_in_folder(service, folder_options[student_name])

                # Normalize file fields
                for f in files:
                    f.setdefault('size', 'N/A')
                    f.setdefault('modifiedTime', 'N/A')

                df = pd.DataFrame(files)

                # Keep and rename necessary columns
                df = df[['name', 'mimeType', 'modifiedTime', 'size']]
                df['modifiedTime'] = pd.to_datetime(df['modifiedTime'], errors='coerce').dt.tz_localize(None)
                df['size'] = df['size'].fillna('N/A')

                df.rename(columns={
                    'name': 'File Name',
                    'mimeType': 'File Type',
                    'modifiedTime': 'Last Modified',
                    'size': 'Size (bytes)'
                }, inplace=True)

                st.write(f"### 📄 Files in {student_name}")
                st.dataframe(df)

                # Export to Excel
                excel_path = f"{student_name}_files.xlsx"
                df.to_excel(excel_path, index=False, sheet_name='Files')

                with open(excel_path, "rb") as f:
                    st.download_button(
                        label="📥 Download Excel",
                        data=f,
                        file_name=excel_path,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

        except HttpError as error:
            st.error(f"An error occurred: {error}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

if __name__ == '__main__':
    main()
