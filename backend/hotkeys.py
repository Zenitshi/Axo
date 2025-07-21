from pynput import keyboard

def get_pynput_key(key_name):
    """Maps a string key name to a pynput key object."""
    key_map = {
        'alt': keyboard.Key.alt, 'alt_l': keyboard.Key.alt_l, 'alt_r': keyboard.Key.alt_r,
        'ctrl': keyboard.Key.ctrl, 'ctrl_l': keyboard.Key.ctrl_l, 'ctrl_r': keyboard.Key.ctrl_r,
        'shift': keyboard.Key.shift, 'shift_l': keyboard.Key.shift_l, 'shift_r': keyboard.Key.shift_r,
        'space': keyboard.Key.space,
    }
    if key_name in key_map:
        return key_map[key_name]
    try:
        # For special keys like 'f1', 'enter', etc.
        return keyboard.Key[key_name]
    except KeyError:
        # For regular character keys
        return keyboard.KeyCode.from_char(key_name)

def update_hotkey_from_config(app):
    """Parses the hotkey from the config and updates instance variables."""
    hotkey_conf = app.config.get("hotkey_config", {"modifiers": ["ctrl", "shift"], "key": "space"})
    app.hotkey_modifiers = [mod.lower() for mod in hotkey_conf.get("modifiers", [])]
    app.hotkey_key_str = hotkey_conf.get("key", "space").lower()
    app.hotkey_key = get_pynput_key(app.hotkey_key_str)
    print(f"Hotkey updated to: {' + '.join(m.capitalize() for m in app.hotkey_modifiers)} + {app.hotkey_key_str.capitalize()}")

def check_hotkey_modifiers_active(app):
    """Checks if the configured modifier keys are currently pressed."""
    # This is a simplified check. A more robust check would handle left/right modifiers.
    for mod in app.hotkey_modifiers:
        if mod == 'ctrl' and not any(k in app.currently_pressed_keys for k in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)):
            return False
        if mod == 'shift' and not any(k in app.currently_pressed_keys for k in (keyboard.Key.shift_l, keyboard.Key.shift_r)):
            return False
        if mod == 'alt' and not any(k in app.currently_pressed_keys for k in (keyboard.Key.alt_l, keyboard.Key.alt_r)):
            return False
    return True

def start_keyboard_listener(app):
    print("Starting global keyboard listener for Axo...")
    with keyboard.Listener(on_press=lambda key: on_global_key_press(app, key), on_release=lambda key: on_global_key_release(app, key)) as listener:
        listener.join()
    print("Axo global keyboard listener stopped.")

def on_global_key_press(app, key):
    app.currently_pressed_keys.add(key)
    
    key_char_val = getattr(key, 'char', None)
    vk_val = getattr(key, 'vk', None)
    
    has_ctrl = any(k in app.currently_pressed_keys for k in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r))
    has_shift = any(k in app.currently_pressed_keys for k in (keyboard.Key.shift_l, keyboard.Key.shift_r))

    settings_hotkey_triggered = False
    if has_ctrl and has_shift:
        if (key_char_val and key_char_val.lower() == app.settings_hotkey_char) or \
           (vk_val and vk_val == 0x48): # 0x48 is the virtual-key code for 'H'
            settings_hotkey_triggered = True

    if settings_hotkey_triggered:
        app.master.after(0, app._open_settings_dialog)
        return

    # UI Toggle Hotkey Check (Ctrl+Shift+X)
    ui_toggle_hotkey_triggered = False
    if has_ctrl and has_shift:
        if vk_val == 0x58: # 0x58 is the virtual-key code for 'X'
            ui_toggle_hotkey_triggered = True

    if ui_toggle_hotkey_triggered:
        app.master.after(0, app._toggle_ui_visibility)
        return

    if key == app.hotkey_key and check_hotkey_modifiers_active(app):
        if not app.hotkey_active_for_release and (app.current_state == "initial" or app.current_state == "loading_model"):
            if app.current_state == "loading_model" and not app.model_loaded_event.is_set():
                return
            app.hotkey_active_for_release = True
            app.master.after(0, app._trigger_recording_start)

def on_global_key_release(app, key):
    original_hotkey_active_for_release = app.hotkey_active_for_release

    if original_hotkey_active_for_release and key == app.hotkey_key:
        if app.current_state == "listening":
            app.master.after(0, app._trigger_recording_stop_and_process)
        app.hotkey_active_for_release = False

    is_a_configured_modifier = False
    try:
        key_name = key.name
        if key_name.endswith(('_l', '_r')):
            key_name = key_name[:-2] # Normalize 'ctrl_l' to 'ctrl'
        if key_name in app.hotkey_modifiers:
            is_a_configured_modifier = True
    except AttributeError:
        pass

    if original_hotkey_active_for_release and is_a_configured_modifier:
        app.currently_pressed_keys.remove(key)
        if not check_hotkey_modifiers_active(app):
             if app.current_state == "listening":
                app.master.after(0, app._trigger_recording_stop_and_process)
             app.hotkey_active_for_release = False
        app.currently_pressed_keys.add(key)

    try:
        app.currently_pressed_keys.remove(key)
    except KeyError:
        pass 