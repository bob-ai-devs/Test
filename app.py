import streamlit as st
import pandas as pd
import io
import time
import uuid

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import (
    MediaIoBaseDownload,
    MediaIoBaseUpload
)


# ============================================================
# CONFIGURATION
# ============================================================

FILE_NAME = "users.csv"
LOCK_FILE_NAME = "users.csv.lock"

# Google Drive folder where the CSV should be stored
FOLDER_ID = "1gBVEsolVKjNcXJQez8JomJKL28t9XAt2"

# Columns in the CSV
COLUMNS = [
    "Name",
    "Age",
    "City"
]

SCOPES = [
    "https://www.googleapis.com/auth/drive"
]


# ============================================================
# GOOGLE DRIVE CONNECTION
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
# FIND FILE
# ============================================================

def find_file(file_name):

    query = (
        f"name = '{file_name}' "
        f"and '{FOLDER_ID}' in parents "
        f"and trashed = false"
    )

    result = drive.files().list(
        q=query,
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

def create_csv(first_row):

    df = pd.DataFrame(
        [first_row],
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
# DOWNLOAD CSV
# ============================================================

def download_csv(file_id):

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

        status, done = downloader.next_chunk()

    buffer.seek(0)

    return pd.read_csv(buffer)


# ============================================================
# UPDATE CSV
# ============================================================

def update_csv(file_id, df):

    output = io.BytesIO()

    df.to_csv(
        output,
        index=False
    )

    output.seek(0)

    media = MediaIoBaseUpload(
        output,
        mimetype="text/csv",
        resumable=True
    )

    drive.files().update(
        fileId=file_id,
        media_body=media
    ).execute()


# ============================================================
# CREATE LOCK
# ============================================================

def create_lock():

    lock_id = str(uuid.uuid4())

    output = io.BytesIO(
        lock_id.encode("utf-8")
    )

    media = MediaIoBaseUpload(
        output,
        mimetype="text/plain"
    )

    try:

        result = drive.files().create(
            body={
                "name": LOCK_FILE_NAME,
                "parents": [FOLDER_ID]
            },
            media_body=media,
            fields="id"
        ).execute()

        return result["id"]

    except Exception:

        return None


# ============================================================
# DELETE LOCK
# ============================================================

def delete_lock(lock_id):

    if lock_id:

        try:

            drive.files().delete(
                fileId=lock_id
            ).execute()

        except Exception:

            pass


# ============================================================
# WAIT FOR LOCK
# ============================================================

def acquire_lock(
    timeout=30,
    retry_interval=1
):

    start_time = time.time()

    while time.time() - start_time < timeout:

        # Check whether lock exists
        existing_lock = find_file(
            LOCK_FILE_NAME
        )

        if not existing_lock:

            # Try to create lock
            lock_id = create_lock()

            if lock_id:

                # Verify that our lock exists
                current_lock = find_file(
                    LOCK_FILE_NAME
                )

                if current_lock == lock_id:

                    return lock_id

                # Something unexpected happened
                delete_lock(lock_id)

        # Someone else currently has the lock
        time.sleep(retry_interval)

    return None


# ============================================================
# APP
# ============================================================

st.title("Google Drive CSV Updater")

st.write(
    "Enter the details below. "
    "The data will be saved directly to Google Drive."
)


# ============================================================
# INPUT
# ============================================================

name = st.text_input(
    "Name"
)

age = st.number_input(
    "Age",
    min_value=0,
    max_value=120,
    value=18,
    step=1
)

city = st.text_input(
    "City"
)


# ============================================================
# SUBMIT
# ============================================================

if st.button(
    "Add Record",
    type="primary"
):

    if not name.strip():

        st.warning(
            "Please enter a name."
        )

        st.stop()

    if not city.strip():

        st.warning(
            "Please enter a city."
        )

        st.stop()


    new_row = {
        "Name": name.strip(),
        "Age": age,
        "City": city.strip()
    }


    # --------------------------------------------------------
    # ACQUIRE LOCK
    # --------------------------------------------------------

    with st.spinner(
        "Waiting for database lock..."
    ):

        lock_id = acquire_lock(
            timeout=30,
            retry_interval=1
        )


    if not lock_id:

        st.error(
            "The file is currently being updated by another user. "
            "Please try again."
        )

        st.stop()


    try:

        # ====================================================
        # LOCK ACQUIRED
        # ====================================================

        st.info(
            "Updating Google Drive..."
        )


        # ----------------------------------------------------
        # CHECK IF CSV EXISTS
        # ----------------------------------------------------

        file_id = find_file(
            FILE_NAME
        )


        # ====================================================
        # CSV DOES NOT EXIST
        # ====================================================

        if not file_id:

            file_id, df = create_csv(
                new_row
            )

            st.success(
                "CSV did not exist. "
                "It was created and the record was added."
            )


        # ====================================================
        # CSV EXISTS
        # ====================================================

        else:

            # Download latest CSV
            df = download_csv(
                file_id
            )


            # ------------------------------------------------
            # Ensure expected columns exist
            # ------------------------------------------------

            for column in COLUMNS:

                if column not in df.columns:

                    df[column] = ""


            # Keep expected column order
            df = df[COLUMNS]


            # ------------------------------------------------
            # Append new record
            # ------------------------------------------------

            new_df = pd.DataFrame(
                [new_row],
                columns=COLUMNS
            )

            df = pd.concat(
                [
                    df,
                    new_df
                ],
                ignore_index=True
            )


            # ------------------------------------------------
            # Update Google Drive file
            # ------------------------------------------------

            update_csv(
                file_id,
                df
            )


            st.success(
                "Record appended successfully!"
            )


        # ====================================================
        # SHOW DATA
        # ====================================================

        st.dataframe(
            df,
            use_container_width=True
        )


    except Exception as e:

        st.error(
            f"Error updating CSV: {e}"
        )


    finally:

        # ====================================================
        # ALWAYS RELEASE LOCK
        # ====================================================

        delete_lock(
            lock_id
        )
