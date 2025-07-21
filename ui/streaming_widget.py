import customtkinter as ctk
import tkinter as tk
from typing import Dict, Any, Optional
import threading
import time

class StreamingWidget:
    """
    A streaming widget that appears above the main button and moves with it.
    """
    
    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.streaming_frame = None
        self.text_widget = None
        self.confidence_indicator = None
        self.is_streaming = False
        self.accumulated_text = ""
        self.corrections_count = 0
        self.streaming_active = False
        self.is_resizable = False
        self.resize_button = None
        
        # Default and current dimensions (increased by 40% width, 20% height)
        self.default_width = 560  # 400 * 1.4
        self.default_height = 180  # 150 * 1.2
        self.min_width = 420  # 300 * 1.4
        self.min_height = 120  # 100 * 1.2
        self.max_width = 1120  # 800 * 1.4
        self.max_height = 480  # 400 * 1.2
        self.current_width = self.default_width
        self.current_height = self.default_height
        
        # Resize tracking
        self.resize_start_x = 0
        self.resize_start_y = 0
        self.resize_start_width = 0
        self.resize_start_height = 0
        self.resize_mode = None
        self.resize_start_pos_x = 0
        self.resize_start_pos_y = 0
        
        # Position tracking for button connection
        self.position_update_job = None
        self.first_token_received = False
        
    def show_streaming_widget(self, original_text: str):
        """
        Show the streaming widget above the main button.
        """
        if self.streaming_frame is not None:
            self.close_widget()
            
        # Reset to default size each time
        self.current_width = self.default_width
        self.current_height = self.default_height
        self.is_resizable = False
        self.first_token_received = False
        
        # Create the streaming widget
        self.streaming_frame = ctk.CTkToplevel(self.parent_app.master)
        self.streaming_frame.title("")
        self.streaming_frame.overrideredirect(True)
        self.streaming_frame.attributes("-topmost", True)
        self.streaming_frame.configure(fg_color="#2B2B2B", corner_radius=12)
        
        # Position the widget initially
        self.update_widget_position()
        
        # Bind resize events
        self.streaming_frame.bind("<Button-1>", self.on_click)
        self.streaming_frame.bind("<B1-Motion>", self.on_drag)
        self.streaming_frame.bind("<ButtonRelease-1>", self.on_release)
        
        # Main container
        main_container = ctk.CTkFrame(self.streaming_frame, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=3, pady=3)
        
        # Header with controls
        header_frame = ctk.CTkFrame(main_container, fg_color="transparent", height=25)
        header_frame.pack(fill="x", pady=(0, 3))
        header_frame.pack_propagate(False)
        
        # Status indicator
        self.confidence_indicator = ctk.CTkLabel(
            header_frame, 
            text="● Processing...", 
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color="#4A9EFF"
        )
        self.confidence_indicator.pack(side="left", padx=(5, 0))
        
        # Close button (rightmost)
        close_btn = ctk.CTkButton(
            header_frame,
            text="×",
            width=20,
            height=18,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self.close_widget,
            fg_color="#FF4444",
            hover_color="#FF6666"
        )
        close_btn.pack(side="right", padx=(0, 2))
        
        # Resize toggle button (middle)
        self.resize_button = ctk.CTkButton(
            header_frame,
            text="⤡",
            width=20,
            height=18,
            font=ctk.CTkFont(size=10),
            command=self.toggle_resize_mode,
            fg_color="#666666",
            hover_color="#777777"
        )
        self.resize_button.pack(side="right", padx=(0, 2))
        
        # Paste button (left of resize and close)
        paste_btn = ctk.CTkButton(
            header_frame,
            text="Paste",
            width=40,
            height=18,
            font=ctk.CTkFont(size=9),
            command=self.paste_and_close,
            fg_color="#4CAF50",
            hover_color="#45A049"
        )
        paste_btn.pack(side="right", padx=(0, 2))
        
        # Copy button (left of paste)
        copy_btn = ctk.CTkButton(
            header_frame,
            text="Copy",
            width=40,
            height=18,
            font=ctk.CTkFont(size=9),
            command=self.copy_text,
            fg_color="#4A9EFF",
            hover_color="#3A8EEF"
        )
        copy_btn.pack(side="right", padx=(0, 2))
        
        # Text display area with scrolling
        text_frame = ctk.CTkFrame(main_container, fg_color="#1E1E1E", corner_radius=8)
        text_frame.pack(fill="both", expand=True)
        
        # Scrollable text widget (same text size as specified)
        self.text_widget = ctk.CTkTextbox(
            text_frame,
            font=ctk.CTkFont(size=11),  # Keep text size unchanged
            wrap="word",
            activate_scrollbars=True,
            scrollbar_button_color="#666666",
            scrollbar_button_hover_color="#777777"
        )
        self.text_widget.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Initialize state
        self.accumulated_text = ""
        self.corrections_count = 0
        self.is_streaming = True
        self.streaming_active = True
        
        # Show initial message
        self.text_widget.insert("0.0", "Preparing to process text...")
        
        # Start position tracking
        self.start_position_tracking()
        
    def update_widget_position(self):
        """Update widget position relative to main button."""
        if not self.streaming_frame or not self.streaming_active:
            return
            
        try:
            # Force update the parent app geometry first
            self.parent_app.master.update_idletasks()
            
            # Get button position with more robust method
            button_x = self.parent_app.master.winfo_rootx()
            button_y = self.parent_app.master.winfo_rooty()
            button_width = self.parent_app.master.winfo_width()
            button_height = self.parent_app.master.winfo_height()
            
            # Position above the button, centered horizontally
            pos_x = button_x + (button_width // 2) - (self.current_width // 2)
            pos_y = button_y - self.current_height - 20  # Increased gap
            
            # Ensure widget doesn't go off screen
            screen_width = self.parent_app.master.winfo_screenwidth()
            screen_height = self.parent_app.master.winfo_screenheight()
            
            # Horizontal bounds with better margins
            margin = 20
            if pos_x < margin:
                pos_x = margin
            elif pos_x + self.current_width > screen_width - margin:
                pos_x = screen_width - self.current_width - margin
                
            # Vertical bounds - ensure it doesn't go above screen
            if pos_y < margin:
                # If can't fit above, position below button instead
                pos_y = button_y + button_height + 20
                # If still doesn't fit, place at safe position
                if pos_y + self.current_height > screen_height - margin:
                    pos_y = screen_height - self.current_height - margin
            elif pos_y + self.current_height > screen_height - margin:
                pos_y = screen_height - self.current_height - margin
            
            # Update position only if it's actually different to avoid flicker
            current_geometry = self.streaming_frame.geometry()
            new_geometry = f"{self.current_width}x{self.current_height}+{pos_x}+{pos_y}"
            
            if current_geometry != new_geometry:
                self.streaming_frame.geometry(new_geometry)
            
        except Exception as e:
            print(f"Error updating widget position: {e}")
    
    def start_position_tracking(self):
        """Start tracking button position to keep widget connected."""
        if self.streaming_active and not self.is_resizable:
            self.update_widget_position()
            # Schedule next update with faster frequency for smoother tracking
            self.position_update_job = self.parent_app.master.after(50, self.start_position_tracking)
    
    def stop_position_tracking(self):
        """Stop position tracking."""
        if self.position_update_job:
            self.parent_app.master.after_cancel(self.position_update_job)
            self.position_update_job = None
        
    def toggle_resize_mode(self):
        """Toggle resize mode on/off."""
        self.is_resizable = not self.is_resizable
        
        if self.is_resizable:
            self.resize_button.configure(text="⤢", fg_color="#4CAF50")
            self.streaming_frame.configure(cursor="sizing")
            # Stop position tracking during resize
            self.stop_position_tracking()
        else:
            self.resize_button.configure(text="⤡", fg_color="#666666")
            self.streaming_frame.configure(cursor="")
            # Resume position tracking
            self.start_position_tracking()
    
    def on_click(self, event):
        """Handle mouse click for resize functionality."""
        if not self.is_resizable:
            return
            
        self.resize_start_x = event.x_root
        self.resize_start_y = event.y_root
        self.resize_start_width = self.current_width
        self.resize_start_height = self.current_height
        self.resize_start_pos_x = self.streaming_frame.winfo_x()
        self.resize_start_pos_y = self.streaming_frame.winfo_y()
        
        # Determine resize mode based on cursor position
        widget_x = event.x
        widget_y = event.y
        
        # Corner and edge detection
        corner_size = 15
        
        if widget_x < corner_size and widget_y < corner_size:
            self.resize_mode = "nw"
            self.streaming_frame.configure(cursor="size_nw_se")
        elif widget_x > self.current_width - corner_size and widget_y < corner_size:
            self.resize_mode = "ne"
            self.streaming_frame.configure(cursor="size_ne_sw")
        elif widget_x < corner_size and widget_y > self.current_height - corner_size:
            self.resize_mode = "sw"
            self.streaming_frame.configure(cursor="size_ne_sw")
        elif widget_x > self.current_width - corner_size and widget_y > self.current_height - corner_size:
            self.resize_mode = "se"
            self.streaming_frame.configure(cursor="size_nw_se")
        elif widget_x < corner_size:
            self.resize_mode = "w"
            self.streaming_frame.configure(cursor="size_we")
        elif widget_x > self.current_width - corner_size:
            self.resize_mode = "e"
            self.streaming_frame.configure(cursor="size_we")
        elif widget_y < corner_size:
            self.resize_mode = "n"
            self.streaming_frame.configure(cursor="size_ns")
        elif widget_y > self.current_height - corner_size:
            self.resize_mode = "s"
            self.streaming_frame.configure(cursor="size_ns")
        else:
            self.resize_mode = None
    
    def on_drag(self, event):
        """Handle mouse drag for resizing with bounds checking."""
        if not self.is_resizable or not self.resize_mode:
            return
            
        try:
            dx = event.x_root - self.resize_start_x
            dy = event.y_root - self.resize_start_y
            
            new_width = self.resize_start_width
            new_height = self.resize_start_height
            new_x = self.resize_start_pos_x
            new_y = self.resize_start_pos_y
            
            # Calculate new dimensions based on resize mode
            if "e" in self.resize_mode:
                new_width = max(self.min_width, min(self.max_width, self.resize_start_width + dx))
            elif "w" in self.resize_mode:
                target_width = self.resize_start_width - dx
                new_width = max(self.min_width, min(self.max_width, target_width))
                # Adjust position only if we can actually resize
                width_change = self.resize_start_width - new_width
                new_x = self.resize_start_pos_x + width_change
                
            if "s" in self.resize_mode:
                new_height = max(self.min_height, min(self.max_height, self.resize_start_height + dy))
            elif "n" in self.resize_mode:
                target_height = self.resize_start_height - dy
                new_height = max(self.min_height, min(self.max_height, target_height))
                # Adjust position only if we can actually resize
                height_change = self.resize_start_height - new_height
                new_y = self.resize_start_pos_y + height_change
            
            # Screen bounds checking with safety margins
            screen_width = self.parent_app.master.winfo_screenwidth()
            screen_height = self.parent_app.master.winfo_screenheight()
            margin = 10
            
            # Ensure widget stays fully on screen
            if new_x < margin:
                new_x = margin
            elif new_x + new_width > screen_width - margin:
                new_x = screen_width - new_width - margin
                
            if new_y < margin:
                new_y = margin
            elif new_y + new_height > screen_height - margin:
                new_y = screen_height - new_height - margin
            
            # Apply new dimensions safely
            self.current_width = new_width
            self.current_height = new_height
            
            # Update geometry with validation
            new_geometry = f"{new_width}x{new_height}+{new_x}+{new_y}"
            self.streaming_frame.geometry(new_geometry)
            
        except Exception as e:
            print(f"Error during resize: {e}")
            # Reset to safe state
            self.is_resizable = False
            self.resize_button.configure(text="⤡", fg_color="#666666")
            self.streaming_frame.configure(cursor="")
    
    def on_release(self, event):
        """Handle mouse release after resizing."""
        if self.is_resizable:
            self.streaming_frame.configure(cursor="sizing")
        self.resize_mode = None
        
    def update_streaming_content(self, stream_data: Dict[str, Any]):
        """Update the streaming widget with native API streaming content."""
        if not self.streaming_frame or not self.streaming_active:
            return
            
        try:
            data_type = stream_data.get("type")
            content = stream_data.get("content", "")
            
            if data_type == "token":
                # If this is the first token, clear the "Preparing..." message
                if not self.first_token_received:
                    self.text_widget.delete("1.0", tk.END)
                    self.first_token_received = True

                if content:
                    self.accumulated_text += content
                    self.text_widget.insert(tk.END, content)
                    self.text_widget.see(tk.END)
                    # Force the UI to update to show the token immediately
                    self.streaming_frame.update_idletasks()
                    
            elif data_type == "final":
                # Mark streaming as complete
                if self.confidence_indicator:
                    self.confidence_indicator.configure(
                        text="● Complete", 
                        text_color="#4CAF50"
                    )
                self.is_streaming = False
                
            elif data_type == "error":
                if self.confidence_indicator:
                    self.confidence_indicator.configure(
                        text="● Error", 
                        text_color="#FF4444"
                    )
                self.text_widget.delete("1.0", tk.END)
                self.text_widget.insert("1.0", f"Error: {content}")
                self.is_streaming = False
                
        except Exception as e:
            print(f"Error updating streaming content: {e}")
    
    def update_confidence_display(self, confidence: float):
        """Update the confidence indicator display."""
        if not self.confidence_indicator or not self.streaming_active:
            return
            
        try:
            if confidence >= 0.8:
                color = "#4CAF50"
                status = "● High"
            elif confidence >= 0.5:
                color = "#FF9800"
                status = "● Medium"
            else:
                color = "#FF4444"
                status = "● Low"
                
            self.confidence_indicator.configure(text=status, text_color=color)
            
        except Exception as e:
            print(f"Error updating confidence display: {e}")
    
    def update_corrections_indicator(self):
        """Update the corrections count in the indicator."""
        if not self.confidence_indicator or not self.streaming_active:
            return
            
        try:
            current_text = self.confidence_indicator.cget("text")
            if self.corrections_count > 0:
                base_text = current_text.split(" (")[0]
                self.confidence_indicator.configure(
                    text=f"{base_text} ({self.corrections_count})"
                )
        except Exception as e:
            print(f"Error updating corrections indicator: {e}")
    
    def copy_text(self):
        """Copy the current accumulated text to clipboard."""
        if self.accumulated_text and self.streaming_active:
            try:
                import pyperclip
                pyperclip.copy(self.accumulated_text)
                
                # Show brief feedback
                if self.confidence_indicator:
                    original_text = self.confidence_indicator.cget("text")
                    self.confidence_indicator.configure(text="● Copied!", text_color="#4CAF50")
                    
                    def restore_text():
                        if self.confidence_indicator and self.streaming_active:
                            self.confidence_indicator.configure(text=original_text)
                    
                    self.parent_app.master.after(1500, restore_text)
                    
            except Exception as e:
                print(f"Error copying text: {e}")
    
    def paste_text(self):
        """Paste the accumulated text without closing."""
        if self.accumulated_text and self.streaming_active:
            try:
                import pyperclip
                import pyautogui
                pyperclip.copy(self.accumulated_text)
                time.sleep(0.1)
                pyautogui.hotkey('ctrl', 'v')
            except Exception as e:
                print(f"Error pasting text: {e}")
    
    def paste_and_close(self):
        """Paste the accumulated text and close the widget."""
        if self.accumulated_text and self.streaming_active:
            try:
                import pyperclip
                import pyautogui
                # Copy text to clipboard
                pyperclip.copy(self.accumulated_text)
                # Small delay to ensure clipboard is updated
                time.sleep(0.1)
                # Close widget first to remove focus from it
                self.close_widget()
                # Small delay to allow focus to return to previous application
                time.sleep(0.1)
                # Paste the content
                pyautogui.hotkey('ctrl', 'v')
                return  # Exit early since we already closed the widget
            except Exception as e:
                print(f"Error pasting text: {e}")
        self.close_widget()
    
    def close_widget(self):
        """Close the streaming widget safely."""
        self.streaming_active = False
        self.is_streaming = False
        self.is_resizable = False
        
        # Stop position tracking
        self.stop_position_tracking()
        
        if self.streaming_frame:
            try:
                self.streaming_frame.destroy()
            except:
                pass
            self.streaming_frame = None
            
        self.text_widget = None
        self.confidence_indicator = None
        self.resize_button = None
        self.accumulated_text = ""
        self.corrections_count = 0
        
        # Reset to default size for next time
        self.current_width = self.default_width
        self.current_height = self.default_height
    
    def is_widget_open(self) -> bool:
        """Check if the streaming widget is currently open."""
        return (self.streaming_frame is not None and 
                self.streaming_active and 
                self.is_streaming) 