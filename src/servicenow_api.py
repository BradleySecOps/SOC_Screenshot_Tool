import requests
import json
import io
import base64
from tkinter import messagebox # Keep messagebox for error reporting

def get_auth(username, password):
    """Returns Basic Authentication tuple if credentials are provided."""
    return (username, password) if username and password else None

def get_ticket_sys_id(servicenow_url, username, password, ticket_number):
    """Looks up the sys_id and table name for a given INC or SIR number."""
    if not servicenow_url or not username or not password or not ticket_number:
        return None, None, "Error: ServiceNow not configured or ticket number missing."

    table = "incident" if ticket_number.upper().startswith("INC") else "sn_si_incident" if ticket_number.upper().startswith("SIR") else None
    if not table:
        return None, None, "Error: INC/SIR prefix needed."

    url = f"{servicenow_url}/api/now/table/{table}"
    headers = {"Accept": "application/json"}
    params = {"sysparm_query": f"number={ticket_number}", "sysparm_fields": "sys_id", "sysparm_limit": "1"}
    auth = get_auth(username, password)

    try:
        r = requests.get(url, headers=headers, params=params, auth=auth, timeout=10)
        r.raise_for_status()
        data = r.json()
        if results := data.get('result', []):
            sys_id = results[0].get('sys_id')
            return sys_id, table, f"Found: {ticket_number}"
        else:
            return None, None, f"Error: {ticket_number} not found."
    except Exception as e:
        print(f"SysID lookup error: {e}")
        return None, None, "Error: Lookup failed."

def upload_screenshot_to_servicenow(servicenow_url, username, password, table_name, table_sys_id, image, filename="screenshot.png"):
    """Uploads an image as an attachment to a ServiceNow ticket."""
    if not servicenow_url or not username or not password or not table_name or not table_sys_id or not image:
        return False, "Error: ServiceNow not configured, ticket info missing, or no image."

    api_url = f"{servicenow_url}/api/now/attachment/upload"
    auth = get_auth(username, password)
    headers = {"Accept": "application/json"}
    data_payload = {"table_name": table_name, "table_sys_id": table_sys_id}

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    files_payload = {'uploadFile': (filename, img_byte_arr, 'image/png')}

    try:
        r = requests.post(api_url, headers=headers, data=data_payload, files=files_payload, auth=auth, timeout=30)
        r.raise_for_status()
        return True, "Attachment upload successful."
    except Exception as e:
        print(f"SN Upload error: {e}")
        error_message = f"Failed attachment upload:\n{e}"
        messagebox.showerror("Upload Error", error_message) # Use messagebox for user feedback
        return False, error_message

def add_work_note_to_ticket(servicenow_url, username, password, table_name, table_sys_id, comment):
    """Adds a work note to the specified ServiceNow ticket."""
    if not servicenow_url or not username or not password or not table_name or not table_sys_id or not comment:
        return False, "Error: ServiceNow not configured, ticket info missing, or no comment."

    api_url = f"{servicenow_url}/api/now/table/{table_name}/{table_sys_id}"
    auth = get_auth(username, password)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    # Try using 'comments' field instead of 'work_notes'
    payload = json.dumps({"comments": comment})

    try:
        response = requests.patch(api_url, headers=headers, data=payload, auth=auth, timeout=15)
        response.raise_for_status()
        return True, "Comment added successfully."
    except requests.exceptions.RequestException as e:
        error_details = ""; status_code = e.response.status_code if e.response is not None else "N/A"
        try: error_details = e.response.json().get('error', {}).get('message', '') if e.response is not None else str(e)
        except: error_details = str(e)
        print(f"Error adding work note ({status_code}): {error_details}")
        error_message = f"Failed to add comment (HTTP {status_code}):\n{error_details}"
        messagebox.showerror("Comment Error", error_message) # Use messagebox for user feedback
        return False, error_message
    except Exception as e:
         print(f"Unexpected error adding work note: {e}")
         error_message = f"An unexpected error occurred adding comment:\n{e}"
         messagebox.showerror("Comment Error", error_message) # Use messagebox for user feedback
         return False, error_message