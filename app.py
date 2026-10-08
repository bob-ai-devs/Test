import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build


# ============================================================
# CONFIGURATION
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

SHEET_ID = st.secrets["GOOGLE_SHEET_ID"]

SHEET_NAME = "Sheet1"


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
# APPEND DATA TO GOOGLE SHEET
# ============================================================

def append_row(name, age, city):

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
            range=f"{SHEET_NAME}!A:C",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        )
        .execute()
    )

    return result


# ============================================================
# STREAMLIT UI
# ============================================================

st.set_page_config(
    page_title="Google Sheets Data Entry",
    page_icon="📊",
    layout="centered"
)

st.title("📊 Google Sheets Data Entry")

st.write("Enter your details below.")


# ============================================================
# INPUT FIELDS
# ============================================================

name = st.text_input(
    "Name"
)

age = st.number_input(
    "Age",
    min_value=0,
    max_value=120,
    value=25,
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

        st.warning("Please enter your name.")

    elif not city.strip():

        st.warning("Please enter your city.")

    else:

        try:

            append_row(
                name.strip(),
                int(age),
                city.strip()
            )

            st.success(
                "Record added successfully!"
            )

        except Exception as e:

            st.error(
                f"Error: {e}"
            )
