import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, scrolledtext
import os
import time
import copy

# Import refactored modules
from src import config_window
from src import servicenow_api
from src import screenshot_logic

class ScreenshotTool(tk.Tk):
    # --- Predefined Options ---
    # Moved to screenshot_logic.py, keep references if needed for UI config
    PREDEFINED_COLORS = screenshot_logic.PREDEFINED_COLORS
    PREDEFINED_SIZES = screenshot_logic.PREDEFINED_SIZES
    DEFAULT_COLOR_NAME = "Red"
    DEFAULT_SIZE_LABEL = "L"
    DEFAULT_RECT_WIDTH = screenshot_logic.DEFAULT_RECT_WIDTH

    def __init__(self):
        super().__init__()

        # Apply a modern theme
        style = ttk.Style(self)
        try:
            available_themes = style.theme_names()
            if 'clam' in available_themes: style.theme_use('clam')
            elif 'vista' in available_themes: style.theme_use('vista')
        except tk.TclError: print("ttk themes not available.")

        self.title("SOC Screenshot & Annotation Tool")
        self.geometry("950x850") # Increased height for comment box

        # --- State Variables ---
        self.screenshot_image = None
        self.modified_image = None
        self.screenshot_photo = [None] # Use a list to hold PhotoImage reference

        self.edit_mode = tk.StringVar(value="select")
        self.text_to_add = ""
        self.selected_color_name = tk.StringVar(value=self.DEFAULT_COLOR_NAME)
        self.selected_size_label = tk.StringVar(value=self.DEFAULT_SIZE_LABEL)
        self.current_annotation_color = self.PREDEFINED_COLORS[self.DEFAULT_COLOR_NAME]
        self.current_font_size = self.PREDEFINED_SIZES[self.DEFAULT_SIZE_LABEL]
        self.incident_folder_path = None
        self.annotations = []

        # ServiceNow State (Password is NOT stored here)
        self.servicenow_url = ""
        self.servicenow_user = ""
        # SECURITY NOTE: The ServiceNow password is NOT stored in this class.
        # It is only handled temporarily in the ConfigWindow for verification.
        # For actual API calls, a more secure method (like API keys or OAuth)
        # should be implemented, or the user would need to re-enter the password.
        self.servicenow_password_temp = None # Temporary storage for API calls if needed

        self.servicenow_configured = False
        self.target_ticket_number = tk.StringVar()
        self.target_ticket_sys_id = None
        self.target_table_name = None

        # History, Selection, Drawing, Overlay States...
        self.history = [copy.deepcopy(self.annotations)] # Initial state
        self.redo_stack = []
        self.selected_annotation_index = None
        self.selection_indicator_id = None
        self.drag_start_x_canvas = None
        self.drag_start_y_canvas = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.draw_start_x = None
        self.draw_start_y = None
        self.current_rect_id = None
        # Selection window/canvas state is now managed within screenshot_logic

        # --- UI Elements ---
        # Top Frame (Incident + ServiceNow Config)
        self.top_frame = ttk.Frame(self, padding="5 5 5 5")
        self.top_frame.pack(pady=(10, 5), padx=10, fill=tk.X)
        # Incident Controls
        self.incident_frame = ttk.Frame(self.top_frame)
        self.incident_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.new_incident_button = ttk.Button(self.incident_frame, text="New Incident (Local Folder)", command=self.create_new_incident)
        self.new_incident_button.pack(side=tk.LEFT, padx=5)
        ttk.Label(self.incident_frame, text="Local Folder:").pack(side=tk.LEFT, padx=(10, 0))
        self.incident_label = ttk.Label(self.incident_frame, text="None Set", foreground="grey", width=30)
        self.incident_label.pack(side=tk.LEFT, padx=(2, 5))
        # ServiceNow Controls
        self.servicenow_frame = ttk.Frame(self.top_frame)
        self.servicenow_frame.pack(side=tk.RIGHT)
        self.configure_sn_button = ttk.Button(self.servicenow_frame, text="Configure ServiceNow", command=self.open_config_window)
        self.configure_sn_button.pack(side=tk.LEFT, padx=5)
        self.sn_status_label = ttk.Label(self.servicenow_frame, text="Not Configured", foreground="red", width=15)
        self.sn_status_label.pack(side=tk.LEFT, padx=5)

        # Ticket Entry Frame
        self.ticket_frame = ttk.Frame(self, padding="5 0 5 0")
        self.ticket_frame.pack(pady=(0, 5), padx=10, fill=tk.X)
        ttk.Label(self.ticket_frame, text="Target INC/SIR #:").pack(side=tk.LEFT, padx=5)
        self.ticket_entry = ttk.Entry(self.ticket_frame, textvariable=self.target_ticket_number, width=20)
        self.ticket_entry.pack(side=tk.LEFT, padx=5)
        self.ticket_status_label = ttk.Label(self.ticket_frame, text="", width=40)
        self.ticket_status_label.pack(side=tk.LEFT, padx=5)

        # Comment Entry Frame
        self.comment_frame = ttk.Frame(self, padding="5 0 5 0")
        self.comment_frame.pack(pady=(0, 5), padx=10, fill=tk.X)
        ttk.Label(self.comment_frame, text="Comment/Work Note (for SN Upload):").pack(anchor="w")
        self.comment_text = scrolledtext.ScrolledText(self.comment_frame, height=4, width=80, wrap=tk.WORD)
        self.comment_text.pack(fill=tk.X, expand=True)

        # Annotation Controls Frame
        self.annotation_frame = ttk.Frame(self, padding="5 5 5 5")
        self.annotation_frame.pack(pady=(0,10), padx=10, fill=tk.X)
        self.select_area_button = ttk.Button(self.annotation_frame, text="Select Area", command=self.start_region_selection)
        self.select_area_button.pack(side=tk.LEFT, padx=5)
        ttk.Label(self.annotation_frame, text="Mode:").pack(side=tk.LEFT, padx=(15, 2))
        ttk.Radiobutton(self.annotation_frame, text="Select", variable=self.edit_mode, value="select", command=self.update_bindings).pack(side=tk.LEFT)
        ttk.Radiobutton(self.annotation_frame, text="Text", variable=self.edit_mode, value="text", command=self.update_bindings).pack(side=tk.LEFT)
        ttk.Radiobutton(self.annotation_frame, text="Rectangle", variable=self.edit_mode, value="rectangle", command=self.update_bindings).pack(side=tk.LEFT)
        ttk.Label(self.annotation_frame, text="Color:").pack(side=tk.LEFT, padx=(15, 2))
        self.color_combobox = ttk.Combobox(self.annotation_frame, textvariable=self.selected_color_name, values=list(self.PREDEFINED_COLORS.keys()), state="readonly", width=10)
        self.color_combobox.pack(side=tk.LEFT, padx=(0, 10))
        self.color_combobox.bind("<<ComboboxSelected>>", self.update_color_state)
        ttk.Label(self.annotation_frame, text="Size:").pack(side=tk.LEFT)
        self.size_combobox = ttk.Combobox(self.annotation_frame, textvariable=self.selected_size_label, values=list(self.PREDEFINED_SIZES.keys()), state="readonly", width=5)
        self.size_combobox.pack(side=tk.LEFT, padx=(2, 10))
        self.size_combobox.bind("<<ComboboxSelected>>", self.update_size_state)
        self.text_entry = ttk.Entry(self.annotation_frame, width=25)
        self.text_entry.pack(side=tk.LEFT, padx=5)
        self.text_entry.bind("<KeyRelease>", self.update_text_variable)
        self.text_entry.insert(0, "Enter text here...")
        self.text_entry.bind("<FocusIn>", self.clear_placeholder)
        self.text_entry.bind("<FocusOut>", self.add_placeholder)
        self.redo_button = ttk.Button(self.annotation_frame, text="Redo", command=self.redo_action, state=tk.DISABLED)
        self.redo_button.pack(side=tk.RIGHT, padx=(0, 5))
        self.undo_button = ttk.Button(self.annotation_frame, text="Undo", command=self.undo_action, state=tk.DISABLED)
        self.undo_button.pack(side=tk.RIGHT, padx=(0, 5))
        self.save_button = ttk.Button(self.annotation_frame, text="Save", command=self.save_screenshot, state=tk.DISABLED)
        self.save_button.pack(side=tk.RIGHT, padx=5)

        # Main Canvas
        self.canvas = tk.Canvas(self, bg="lightgrey", cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        # Status Bar
        self.status_bar = ttk.Label(self, text="Ready. Click 'Select Area' to start.", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.after(10, self.update_bindings)

    # --- ServiceNow Config Window ---
    def open_config_window(self):
        # Pass self to the ConfigWindow so it can update servicenow_url and servicenow_user
        config_window.ConfigWindow(self)

    def update_servicenow_status(self):
        # Password is not stored, so check only URL and User
        if self.servicenow_url and self.servicenow_user:
            self.servicenow_configured = True
            self.sn_status_label.config(text="Configured", foreground="green")
            self.save_button.config(text="Upload to SN")
        else:
            self.servicenow_configured = False
            self.sn_status_label.config(text="Not Configured", foreground="red")
            self.save_button.config(text="Save")

    # --- Placeholder Logic ---
    def clear_placeholder(self, event=None):
        if self.text_entry.get() == "Enter text here...":
            self.text_entry.delete(0, tk.END)
            self.text_entry.config(foreground="black")

    def add_placeholder(self, event=None):
        if not self.text_entry.get():
            self.text_entry.insert(0, "Enter text here...")
            self.text_entry.config(foreground="grey")

    # --- Customization State Updates ---
    def update_color_state(self, event=None):
        name = self.selected_color_name.get()
        self.current_annotation_color = screenshot_logic.PREDEFINED_COLORS.get(name, "#000000")
        self.update_status(f"Color: {name}")

    def update_size_state(self, event=None):
        label = self.selected_size_label.get()
        self.current_font_size = screenshot_logic.PREDEFINED_SIZES.get(label, 18)
        self.update_status(f"Size: {label}")

    # --- Mode and Binding Management ---
    def update_bindings(self):
        # Unbind all previous bindings
        self.canvas.unbind("<Button-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")

        self.update_text_variable()
        self.clear_selection_indicator()
        self.selected_annotation_index = None

        mode = self.edit_mode.get()
        if mode == "text":
            self.canvas.config(cursor="xterm")
            self.canvas.bind("<Button-1>", self.on_canvas_click_text)
            self.update_status("Text Mode")
        elif mode == "rectangle":
            self.canvas.config(cursor="crosshair")
            self.canvas.bind("<Button-1>", self.on_canvas_press_rect)
            self.canvas.bind("<B1-Motion>", self.on_canvas_drag_rect)
            self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release_rect)
            self.update_status("Rectangle Mode")
        else: # select mode
            self.canvas.config(cursor="arrow")
            self.canvas.bind("<Button-1>", self.on_canvas_click_select)
            self.update_status("Select Mode")

    def update_status(self, message):
        self.status_bar.config(text=message)

    def update_text_variable(self, event=None):
        self.text_to_add = self.text_entry.get() if self.text_entry.get() != "Enter text here..." else ""

    # --- Incident Management (Local Folder) ---
    def create_new_incident(self):
        name = simpledialog.askstring("New Local Folder", "Enter Name:", parent=self)
        if not name:
            self.update_status("Cancelled.")
            return
        safe_name = "".join(c for c in name if c.isalnum() or c in ('-', '_')).strip()
        if not safe_name:
            messagebox.showerror("Invalid", "Invalid name.", parent=self)
            self.update_status("Invalid name.")
            return
        path = os.path.join(os.getcwd(), safe_name)
        try:
            os.makedirs(path, exist_ok=True)
            self.incident_folder_path = path
            self.incident_label.config(text=path, foreground="black")
            self.update_status(f"Local folder: {safe_name}")
        except OSError as e:
            messagebox.showerror("Error", f"Failed: {e}", parent=self)
            self.update_status("Folder error.")
            self.incident_folder_path = None
            self.incident_label.config(text="None Set", foreground="grey")

    # --- Region Selection ---
    def start_region_selection(self):
        self.update_status("Selecting area...")
        # Pass a callback function to screenshot_logic
        screenshot_logic.start_region_selection(self, self.on_region_captured)

    def on_region_captured(self, screenshot_image, status_message):
        """Callback function executed after a region is captured."""
        self.screenshot_image = screenshot_image
        if self.screenshot_image:
            self.modified_image = self.screenshot_image.copy()
            self.annotations = []
            self.history = [copy.deepcopy(self.annotations)] # Save initial state
            self.redo_stack = []
            self.clear_selection_indicator()
            self.selected_annotation_index = None
            self.update_undo_redo_buttons()
            self.redraw_canvas()
            self.save_button.config(state=tk.NORMAL)
            self.edit_mode.set("select")
            self.update_bindings()
        self.update_status(status_message)

    # --- Image Display & Coordinate Conversion ---
    def display_screenshot(self):
        # Use the function from screenshot_logic
        self.screenshot_photo[0] = screenshot_logic.display_image_on_canvas(self.canvas, self.modified_image, self.screenshot_photo)
        self.redraw_selection_indicator()

    def canvas_to_image_coords(self, cx, cy):
        # Use the function from screenshot_logic
        return screenshot_logic.canvas_to_image_coords(self.canvas, self.screenshot_image, self.screenshot_photo[0], cx, cy)

    def image_to_canvas_coords(self, ix, iy):
        # Use the function from screenshot_logic
        return screenshot_logic.image_to_canvas_coords(self.canvas, self.screenshot_image, self.screenshot_photo[0], ix, iy)

    # --- Annotation Helpers & Drawing ---
    def get_annotation_bbox(self, ann):
        # Use the function from screenshot_logic
        return screenshot_logic.get_annotation_bbox(ann)

    def on_canvas_click_text(self, event):
        self.update_text_variable()
        ix, iy = self.canvas_to_image_coords(event.x, event.y)
        if ix is None:
            self.update_status("Clicked outside image.")
            return

        # Use the function from screenshot_logic
        new_annotations, status_message = screenshot_logic.add_text_annotation(
            self.screenshot_image, self.annotations, ix, iy, self.text_to_add,
            self.current_annotation_color, self.current_font_size
        )
        if new_annotations != self.annotations: # Check if annotation was actually added
            self.save_state_for_undo()
            self.annotations = new_annotations
            self.redraw_canvas()
            self.edit_mode.set("select")
            self.update_bindings()
        self.update_status(status_message)


    def on_canvas_press_rect(self, event):
        if not self.screenshot_image:
            self.update_status("Select area first.")
            return
        self.draw_start_x, self.draw_start_y = event.x, event.y
        if self.current_rect_id:
            self.canvas.delete(self.current_rect_id)
        self.current_rect_id = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline=self.current_annotation_color, width=self.DEFAULT_RECT_WIDTH
        )

    def on_canvas_drag_rect(self, event):
        if self.current_rect_id:
            self.canvas.coords(self.current_rect_id, self.draw_start_x, self.draw_start_y, event.x, event.y)

    def on_canvas_release_rect(self, event):
        if not self.current_rect_id:
            return
        self.canvas.delete(self.current_rect_id)
        self.current_rect_id = None

        sx, sy = self.canvas_to_image_coords(self.draw_start_x, self.draw_start_y)
        ex, ey = self.canvas_to_image_coords(event.x, event.y)
        self.draw_start_x, self.draw_start_y = None, None

        if sx is None or ex is None:
            self.update_status("Rect outside image.")
            return

        # Use the function from screenshot_logic
        new_annotations, status_message = screenshot_logic.add_rectangle_annotation(
            self.screenshot_image, self.annotations, sx, sy, ex, ey,
            self.current_annotation_color, self.DEFAULT_RECT_WIDTH
        )
        if new_annotations != self.annotations: # Check if annotation was actually added
            self.save_state_for_undo()
            self.annotations = new_annotations
            self.redraw_canvas()
        self.update_status(status_message)

    # --- Selection Handling ---
    def clear_selection_indicator(self):
         if self.selection_indicator_id:
             self.canvas.delete(self.selection_indicator_id)
             self.selection_indicator_id = None

    def redraw_selection_indicator(self):
         self.clear_selection_indicator()
         if self.selected_annotation_index is not None and self.selected_annotation_index < len(self.annotations):
            ann = self.annotations[self.selected_annotation_index]
            bbox = self.get_annotation_bbox(ann)
            if bbox:
                cx1, cy1 = self.image_to_canvas_coords(bbox[0], bbox[1])
                cx2, cy2 = self.image_to_canvas_coords(bbox[2], bbox[3])
                if cx1 is not None:
                    self.selection_indicator_id = self.canvas.create_rectangle(
                        cx1-2, cy1-2, cx2+2, cy2+2, outline="blue", dash=(4, 2), width=1
                    )

    def on_canvas_click_select(self, event):
        ix, iy = self.canvas_to_image_coords(event.x, event.y)
        self.clear_selection_indicator()
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        self.drag_start_x_canvas = None
        self.drag_start_y_canvas = None
        self.selected_annotation_index = None

        if ix is None:
            self.update_status("Selection cleared.")
            return

        # Use the function from screenshot_logic
        found_idx = screenshot_logic.find_annotation_at_coords(self.annotations, ix, iy)

        if found_idx is not None:
            self.selected_annotation_index = found_idx
            self.redraw_selection_indicator()
            if self.selection_indicator_id:
                ann = self.annotations[found_idx]
                self.update_status(f"Selected {ann['type']}. Drag to move.")
                self.drag_start_x_canvas, self.drag_start_y_canvas = event.x, event.y
                # Calculate offset based on annotation type
                if ann['type'] == 'text':
                    ox, oy = ann['x'], ann['y']
                elif ann['type'] == 'rectangle':
                    ox, oy = min(ann['x1'], ann['x2']), min(ann['y1'], ann['y2'])
                else:
                    ox, oy = ix, iy # Default to click point if type is unknown

                self.drag_offset_x, self.drag_offset_y = ix - ox, iy - oy
                self.canvas.bind("<B1-Motion>", self.on_canvas_drag_selected)
                self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release_selected)
            else:
                self.selected_annotation_index = None
                self.update_status("Select indicator error.")
        else:
            self.update_status("Clicked empty area.")

    def on_canvas_drag_selected(self, event):
        if self.selected_annotation_index is None or self.drag_start_x_canvas is None:
            return

        ix, iy = self.canvas_to_image_coords(event.x, event.y)
        if ix is None:
            return

        new_ox, new_oy = ix - self.drag_offset_x, iy - self.drag_offset_y

        # Use the function from screenshot_logic
        try:
            self.annotations = screenshot_logic.move_annotation(self.annotations, self.selected_annotation_index, new_ox, new_oy)
            self.redraw_canvas()
        except IndexError:
            self.clear_selection_indicator()
            self.selected_annotation_index = None
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")


    def on_canvas_release_selected(self, event):
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        if self.selected_annotation_index is None:
            return

        if self.drag_start_x_canvas is not None and self.selected_annotation_index < len(self.annotations):
            self.save_state_for_undo() # Save state after successful drag
            self.update_status("Move complete.")
        elif self.selected_annotation_index is not None and self.selected_annotation_index >= len(self.annotations):
             self.update_status("Move error."); self.clear_selection_indicator(); self.selected_annotation_index = None

        self.drag_start_x_canvas = None
        self.drag_start_y_canvas = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0


    # --- Annotation Drawing ---
    def redraw_canvas(self):
        # Use the function from screenshot_logic
        self.modified_image = screenshot_logic.redraw_image_with_annotations(self.screenshot_image, self.annotations)
        self.display_screenshot()

    # --- Undo/Redo Functionality ---
    def save_state_for_undo(self, is_initial_state=False):
        # Use the function from screenshot_logic
        self.history, self.redo_stack = screenshot_logic.save_state_for_undo(
            self.history, self.redo_stack, self.annotations, is_initial_state
        )
        self.update_undo_redo_buttons()

    def update_undo_redo_buttons(self):
        self.undo_button.config(state=tk.NORMAL if len(self.history) > 1 else tk.DISABLED)
        self.redo_button.config(state=tk.NORMAL if self.redo_stack else tk.DISABLED)

    def undo_action(self):
        # Use the function from screenshot_logic
        self.history, self.redo_stack, self.annotations, status_message = screenshot_logic.undo_action(
            self.history, self.redo_stack, self.annotations
        )
        self.clear_selection_indicator()
        self.selected_annotation_index = None
        self.redraw_canvas()
        self.update_undo_redo_buttons()
        self.update_status(status_message)

    def redo_action(self):
        # Use the function from screenshot_logic
        self.history, self.redo_stack, self.annotations, status_message = screenshot_logic.redo_action(
            self.history, self.redo_stack, self.annotations
        )
        self.clear_selection_indicator()
        self.selected_annotation_index = None
        self.redraw_canvas()
        self.update_undo_redo_buttons()
        self.update_status(status_message)

    # --- Save Functionality ---
    def save_screenshot(self):
        if not self.screenshot_image:
            messagebox.showwarning("No Image", "Select area first.", parent=self)
            return
        self.redraw_canvas()
        if not self.modified_image:
            messagebox.showerror("Error", "Failed to prepare image.", parent=self)
            return

        # --- ServiceNow Upload Path ---
        if self.servicenow_configured:
            ticket_number = self.target_ticket_number.get().strip()
            if not ticket_number:
                messagebox.showwarning("Missing Ticket", "Enter target INC/SIR #.", parent=self)
                return

            # Prompt for password before API call (more secure than storing)
            password = simpledialog.askstring("ServiceNow Password", "Enter your ServiceNow password:", show='*', parent=self)
            if not password:
                self.update_status("ServiceNow upload cancelled (password not provided).")
                return

            # Use the function from servicenow_api
            sys_id, table, status_message = servicenow_api.get_ticket_sys_id(
                self.servicenow_url, self.servicenow_user, password, ticket_number
            )
            self.ticket_status_label.config(text=status_message, foreground="green" if sys_id else "red") # Update ticket status label

            if sys_id and table:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{ticket_number}_{timestamp}.png"

                # Use the function from servicenow_api
                upload_success, upload_status_message = servicenow_api.upload_screenshot_to_servicenow(
                    self.servicenow_url, self.servicenow_user, password, table, sys_id, self.modified_image, filename
                )
                self.update_status(upload_status_message)

                if upload_success:
                    comment = self.comment_text.get("1.0", tk.END).strip()
                    if comment:
                        # Add comment *after* successful upload
                        # Use the function from servicenow_api
                        comment_success, comment_status_message = servicenow_api.add_work_note_to_ticket(
                            self.servicenow_url, self.servicenow_user, password, table, sys_id, comment
                        )
                        self.update_status(comment_status_message)
                        if comment_success:
                             self.comment_text.delete("1.0", tk.END) # Clear comment box on success
                    else:
                         self.update_status("Attachment uploaded (no comment).")
            else:
                self.update_status("Cannot upload: Ticket lookup failed.")
            return

        # --- Local Save Path ---
        save_path = None
        if self.incident_folder_path:
            # Use the function from screenshot_logic for local save
            success, status_message = screenshot_logic.save_image_to_file(
                self.modified_image, self.incident_folder_path
            )
            if success:
                messagebox.showinfo("Success", status_message, parent=self)
                self.update_status(f"Saved: {os.path.basename(status_message.split(' to ')[-1])}") # Extract filename from message
            else:
                self.update_status(status_message)
            return # Exit after attempting local save to incident folder

        # If no incident folder is set, prompt for save location
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("All", "*.*")],
            title="Save As",
            initialdir=os.getcwd()
        )
        if save_path:
            # Use the function from screenshot_logic for local save
            success, status_message = screenshot_logic.save_image_to_file(
                self.modified_image, os.path.dirname(save_path), filename_prefix=os.path.basename(save_path).split('.')[0]
            )
            if success:
                messagebox.showinfo("Success", status_message, parent=self)
                self.update_status(f"Saved: {os.path.basename(status_message.split(' to ')[-1])}") # Extract filename from message
            else:
                self.update_status(status_message)
        else:
             self.update_status("Local save cancelled.")


# --- Main Execution ---
if __name__ == "__main__":
    # Check for required libraries
    try:
        from PIL import Image, ImageGrab, ImageTk, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not found. Please install it: pip install Pillow")
        exit()
    try:
        import requests
    except ImportError:
        print("Requests not found. Please install it: pip install requests")
        exit()

    app = ScreenshotTool()
    app.text_entry.config(foreground="grey") # Set initial placeholder color
    app.mainloop()