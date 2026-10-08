import streamlit as st
import pandas as pd
import io
import time
import uuid
from datetime import datetime, timezone

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

FOLDER_ID = "1gBVEsolVKjNcXJQez8JomJKL28t9XAt2"

COLUMNS = [
    "Name",
    "Age",
    "City"
]

SCOPES = [
    "https://www.googleapis.com/auth/drive"
]

LOCK_TIMEOUT = 60
WAIT_TIMEOUT = 30
RETRY_INTERVAL = 1


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
        fields="files(id,name,createdTime)"
    ).execute()

    files = result.get("files", [])

    if files:
        return files[0]

    return None


# ============================================================
# ACQUIRE LOCK
# ============================================================

def acquire_lock():

    start = time.time()

    while True:

        lock = find_file(LOCK_FILE_NAME)

        # ----------------------------------------------------
        # NO LOCK
        # ----------------------------------------------------

        if lock is None:

            try:

                lock_text = str(uuid.uuid4())

                output = io.BytesIO(
                    lock_text.encode("utf-8")
                )

                media = MediaIoBaseUpload(
                    output,
                    mimetype="text/plain"
                )

                result = drive.files().create(
                    body={
                        "name": LOCK_FILE_NAME,
                        "parents": [FOLDER_ID]
                    },
                    media_body=media,
                    fields="id"
                ).execute()

                # Lock successfully created
                return result["id"]

            except Exception as e:

                # Another user may have created the lock
                time.sleep(RETRY_INTERVAL)


        # ----------------------------------------------------
        # LOCK EXISTS
        # ----------------------------------------------------

        else:

            created_time = lock.get("createdTime")

            if created_time:

                created = datetime.fromisoformat(
                    created_time.replace("Z", "+00:00")
                )

                age = (
                    datetime.now(timezone.utc) - created
                ).total_seconds()

                # Remove stale lock
                if age > LOCK_TIMEOUT:

                    try:

                        drive.files().delete(
                            fileId=lock["id"]
                        ).execute()

                    except Exception:
                        pass

                    continue


        # ----------------------------------------------------
        # WAIT TIMEOUT
        # ----------------------------------------------------

        if time.time() - start >= WAIT_TIMEOUT:

            return None

        time.sleep(RETRY_INTERVAL)


# ============================================================
# RELEASE LOCK
# ============================================================

def release_lock(lock_id):

    if lock_id:

        try:

            drive.files().delete(
                fileId=lock_id
            ).execute()

        except Exception:
            pass


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

        _, done = downloader.next_chunk()

    buffer.seek(0)

    return pd.read_csv(buffer)


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
        mimetype="text/csv"
    )

    drive.files().update(
        fileId=file_id,
        media_body=media
    ).execute()


# ============================================================
# STREAMLIT UI
# ============================================================

st.title("Google Drive CSV Updater")

name = st.text_input("Name")

age = st.number_input(
    "Age",
    min_value=0,
    max_value=120,
    value=18,
    step=1
)

city = st.text_input("City")


# ============================================================
# ADD RECORD
# ============================================================

if st.button("Add Record", type="primary"):

    if not name.strip():

        st.warning("Please enter Name.")
        st.stop()

    if not city.strip():

        st.warning("Please enter City.")
        st.stop()


    new_row = {
        "Name": name.strip(),
        "Age": age,
        "City": city.strip()
    }


    # --------------------------------------------------------
    # GET LOCK
    # --------------------------------------------------------

    with st.spinner("Preparing Google Drive..."):

        lock_id = acquire_lock()


    if lock_id is None:

        st.error(
            "The file is currently being updated by another user. "
            "Please try again."
        )

        st.stop()


    try:

        # ----------------------------------------------------
        # FIND CSV
        # ----------------------------------------------------

        existing_file = find_file(
            FILE_NAME
        )


        # ====================================================
        # CSV DOES NOT EXIST
        # ====================================================

        if existing_file is None:

            file_id, df = create_csv(
                new_row
            )

            st.success(
                "CSV created and record added successfully!"
            )


        # ====================================================
        # CSV EXISTS
        # ====================================================

        else:

            file_id = existing_file["id"]

            # Download latest version
            df = download_csv(
                file_id
            )

            # Ensure columns exist
            for column in COLUMNS:

                if column not in df.columns:

                    df[column] = ""

            df = df[COLUMNS]

            # Append row
            df.loc[len(df)] = new_row

            # Update Drive
            update_csv(
                file_id,
                df
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


    finally:

        # ----------------------------------------------------
        # ALWAYS RELEASE LOCK
        # ----------------------------------------------------

        release_lock(
            lock_id
        )
