import streamlit as st
import pandas as pd
import io

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


# ============================================================
# CONFIG
# ============================================================

FOLDER_ID = "1gBVEsolVKjNcXJQez8JomJKL28t9XAt2"
FILE_NAME = "users.csv"

COLUMNS = ["Name", "Age", "City"]

SCOPES = [
    "https://www.googleapis.com/auth/drive"
]


# ============================================================
# GOOGLE DRIVE
# ============================================================

credentials = service_account.Credentials.from_service_account_info(
    st.secrets["google_service_account"],
    scopes=SCOPES
)

drive = build(
    "drive",
    "v3",
    credentials=credentials
)


# ============================================================
# FIND CSV
# ============================================================

def find_csv():

    result = drive.files().list(
        q=(
            f"name = '{FILE_NAME}' "
            f"and '{FOLDER_ID}' in parents "
            f"and trashed = false"
        ),
        spaces="drive",
        fields="files(id,name)"
    ).execute()

    files = result.get("files", [])

    if files:
        return files[0]["id"]

    return None


# ============================================================
# CREATE CSV
# ============================================================

def create_csv(row):

    df = pd.DataFrame(
        [row],
        columns=COLUMNS
    )

    output = io.BytesIO()

    df.to_csv(
        output,
        index=False
    )

    output.seek(0)

    media = MediaIoBaseUpload(
        output,
        mimetype="text/csv"
    )

    result = drive.files().create(
        body={
            "name": FILE_NAME,
            "parents": [FOLDER_ID]
        },
        media_body=media,
        fields="id"
    ).execute()

    return result["id"], df


# ============================================================
# APPEND CSV
# ============================================================

def append_csv(file_id, row):

    # Download
    request = drive.files().get_media(
        fileId=file_id
    )

    buffer = io.BytesIO()

    downloader = MediaIoBaseDownload(
        buffer,
        request
    )

    done = False

    while not done:

        _, done = downloader.next_chunk()

    buffer.seek(0)

    # Read
    df = pd.read_csv(buffer)

    # Append
    new_row = pd.DataFrame(
        [row],
        columns=COLUMNS
    )

    df = pd.concat(
        [df, new_row],
        ignore_index=True
    )

    # Upload
    output = io.BytesIO()

    df.to_csv(
        output,
        index=False
    )

    output.seek(0)

    media = MediaIoBaseUpload(
        output,
        mimetype="text/csv"
    )

    drive.files().update(
        fileId=file_id,
        media_body=media
    ).execute()

    return df


# ============================================================
# UI
# ============================================================

st.title("Google Drive CSV Test")

name = st.text_input("Name")

age = st.number_input(
    "Age",
    min_value=0,
    max_value=120,
    value=18
)

city = st.text_input("City")


if st.button("Add Record"):

    if not name or not city:

        st.warning("Enter Name and City.")

        st.stop()


    row = {
        "Name": name,
        "Age": age,
        "City": city
    }


    try:

        file_id = find_csv()


        # ----------------------------------------
        # CREATE
        # ----------------------------------------

        if file_id is None:

            file_id, df = create_csv(row)

            st.success(
                "CSV created successfully!"
            )


        # ----------------------------------------
        # APPEND
        # ----------------------------------------

        else:

            df = append_csv(
                file_id,
                row
            )

            st.success(
                "Record appended successfully!"
            )


        st.dataframe(
            df,
            use_container_width=True
        )


    except Exception as e:

        st.error(
            f"Error: {e}"
        )
