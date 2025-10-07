import tkinter as tk
from tkinter import Canvas
import math
import random
import time
from threading import Thread
import sys


class ModernPillUI:
    def __init__(self, app):
        self.app = app

        # Remove default UI components
        if hasattr(app, 'main_content_frame'):
            app.main_content_frame.destroy()

        # Set up the main window with no decorations
        app.master.title("")
        app.master.overrideredirect(True)  # Remove window border and title bar
        app.master.attributes("-topmost", True)  # Keep window on top
        app.master.attributes("-transparentcolor", "#000001")  # Use a specific color for transparency

        # Set window size and position
        self.width = 240
        self.height = 60
        screen_width = app.master.winfo_screenwidth()
        screen_height = app.master.winfo_screenheight()
        offset_from_bottom = 30
        self.initial_pos_x = (screen_width // 2) - (self.width // 2)
        self.initial_pos_y = screen_height - self.height - offset_from_bottom
        app.master.geometry(f"{self.width}x{self.height}+{self.initial_pos_x}+{self.initial_pos_y}")

        # Variables for UI state - map to app's state system
        self.state = "ready"  # ready, listening, processing, error
        self.is_recording = False
        self.drag_start_x = 0
        self.drag_start_y = 0

        # Animation variables
        self.pulse_radius = 12
        self.pulse_direction = 1
        self.audio_bars = [0] * 12
        self.processing_angle = 0
        self.pulse_alpha = 0
        self.bar_pulse = 0
        self.bar_direction = 1
        self.animation_time = 0

        # Create the main canvas with a specific background color
        self.canvas = Canvas(
            app.master,
            width=self.width,
            height=self.height,
            bg="#000001",  # This color will be transparent
            highlightthickness=0
        )
        self.canvas.pack()

        # Create the pill-shaped background
        self.draw_pill_background()

        # Create the state indicator circle
        self.state_circle = self.canvas.create_oval(
            18, 18, 42, 42,
            fill="#4a9eff",
            outline="",
            tags="state_circle"
        )

        # Create the ready state bar
        self.ready_bar = self.canvas.create_rectangle(
            self.width//2 - 20, self.height//2 - 1.5,
            self.width//2 + 20, self.height//2 + 1.5,
            fill="#a0a0a0",
            outline="",
            tags="ready_bar"
        )

        # Create audio bars (initially hidden)
        self.audio_bar_objects = []
        bar_width = 6
        bar_spacing = 3
        start_x = 80

        for i in range(12):
            x = start_x + i * (bar_width + bar_spacing)
            # Create pill-shaped bars with rounded ends
            bar_id = self.canvas.create_oval(
                x, self.height//2 - 20,
                x + bar_width, self.height//2 + 20,
                fill="#f0f0f0",
                outline="",
                tags=f"audio_bar_{i}"
            )
            self.audio_bar_objects.append(bar_id)

        # Create processing spinner
        self.spinner_parts = []
        for i in range(3):
            part = self.canvas.create_arc(
                18, 18, 42, 42,
                start=i*30, extent=90-i*20,
                outline="#4a9eff",
                width=2,
                style="arc",
                tags=f"spinner_{i}"
            )
            self.spinner_parts.append(part)

        # Create error X
        self.error_x1 = self.canvas.create_line(
            24, 24, 36, 36,
            fill="#ffffff",
            width=2,
            tags="error_x1"
        )
        self.error_x2 = self.canvas.create_line(
            36, 24, 24, 36,
            fill="#ffffff",
            width=2,
            tags="error_x2"
        )

        # Create text elements
        self.processing_text = self.canvas.create_text(
            self.width//2, self.height//2,
            text="Processing",
            fill="#a0a0a0",
            font=("Segoe UI", 10),
            tags="processing_text"
        )

        self.error_text = self.canvas.create_text(
            self.width//2, self.height//2,
            text="Error",
            fill="#ff5555",
            font=("Segoe UI", 10),
            tags="error_text"
        )

        # Create loading text element
        self.loading_text = self.canvas.create_text(
            self.width//2, self.height//2,
            text="Loading Model...",
            fill="#a0a0a0",
            font=("Segoe UI", 10),
            tags="loading_text"
        )

        # Set initial state based on app's current state
        self.update_state_from_app()

        # Bind events
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        # Start the animation loop
        self.animate()

    def draw_pill_background(self):
        """Draw the pill-shaped background with anti-aliasing"""
        self.canvas.delete("background")

        # Create a pill shape (rounded rectangle) with fully rounded ends
        radius = self.height / 2

        # Draw the main pill shape with anti-aliasing
        # Use multiple layers for anti-aliasing effect
        for layer in range(3):
            offset = layer * 0.3
            color_value = 10 + layer * 2
            color = f"#{color_value:02x}{color_value:02x}{color_value:02x}"

            # Left arc
            self.canvas.create_arc(
                offset, offset, radius*2+offset, self.height-offset,
                start=90, extent=180,
                fill=color, outline="", tags="background"
            )

            # Right arc
            self.canvas.create_arc(
                self.width-radius*2-offset, offset, self.width-offset, self.height-offset,
                start=270, extent=180,
                fill=color, outline="", tags="background"
            )

            # Middle rectangle
            self.canvas.create_rectangle(
                radius+offset, offset, self.width-radius-offset, self.height-offset,
                fill=color, outline="", tags="background"
            )

        # Add subtle border with anti-aliasing
        border_color = "#1a1a1a"

        # Left arc border
        self.canvas.create_arc(
            0, 0, radius*2, self.height,
            start=90, extent=180,
            outline=border_color, width=1, style="arc", tags="background"
        )

        # Right arc border
        self.canvas.create_arc(
            self.width-radius*2, 0, self.width, self.height,
            start=270, extent=180,
            outline=border_color, width=1, style="arc", tags="background"
        )

        # Top and bottom borders
        self.canvas.create_line(
            radius, 0, self.width-radius, 0,
            fill=border_color, width=1, tags="background"
        )
        self.canvas.create_line(
            radius, self.height, self.width-radius, self.height,
            fill=border_color, width=1, tags="background"
        )

    def update_visibility(self):
        """Update visibility of elements based on current state"""
        if self.state == "loading":
            # Show loading text, hide others
            self.canvas.itemconfig(self.ready_bar, state="hidden")
            for bar in self.audio_bar_objects:
                self.canvas.itemconfig(bar, state="hidden")
            for part in self.spinner_parts:
                self.canvas.itemconfig(part, state="hidden")
            self.canvas.itemconfig(self.error_x1, state="hidden")
            self.canvas.itemconfig(self.error_x2, state="hidden")
            self.canvas.itemconfig(self.processing_text, state="hidden")
            self.canvas.itemconfig(self.error_text, state="hidden")
            self.canvas.itemconfig(self.loading_text, state="normal")

        elif self.state == "ready":
            # Show ready bar, hide others
            self.canvas.itemconfig(self.ready_bar, state="normal")
            for bar in self.audio_bar_objects:
                self.canvas.itemconfig(bar, state="hidden")
            for part in self.spinner_parts:
                self.canvas.itemconfig(part, state="hidden")
            self.canvas.itemconfig(self.error_x1, state="hidden")
            self.canvas.itemconfig(self.error_x2, state="hidden")
            self.canvas.itemconfig(self.processing_text, state="hidden")
            self.canvas.itemconfig(self.error_text, state="hidden")
            self.canvas.itemconfig(self.loading_text, state="hidden")

        elif self.state == "listening":
            # Show audio bars, hide others
            self.canvas.itemconfig(self.ready_bar, state="hidden")
            for bar in self.audio_bar_objects:
                self.canvas.itemconfig(bar, state="normal")
            for part in self.spinner_parts:
                self.canvas.itemconfig(part, state="hidden")
            self.canvas.itemconfig(self.error_x1, state="hidden")
            self.canvas.itemconfig(self.error_x2, state="hidden")
            self.canvas.itemconfig(self.processing_text, state="hidden")
            self.canvas.itemconfig(self.error_text, state="hidden")
            self.canvas.itemconfig(self.loading_text, state="hidden")

        elif self.state == "processing":
            # Show spinner, hide others
            self.canvas.itemconfig(self.ready_bar, state="hidden")
            for bar in self.audio_bar_objects:
                self.canvas.itemconfig(bar, state="hidden")
            for part in self.spinner_parts:
                self.canvas.itemconfig(part, state="normal")
            self.canvas.itemconfig(self.error_x1, state="hidden")
            self.canvas.itemconfig(self.error_x2, state="hidden")
            self.canvas.itemconfig(self.processing_text, state="normal")
            self.canvas.itemconfig(self.error_text, state="hidden")
            self.canvas.itemconfig(self.loading_text, state="hidden")

        elif self.state == "error":
            # Show error, hide others
            self.canvas.itemconfig(self.ready_bar, state="hidden")
            for bar in self.audio_bar_objects:
                self.canvas.itemconfig(bar, state="hidden")
            for part in self.spinner_parts:
                self.canvas.itemconfig(part, state="hidden")
            self.canvas.itemconfig(self.error_x1, state="normal")
            self.canvas.itemconfig(self.error_x2, state="normal")
            self.canvas.itemconfig(self.processing_text, state="hidden")
            self.canvas.itemconfig(self.error_text, state="normal")
            self.canvas.itemconfig(self.loading_text, state="hidden")

    def animate(self):
        """Main animation loop with smooth 60fps rendering"""
        self.animation_time += 0.016  # ~60fps

        if self.state == "loading":
            # Animate loading text with subtle pulsing effect
            loading_alpha = 0.6 + 0.4 * abs(math.sin(self.animation_time * 2))
            loading_color_value = int(160 * loading_alpha)
            loading_color = f"#{loading_color_value:02x}{loading_color_value:02x}{loading_color_value:02x}"
            self.canvas.itemconfig(self.loading_text, fill=loading_color)

            # Update state circle to show loading state with glow effect
            circle_alpha = 0.5 + 0.3 * abs(math.sin(self.animation_time * 1.5))
            circle_color_value = int(128 * circle_alpha)
            circle_color = f"#{circle_color_value:02x}{circle_color_value:02x}{circle_color_value:02x}"
            self.canvas.itemconfig(self.state_circle, fill=circle_color)

        elif self.state == "ready":
            # Animate the ready bar with smooth pulsing
            self.bar_pulse += 0.02 * self.bar_direction
            if self.bar_pulse > 1 or self.bar_pulse < 0:
                self.bar_direction *= -1

            # Update bar color with smooth transition
            bar_alpha = 0.5 + self.bar_pulse * 0.5
            bar_color_value = int(160 * bar_alpha)
            bar_color = f"#{bar_color_value:02x}{bar_color_value:02x}{bar_color_value:02x}"
            self.canvas.itemconfig(self.ready_bar, fill=bar_color)

            # Update state circle color with glow effect
            circle_alpha = 0.7 + 0.3 * abs(math.sin(self.animation_time * 2))
            circle_r = int(74 * circle_alpha)
            circle_g = int(158 * circle_alpha)
            circle_b = int(255 * circle_alpha)
            circle_color = f"#{circle_r:02x}{circle_g:02x}{circle_b:02x}"
            self.canvas.itemconfig(self.state_circle, fill=circle_color)

        elif self.state == "listening":
            # Update pulse animation
            self.pulse_radius += 0.2 * self.pulse_direction
            if self.pulse_radius > 16 or self.pulse_radius < 12:
                self.pulse_direction *= -1

            # Update pulse alpha
            self.pulse_alpha = (self.pulse_radius - 12) / 4

            # Update state circle with glow effect
            circle_alpha = 0.8 + 0.2 * abs(math.sin(self.animation_time * 3))
            circle_r = int(74 * circle_alpha)
            circle_g = int(158 * circle_alpha)
            circle_b = int(255 * circle_alpha)
            circle_color = f"#{circle_r:02x}{circle_g:02x}{circle_b:02x}"
            self.canvas.itemconfig(self.state_circle, fill=circle_color)

            # Update audio bars with smooth animation and glow
            bar_width = 6
            bar_spacing = 3
            start_x = 80
            max_height = self.height - 24
            center_y = self.height // 2

            for i, height in enumerate(self.audio_bars):
                x = start_x + i * (bar_width + bar_spacing)
                bar_height = height * max_height * 0.8

                # Create pill-shaped bars with rounded ends
                # Calculate the new oval dimensions
                new_y1 = center_y - bar_height/2
                new_y2 = center_y + bar_height/2

                # Update the oval to create a pill shape
                self.canvas.coords(
                    self.audio_bar_objects[i],
                    x, new_y1, x + bar_width, new_y2
                )

                # Add glow effect to audio bar color
                bar_alpha = min(1.0, 0.6 + 0.4 * height + 0.2 * abs(math.sin(self.animation_time * 5 + i * 0.5)))
                bar_color_value = min(255, int(240 * bar_alpha))
                bar_color = f"#{bar_color_value:02x}{bar_color_value:02x}{bar_color_value:02x}"
                self.canvas.itemconfig(self.audio_bar_objects[i], fill=bar_color)

        elif self.state == "processing":
            # Update spinner animation
            self.processing_angle = (self.processing_angle + 5) % 360

            # Update spinner parts
            for i, part in enumerate(self.spinner_parts):
                start_angle = self.processing_angle + i * 30
                extent = 90 - i * 20
                self.canvas.itemconfig(part, start=start_angle)

            # Update state circle color with glow effect
            circle_alpha = 0.7 + 0.3 * abs(math.sin(self.animation_time * 2.5))
            circle_r = int(74 * circle_alpha)
            circle_g = int(158 * circle_alpha)
            circle_b = int(255 * circle_alpha)
            circle_color = f"#{circle_r:02x}{circle_g:02x}{circle_b:02x}"
            self.canvas.itemconfig(self.state_circle, fill=circle_color)
            # Add to processing state animation:
            text_alpha = 0.6 + 0.4 * abs(math.sin(self.animation_time * 2))
            text_color_value = int(160 * text_alpha)
            text_color = f"#{text_color_value:02x}{text_color_value:02x}{text_color_value:02x}"
            self.canvas.itemconfig(self.processing_text, fill=text_color)

        elif self.state == "error":
            # Update state circle to red
            self.canvas.itemconfig(self.state_circle, fill="#ff5555")

            # Animate error state with subtle shake
            shake_offset = math.sin(self.animation_time * 10) * 2
            self.canvas.coords(
                self.error_x1,
                24 + shake_offset, 24, 36 + shake_offset, 36
            )
            self.canvas.coords(
                self.error_x2,
                36 + shake_offset, 24, 24 + shake_offset, 36
            )

        # Schedule the next animation frame
        self.animation_job = self.app.master.after(16, self.animate)  # ~60fps

    def on_click(self, event):
        """Handle mouse click - only for dragging, no recording functionality"""
        self.drag_start_x = event.x_root - self.app.master.winfo_x()
        self.drag_start_y = event.y_root - self.app.master.winfo_y()
        # Recording functionality removed - only hotkey (Ctrl+Shift+Space) can start recording

    def on_drag(self, event):
        """Handle window dragging"""
        x = event.x_root - self.drag_start_x
        y = event.y_root - self.drag_start_y
        self.app.master.geometry(f"+{x}+{y}")

    def on_release(self, event):
        """Handle mouse release - no recording functionality"""
        # Recording functionality removed - only hotkey (Ctrl+Shift+Space) can stop recording
        pass

    def start_recording(self):
        """Start recording with smooth transition"""
        if not self.app.model_loaded_event.is_set():
            print("Model is still loading, please wait.")
            return

        self.is_recording = True
        self.state = "listening"
        self.update_visibility()

        # Map to app's state system
        self.app.current_state = "listening"
        self.app._start_audio_recording()

    def stop_recording(self):
        """Stop recording with smooth transition"""
        if self.is_recording:
            self.is_recording = False
            self.state = "processing"
            self.update_visibility()

            # Map to app's state system
            self.app.current_state = "processing"
            self.app._stop_audio_recording_and_process()

    def update_audio_bars(self, amplitude):
        """Update audio bars based on actual audio input"""
        # Map the amplitude to audio bar heights
        for i in range(len(self.audio_bars)):
            # Create variation across bars based on position
            phase_shift = i * 0.5
            time_value = time.time()

            # Create natural variation pattern
            base_pattern = math.sin(time_value * 3 + phase_shift) * 0.3
            variation = math.sin(time_value * 7 + i * 0.8) * 0.2

            # Apply amplitude and variations
            self.audio_bars[i] = max(0.1, min(1.0, amplitude * 0.8 + base_pattern + variation + 0.2))

    def finish_processing(self):
        """Transition from processing to ready state"""
        self.state = "ready"
        self.update_visibility()
        self.audio_bars = [0] * 12

        # Map to app's state system
        self.app.current_state = "initial"
        self.app._set_initial_state_after_processing()

    def update_state_from_app(self):
        """Update UI state based on app's current state"""
        if hasattr(self.app, 'current_state'):
            if self.app.current_state == "loading_model":
                self.state = "loading"
            elif self.app.current_state == "initial":
                self.state = "ready"
            elif self.app.current_state == "listening":
                self.state = "listening"
            elif self.app.current_state == "processing":
                self.state = "processing"
            elif self.app.current_state == "error_loading":
                self.state = "error"
            else:
                self.state = "ready"

            self.update_visibility()

    def destroy(self):
        """Clean up modern UI components"""
        # Cancel animation loop first to prevent accessing destroyed canvas
        if hasattr(self, 'animation_job'):
            self.app.master.after_cancel(self.animation_job)
            self.animation_job = None

        if hasattr(self, 'canvas'):
            self.canvas.destroy()