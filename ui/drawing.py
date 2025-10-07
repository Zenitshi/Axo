import tkinter as tk
import math
import numpy as np

def update_ui_elements(app):
    # Check if modern UI is active
    if hasattr(app, 'modern_ui') and app.modern_ui is not None:
        app.modern_ui.update_state_from_app()
        return

    # Default UI updates
    if not app.master.winfo_exists() or not app.drawing_canvas.winfo_exists(): return
    app.drawing_canvas.delete("all"); app.master.update_idletasks()
    if not app.is_window_visible: return

    if app.current_state == "loading_model": draw_loading_model_state_ui(app)
    elif app.current_state == "initial": draw_initial_state_ui(app)
    elif app.current_state == "listening": draw_listening_state_ui(app)
    elif app.current_state == "processing": draw_processing_state_ui(app)
    elif app.current_state == "error_loading": draw_error_loading_state_ui(app)

def draw_loading_model_state_ui(app):
    canvas_width = app.drawing_canvas.winfo_width(); canvas_height = app.drawing_canvas.winfo_height()
    if canvas_width <=1 or canvas_height <=1: return
    app.drawing_canvas.create_text(
        canvas_width / 2, canvas_height / 2,
        text="Loading Model...", fill=app.animation_visual_color,
        font=("Arial", 10)
    )
    if app.current_state == "loading_model":
         app.master.after(100, update_ui_elements, app)

def draw_initial_state_ui(app):
    canvas_width = app.drawing_canvas.winfo_width(); canvas_height = app.drawing_canvas.winfo_height()
    if canvas_width <=1 or canvas_height <=1: return
    line_width, line_thickness = 40, 5; line_y_pos = canvas_height * 0.5
    app.drawing_canvas.create_line(
        (canvas_width-line_width)/2, line_y_pos,
        (canvas_width+line_width)/2, line_y_pos,
        fill=app.indicator_line_color, width=line_thickness, capstyle=tk.ROUND
    )

def draw_listening_state_ui(app):
    canvas_width = app.drawing_canvas.winfo_width(); canvas_height = app.drawing_canvas.winfo_height()
    if canvas_width <= 1 or canvas_height <= 1: return
    anim_center_y = canvas_height / 2
    circle_max_radius = 7
    circle_x_offset = 20
    pulsing_radius = circle_max_radius * (0.65 + 0.35 * abs(math.sin(app.animation_step * 0.38)))
    app.drawing_canvas.create_oval(
        circle_x_offset - pulsing_radius, anim_center_y - pulsing_radius,
        circle_x_offset + pulsing_radius, anim_center_y + pulsing_radius,
        fill=app.accent_color, outline=""
    )
    bar_max_h = 24; bar_w = 4; bar_sep = 3
    total_bars_width = (app.num_audio_bars * (bar_w + bar_sep)) - bar_sep
    bars_start_x_centered = (canvas_width - total_bars_width) / 2
    smoothing_factor = 0.4
    for i in range(app.num_audio_bars):
        phase_shift = i * 0.65
        amplitude_modulation_factor = 0.6 + 0.4 * abs(math.sin(app.animation_step * 0.15 + phase_shift))
        effective_normalized_amplitude = app.current_normalized_amplitude * amplitude_modulation_factor
        target_h_factor = 0.15 + 0.85 * min(effective_normalized_amplitude, 1.0)
        app.bar_target_heights[i] = bar_max_h * target_h_factor
        app.bar_current_heights[i] += (app.bar_target_heights[i] - app.bar_current_heights[i]) * smoothing_factor
        bar_dynamic_height = max(2, app.bar_current_heights[i])
        current_bar_x_center = bars_start_x_centered + i * (bar_w + bar_sep) + (bar_w / 2)
        app.drawing_canvas.create_line(
            current_bar_x_center, anim_center_y - bar_dynamic_height / 2,
            current_bar_x_center, anim_center_y + bar_dynamic_height / 2,
            fill=app.animation_visual_color, width=bar_w, capstyle=tk.ROUND
        )
    app.animation_step += 1
    if app.current_state == "listening": app.master.after(35, update_ui_elements, app)

def draw_processing_state_ui(app):
    canvas_width = app.drawing_canvas.winfo_width(); canvas_height = app.drawing_canvas.winfo_height()
    if canvas_width <=1 or canvas_height <=1: return
    anim_center_x, anim_center_y = canvas_width/2, canvas_height/2
    dot_max_radius = 3.5; orbit_dist = 12 * 1.3; num_processing_dots = 4
    for i in range(num_processing_dots):
        angle = (app.animation_step*0.075 + (2*math.pi/num_processing_dots)*i)
        dot_center_x = anim_center_x + orbit_dist*math.cos(angle)
        dot_center_y = anim_center_y + orbit_dist*math.sin(angle)
        current_dot_size = dot_max_radius * (0.65 + 0.35 * abs(math.sin(app.animation_step*0.12 + i*2)))
        app.drawing_canvas.create_oval(dot_center_x-current_dot_size, dot_center_y-current_dot_size, dot_center_x+current_dot_size, dot_center_y+current_dot_size, fill=app.accent_color, outline="")
    app.animation_step += 1
    if app.current_state == "processing": app.master.after(65, update_ui_elements, app)

def draw_error_loading_state_ui(app):
    canvas_width = app.drawing_canvas.winfo_width(); canvas_height = app.drawing_canvas.winfo_height()
    if canvas_width <=1 or canvas_height <=1: return
    app.drawing_canvas.create_line(canvas_width/2 - 10, canvas_height/2, canvas_width/2 + 10, canvas_height/2, fill="red", width=5, capstyle=tk.ROUND)
    app.drawing_canvas.create_text(
        canvas_width / 2, canvas_height / 2 + 10,
        text="Error Loading", fill="red", font=("Arial", 8)
    ) 