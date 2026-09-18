import sys
from gui.app import JiyaApp

def main() -> None:
    try:
        app = JiyaApp()
        app.mainloop()
    except KeyboardInterrupt:
        print("\nApplication closed by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal UI error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
