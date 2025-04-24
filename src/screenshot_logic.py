import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab, ImageTk, Image, ImageDraw, ImageFont
import copy
import os
import time
import io

# --- Predefined Options (can be moved to a config or passed in) ---
PREDEFINED_COLORS = {
    "Red": "#FF0000", "Green": "#008000", "Blue": "#0000FF", "Yellow": "#FFFF00",
    "Orange": "#FFA500", "Purple": "#800080", "Cyan": "#00FFFF", "Magenta": "#FF00FF",
    "Black": "#000000", "White": "#FFFFFF", "Gray": "#808080", "Lime": "#00FF00",
    "Maroon": "#800000", "Olive": "#808000", "Navy": "#000080", "Teal": "#008080",
    "Pink": "#FFC0CB", "Brown": "#A52A2A", "Gold": "#FFD700", "Silver": "#C0C0C0"
}
PREDEFINED_SIZES = { "XS": 10, "S": 14, "M": 18, "L": 24, "XL": 32 }
DEFAULT_RECT_WIDTH = 3

# --- Region Selection ---
def start_region_selection(parent_window, on_capture_callback):
    """Starts the fullscreen region selection process."""
    parent_window.withdraw()
    # A small delay is often needed for the main window to fully withdraw
    parent_window.after(300, lambda: _create_selection_window(parent_window, on_capture_callback))

def _create_selection_window(parent_window, on_capture_callback):
    selection_window = tk.Toplevel(parent_window)
    selection_window.attributes("-fullscreen", True)
    selection_window.attributes("-alpha", 0.3)
    selection_window.overrideredirect(True)

    selection_canvas = tk.Canvas(selection_window, cursor="crosshair", bg="grey")
    selection_canvas.pack(fill=tk.BOTH, expand=True)

    selection_state = {
        "start_x": None, "start_y": None, "rect_id": None,
        "window": selection_window, "canvas": selection_canvas,
        "on_capture": on_capture_callback, "parent": parent_window
    }

    selection_canvas.bind("<ButtonPress-1>", lambda event: on_selection_press(event, selection_state))
    selection_canvas.bind("<B1-Motion>", lambda event: on_selection_drag(event, selection_state))
    selection_canvas.bind("<ButtonRelease-1>", lambda event: on_selection_release(event, selection_state))

def on_selection_press(event, state):
    state["start_x"], state["start_y"] = event.x_root, event.y_root
    if state["rect_id"]:
        state["canvas"].delete(state["rect_id"])
    state["rect_id"] = state["canvas"].create_rectangle(
        state["start_x"], state["start_y"], state["start_x"], state["start_y"],
        outline='red', width=2
    )
    state["canvas"].itemconfig(state["rect_id"], fill="")

def on_selection_drag(event, state):
    if state["rect_id"]:
        state["canvas"].coords(state["rect_id"], state["start_x"], state["start_y"], event.x_root, event.y_root)

def on_selection_release(event, state):
    x1, y1 = min(state["start_x"], event.x_root), min(state["start_y"], event.y_root)
    x2, y2 = max(state["start_x"], event.x_root), max(state["start_y"], event.y_root)

    if state["window"]:
        state["window"].destroy()

    state["parent"].deiconify() # Show the main window again

    if x2 > x1 and y2 > y1:
        capture_selected_region((x1, y1, x2, y2), state["on_capture"])
    else:
        state["on_capture"](None, "Selection cancelled.")

def capture_selected_region(bbox, on_capture_callback):
    """Captures the screen region defined by bbox and calls the callback."""
    try:
        screenshot_image = ImageGrab.grab(bbox=bbox, all_screens=True)
        on_capture_callback(screenshot_image, "Area captured.")
    except Exception as e:
        messagebox.showerror("Error", f"Capture failed: {e}")
        on_capture_callback(None, "Capture error.")

# --- Image Display & Coordinate Conversion ---
def display_image_on_canvas(canvas, image, photo_image_ref):
    """Displays the given PIL Image on the tkinter Canvas."""
    if not image:
        canvas.delete("all")
        return None

    cw, ch = canvas.winfo_width(), canvas.winfo_height()
    if cw < 2 or ch < 2: # Handle cases where window size is not yet determined
        cw, ch = 600, 400 # Default size

    img_copy = image.copy()
    img_copy.thumbnail((cw - 20, ch - 20), Image.Resampling.LANCZOS)

    # Keep a reference to the PhotoImage to prevent garbage collection
    photo_image = ImageTk.PhotoImage(img_copy)
    photo_image_ref[0] = photo_image # Store in a mutable object like a list

    canvas.delete("all")
    x, y = (cw - img_copy.width) // 2, (ch - img_copy.height) // 2
    canvas.create_image(x, y, anchor=tk.NW, image=photo_image)
    return photo_image # Return the PhotoImage

def canvas_to_image_coords(canvas, image, photo_image, cx, cy):
    """Converts canvas coordinates to image coordinates."""
    if not image or not photo_image:
        return None, None

    cw, ch = canvas.winfo_width(), canvas.winfo_height()
    iw, ih = image.size
    dw, dh = photo_image.width(), photo_image.height()

    if dw <= 0 or dh <= 0: # Avoid division by zero
        return None, None

    ox, oy = (cw - dw) // 2, (ch - dh) // 2

    # Check if click is within the displayed image area
    if not (ox <= cx < ox + dw and oy <= cy < oy + dh):
        return None, None

    rx, ry = cx - ox, cy - oy
    ix, iy = int(rx * (iw / dw)), int(ry * (ih / dh))

    # Clamp coordinates to image bounds
    return max(0, min(ix, iw - 1)), max(0, min(iy, ih - 1))

def image_to_canvas_coords(canvas, image, photo_image, ix, iy):
    """Converts image coordinates to canvas coordinates."""
    if not image or not photo_image:
        return None, None

    cw, ch = canvas.winfo_width(), canvas.winfo_height()
    iw, ih = image.size
    dw, dh = photo_image.width(), photo_image.height()

    if iw <= 0 or ih <= 0 or dw <= 0 or dh <= 0: # Avoid division by zero
        return None, None

    ox, oy = (cw - dw) // 2, (ch - dh) // 2

    rx, ry = ix * (dw / iw), iy * (dh / ih)

    return int(rx + ox), int(ry + oy)

# --- Annotation Helpers & Drawing ---
def get_annotation_bbox(annotation):
    """Calculates the bounding box for an annotation in image coordinates."""
    if annotation['type'] == 'text':
        try:
            # Use a dummy image and draw object to calculate text bbox
            dummy_img = Image.new('RGB', (1, 1))
            dummy_draw = ImageDraw.Draw(dummy_img)
            font = annotation.get('font') or ImageFont.load_default()
            # textbbox returns (left, top, right, bottom)
            return dummy_draw.textbbox((annotation['x'], annotation['y']), annotation['text'], font=font)
        except Exception:
            # Fallback bbox if textbbox fails
            return (annotation['x'], annotation['y'], annotation['x']+10, annotation['y']+10)
    elif annotation['type'] == 'rectangle':
        return (min(annotation['x1'], annotation['x2']), min(annotation['y1'], annotation['y2']),
                max(annotation['x1'], annotation['x2']), max(annotation['y1'], annotation['y2']))
    return None

def add_text_annotation(image, annotations, ix, iy, text, color, font_size):
    """Adds a text annotation to the list."""
    if not image or not text:
        return annotations, "Select area & enter text."

    try:
        font = ImageFont.load_default()
        try:
            # Attempt to use a TrueType font if available
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            # Fallback to default font if TrueType fails
            pass

        ann = {'type': 'text', 'x': ix, 'y': iy, 'text': text, 'color': color, 'font': font}
        new_annotations = copy.deepcopy(annotations)
        new_annotations.append(ann)
        return new_annotations, "Added text."
    except Exception as e:
        messagebox.showerror("Error", f"Text add failed: {e}")
        return annotations, "Error."

def add_rectangle_annotation(image, annotations, ix1, iy1, ix2, iy2, color, width):
    """Adds a rectangle annotation to the list."""
    if not image:
        return annotations, "Select area first."

    try:
        ann = {'type': 'rectangle', 'x1': ix1, 'y1': iy1, 'x2': ix2, 'y2': iy2, 'color': color, 'width': width}
        new_annotations = copy.deepcopy(annotations)
        new_annotations.append(ann)
        return new_annotations, "Drew rectangle."
    except Exception as e:
        messagebox.showerror("Error", f"Rect draw failed: {e}")
        return annotations, "Error."

def redraw_image_with_annotations(original_image, annotations):
    """Draws all annotations onto a copy of the original image."""
    if not original_image:
        return None

    img = original_image.copy()
    draw = ImageDraw.Draw(img)

    for ann in annotations:
        try:
            if ann['type'] == 'text':
                font = ann.get('font') or ImageFont.load_default()
                draw.text((ann['x'], ann['y']), ann['text'], fill=ann['color'], font=font)
            elif ann['type'] == 'rectangle':
                x1, y1, x2, y2 = min(ann['x1'], ann['x2']), min(ann['y1'], ann['y2']), max(ann['x1'], ann['x2']), max(ann['y1'], ann['y2'])
                draw.rectangle([x1, y1, x2, y2], outline=ann['color'], width=ann['width'])
        except Exception as e:
            print(f"Draw error: {e}") # Print error but continue drawing others

    return img

# --- Selection Handling ---
def find_annotation_at_coords(annotations, ix, iy):
    """Finds the index of the top-most annotation at the given image coordinates."""
    if ix is None or iy is None:
        return None

    # Iterate backwards to select the top-most annotation
    for i in range(len(annotations) - 1, -1, -1):
        ann = annotations[i]
        bbox = get_annotation_bbox(ann)
        if bbox and bbox[0] <= ix <= bbox[2] and bbox[1] <= iy <= bbox[3]:
            return i
    return None

def move_annotation(annotations, index, new_ox, new_oy):
    """Moves the annotation at the given index to the new origin (top-left)."""
    if index is None or index >= len(annotations):
        return annotations

    new_annotations = copy.deepcopy(annotations)
    ann = new_annotations[index]

    if ann['type'] == 'text':
        ann['x'], ann['y'] = new_ox, new_oy
    elif ann['type'] == 'rectangle':
        w, h = abs(ann['x2'] - ann['x1']), abs(ann['y2'] - ann['y1'])
        ann['x1'], ann['y1'], ann['x2'], ann['y2'] = new_ox, new_oy, new_ox + w, new_oy + h

    return new_annotations

# --- Undo/Redo Functionality ---
def save_state_for_undo(history, redo_stack, current_annotations, is_initial_state=False):
    """Saves the current annotation state to the history."""
    current = copy.deepcopy(current_annotations)
    if not is_initial_state and history and current == history[-1]:
        return history, redo_stack # No change, no need to save

    new_history = history + [current]
    new_redo_stack = [] if not is_initial_state else redo_stack
    return new_history, new_redo_stack

def undo_action(history, redo_stack, current_annotations):
    """Undoes the last annotation action."""
    if len(history) > 1:
        new_redo_stack = redo_stack + [copy.deepcopy(current_annotations)]
        new_annotations = copy.deepcopy(history[-2]) # Get the state before the last one
        new_history = history[:-1] # Remove the last state
        return new_history, new_redo_stack, new_annotations, "Undo."
    else:
        return history, redo_stack, current_annotations, "Nothing to undo."

def redo_action(history, redo_stack, current_annotations):
    """Redoes the last undone annotation action."""
    if redo_stack:
        new_history = history + [copy.deepcopy(current_annotations)]
        new_annotations = redo_stack[-1] # Get the state from the top of redo stack
        new_redo_stack = redo_stack[:-1] # Remove the top state
        return new_history, new_redo_stack, new_annotations, "Redo."
    else:
        return history, redo_stack, current_annotations, "Nothing to redo."

# --- Save Image ---
def save_image_to_file(image, folder_path, filename_prefix="screenshot"):
    """Saves the given image to a file in the specified folder."""
    if not image or not folder_path:
        return False, "Error: No image or folder path specified."

    try:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.png"
        full_path = os.path.join(folder_path, filename)
        image.save(full_path)
        return True, f"Image saved to {full_path}"
    except Exception as e:
        messagebox.showerror("Save Error", f"Failed to save image:\n{e}")
        return False, f"Failed to save image: {e}"