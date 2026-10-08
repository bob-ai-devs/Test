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

SHEET_ID = st.secrets["GOOGLE_SHEET_ID"].strip()


# ============================================================
# GOOGLE SHEETS CONNECTION
# ============================================================

@st.cache_resource
def get_sheets_service():

    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=SCOPES
    )

    return build(
        "sheets",
        "v4",
        credentials=credentials
    )


sheets = get_sheets_service()


# ============================================================
# GET SPREADSHEET INFORMATION
# ============================================================

def get_spreadsheet():

    result = (
        sheets.spreadsheets()
        .get(
            spreadsheetId=SHEET_ID
        )
        .execute()
    )

    return result


# ============================================================
# GET FIRST TAB NAME
# ============================================================

def get_sheet_name():

    spreadsheet = get_spreadsheet()

    sheet_list = spreadsheet.get("sheets", [])

    if not sheet_list:
        raise Exception(
            "The spreadsheet does not contain any sheets."
        )

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
            range=f"'{sheet_name}'!A:C",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        )
        .execute()
    )

    return result


# ============================================================
# TITLE
# ============================================================

st.title("📊 Google Sheets Data Entry")


# ============================================================
# CONNECTION TEST
# ============================================================

st.subheader("Google Sheets Connection")

if st.button(
    "🔎 Test Google Sheet Connection",
    use_container_width=True
):

    try:

        spreadsheet = get_spreadsheet()

        spreadsheet_name = spreadsheet.get(
            "properties",
            {}
        ).get(
            "title",
            "Unknown"
        )

        sheet_list = spreadsheet.get(
            "sheets",
            []
        )

        st.success("✅ Google Sheet connection successful!")

        st.write(
            f"**Spreadsheet:** {spreadsheet_name}"
        )

        st.write(
            f"**Spreadsheet ID:** `{SHEET_ID}`"
        )

        st.write(
            "**Tabs:**"
        )

        for sheet in sheet_list:

            title = sheet["properties"]["title"]

            st.write(
                f"- {title}"
            )

    except Exception as e:

        st.error(
            f"❌ Connection Error: {e}"
        )


# ============================================================
# INPUT SECTION
# ============================================================

st.divider()

st.subheader("Enter Record")


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
# ADD RECORD
# ============================================================

if st.button(
    "➕ Add Record",
    type="primary",
    use_container_width=True
):

    if not name.strip():

        st.warning(
            "Please enter your name."
        )

    elif not city.strip():

        st.warning(
            "Please enter your city."
        )

    else:

        try:

            sheet_name = get_sheet_name()

            append_row(
                sheet_name,
                name.strip(),
                int(age),
                city.strip()
            )

            st.success(
                "✅ Record added successfully!"
            )

        except Exception as e:

            st.error(
                f"❌ Error: {e}"
            )
