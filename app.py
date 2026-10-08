import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Google Sheets Data Entry",
    page_icon="📊",
    layout="centered"
)


# ============================================================
# CONFIGURATION
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

SHEET_ID = st.secrets["GOOGLE_SHEET_ID"]


# ============================================================
# GOOGLE SHEETS CONNECTION
# ============================================================

@st.cache_resource
def get_sheets_service():

    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=SCOPES
    )

    service = build(
        "sheets",
        "v4",
        credentials=credentials
    )

    return service


sheets = get_sheets_service()


# ============================================================
# GET FIRST SHEET / TAB NAME
# ============================================================

def get_sheet_name():

    spreadsheet = (
        sheets.spreadsheets()
        .get(
            spreadsheetId=SHEET_ID,
            fields="sheets.properties"
        )
        .execute()
    )

    sheet_list = spreadsheet.get("sheets", [])

    if not sheet_list:
        raise Exception("No sheets/tabs found in the Google Sheet.")

    return sheet_list[0]["properties"]["title"]


# ============================================================
# APPEND ROW
# ============================================================

def append_row(sheet_name, name, age, city):

    values = [
        [name, age, city]
    ]

    body = {
        "values": values
    }

    result = (
        sheets.spreadsheets()
        .values()
        .append(
            spreadsheetId=SHEET_ID,
            range=f"'{sheet_name}'!A1:C1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        )
        .execute()
    )

    return result


# ============================================================
# USER INTERFACE
# ============================================================

st.title("📊 Google Sheets Data Entry")

st.write(
    "Enter your details below. "
    "The record will be added as a new row in Google Sheets."
)


# ============================================================
# INPUT FIELDS
# ============================================================

name = st.text_input(
    "Name",
    placeholder="Enter your name"
)

age = st.number_input(
    "Age",
    min_value=0,
    max_value=120,
    value=25,
    step=1
)

city = st.text_input(
    "City",
    placeholder="Enter your city"
)


# ============================================================
# SUBMIT
# ============================================================

if st.button(
    "Add Record",
    type="primary",
    use_container_width=True
):

    if not name.strip():

        st.warning("Please enter your name.")

    elif not city.strip():

        st.warning("Please enter your city.")

    else:

        try:

            # Get actual tab name automatically
            sheet_name = get_sheet_name()

            # Append record
            append_row(
                sheet_name,
                name.strip(),
                int(age),
                city.strip()
            )

            st.success(
                "✅ Record added successfully!"
            )

            st.info(
                f"Data added to sheet tab: {sheet_name}"
            )

        except Exception as e:

            st.error(
                f"Error: {e}"
            )
