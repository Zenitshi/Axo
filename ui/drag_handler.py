
def on_drag_start(app, event):
    app._drag_offset_x = event.x
    app._drag_offset_y = event.y

def on_drag_motion(app, event):
    x = app.master.winfo_pointerx() - app._drag_offset_x
    y = app.master.winfo_pointery() - app._drag_offset_y
    app.master.geometry(f"+{x}+{y}") 