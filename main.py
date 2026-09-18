import sys
import traceback

# ◈ FATAL CRASH INTERCEPTOR ◈
# If the app dies in --windowed mode, this catches the error and forces a popup
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
        
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Critical Engine Failure", f"The UI failed to boot due to an internal error:\n\n{err_msg}")
    except Exception:
        pass  # Fallback if tkinter itself is broken

sys.excepthook = handle_exception


from gui.app import JiyaApp

def main() -> None:
    app = JiyaApp()
    app.mainloop()

if __name__ == "__main__":
    main()
