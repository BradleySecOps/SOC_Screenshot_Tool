import tkinter as tk
from tkinter import ttk, messagebox
import requests
import base64
import json

class ConfigWindow(tk.Toplevel):
    """Window for ServiceNow Configuration."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent # Reference to the main app window
        self.title("ServiceNow Configuration")
        self.geometry("450x200")
        self.transient(parent) # Keep window on top of parent
        self.grab_set() # Modal behavior

        self.url_var = tk.StringVar(value=parent.servicenow_url)
        self.user_var = tk.StringVar(value=parent.servicenow_user)
        # Password entry - not stored long-term

        ttk.Label(self, text="Instance URL (e.g., https://yourco.service-now.com):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(self, textvariable=self.url_var, width=50).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(self, text="Username:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(self, textvariable=self.user_var, width=30).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(self, text="Password (for verification only):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.pass_entry = ttk.Entry(self, show="*", width=30) # Use a direct Entry
        self.pass_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        self.status_label = ttk.Label(self, text="")
        self.status_label.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

        button_frame = ttk.Frame(self)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)

        verify_button = ttk.Button(button_frame, text="Verify & Save", command=self.verify_and_save)
        verify_button.pack(side=tk.LEFT, padx=5)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.destroy)
        cancel_button.pack(side=tk.LEFT, padx=5)

    def verify_and_save(self):
        """Verify credentials and save them to the parent app."""
        url = self.url_var.get().strip().rstrip('/')
        user = self.user_var.get().strip()
        password = self.pass_entry.get() # Get password directly from the entry widget

        if not url or not user or not password:
            self.status_label.config(text="Error: All fields are required.", foreground="red")
            return

        self.status_label.config(text="Verifying...", foreground="blue")
        self.update_idletasks() # Ensure label updates

        verify_url = f"{url}/api/now/table/sys_user?sysparm_query=user_name={user}&sysparm_limit=1&sysparm_fields=sys_id"
        auth = (user, password)
        headers = {"Accept": "application/json"}

        try:
            response = requests.get(verify_url, auth=auth, headers=headers, timeout=10)
            response.raise_for_status()
            try:
                data = response.json()
                if isinstance(data.get('result'), list) and len(data['result']) >= 0:
                     self.status_label.config(text="Verification Successful!", foreground="green")
                     self.parent.servicenow_url = url
                     self.parent.servicenow_user = user
                     # SECURITY NOTE: Password is NOT stored in the parent app.
                     # For actual API calls, the password would need to be re-entered
                     # or a more secure method (like API keys or OAuth) should be used.
                     self.parent.update_servicenow_status() # Update status based on URL/User only
                     self.after(1500, self.destroy) # Close after success
                else:
                     raise ValueError("Unexpected response format")
            except (json.JSONDecodeError, ValueError) as json_err:
                 print(f"ServiceNow verification JSON error: {json_err}")
                 self.status_label.config(text="Verification Failed: Unexpected response.", foreground="red")
        except requests.exceptions.HTTPError as http_err:
            print(f"ServiceNow verification HTTP error: {http_err}")
            status_code = http_err.response.status_code if http_err.response is not None else "N/A"
            if status_code == 401: self.status_label.config(text="Verification Failed: Invalid Credentials.", foreground="red")
            else: self.status_label.config(text=f"Verification Failed: HTTP {status_code}", foreground="red")
        except requests.exceptions.ConnectionError as conn_err:
            print(f"ServiceNow verification Connection error: {conn_err}")
            self.status_label.config(text="Verification Failed: Cannot connect.", foreground="red")
        except requests.exceptions.Timeout:
            print("ServiceNow verification Timeout error")
            self.status_label.config(text="Verification Failed: Timeout.", foreground="red")
        except requests.exceptions.RequestException as req_err:
            print(f"ServiceNow verification Request error: {req_err}")
            self.status_label.config(text="Verification Failed: Request Error.", foreground="red")
        except Exception as e:
             print(f"ServiceNow verification Unknown error: {e}")
             self.status_label.config(text="Verification Failed: Unknown Error.", foreground="red")