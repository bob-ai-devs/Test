import streamlit as st

from google.oauth2 import service_account
from googleapiclient.discovery import build


# ==========================================
# CONFIG
# ==========================================

FOLDER_ID = "1gBVEsolVKjNcXJQez8JomJKL28t9XAt2"

SCOPES = [
    "https://www.googleapis.com/auth/drive"
]


# ==========================================
# GOOGLE DRIVE
# ==========================================

credentials = service_account.Credentials.from_service_account_info(
    st.secrets["google_service_account"],
    scopes=SCOPES
)

drive = build(
    "drive",
    "v3",
    credentials=credentials
)


st.title("Google Drive Test")


# ==========================================
# SHOW SERVICE ACCOUNT
# ==========================================

st.write(
    "Service account:"
)

st.code(
    st.secrets["google_service_account"]["client_email"]
)


# ==========================================
# TEST FOLDER
# ==========================================

try:

    folder = drive.files().get(
        fileId=FOLDER_ID,
        fields="id,name,mimeType"
    ).execute()

    st.success("Folder found!")

    st.write("Folder name:")
    st.write(folder["name"])

    st.write("Folder ID:")
    st.code(folder["id"])

    st.write("Type:")
    st.write(folder["mimeType"])


except Exception as e:

    st.error("Cannot access the folder")

    st.exception(e)


# ==========================================
# LIST FILES
# ==========================================

try:

    result = drive.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed = false",
        spaces="drive",
        fields="files(id,name,mimeType)"
    ).execute()

    files = result.get("files", [])

    st.write("Files visible to service account:")

    if files:

        for file in files:

            st.write(
                f"📄 {file['name']} — {file['id']}"
            )

    else:

        st.warning(
            "Folder is accessible, but no files are visible."
        )


except Exception as e:

    st.error("Cannot list folder contents")

    st.exception(e)
