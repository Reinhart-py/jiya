import sys
import traceback

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
        pass 

sys.excepthook = handle_exception

from gui.app import KiriApp

def main() -> None:
    app = KiriApp()
    app.mainloop()

if __name__ == "__main__":
    main()
