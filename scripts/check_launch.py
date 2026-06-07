import sys
import logging
from pathlib import Path

try:
    from scripts.repo_bootstrap import ensure_repo_root_on_sys_path
except ImportError:  # pragma: no cover - script entry fallback
    from repo_bootstrap import ensure_repo_root_on_sys_path

# Suppress logging during check to focus on startup results
logging.basicConfig(level=logging.ERROR)


def check_launch():
    """
    Automated startup check for SPC Platform.
    Confirms that the application can initialize and show the MainWindow 
    without crashing or raising exceptions.
    """
    print("--- SPC Platform: Startup Verification ---")
    
    # 1. Environment and Path Check
    project_root = str(
        ensure_repo_root_on_sys_path(Path(__file__).resolve().parents[1])
    )
    print(f"Project Root: {project_root}")

    try:
        from app.bootstrap.runtime_env import ensure_home_env

        ensure_home_env()
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer
        from app.ui.main_window import MainWindow
        from app.bootstrap.dpi import setup_high_dpi
        from app.ui.theme import apply_dark_theme
        
        print("Preflight: Modules imported successfully.")
        
        # 2. Qt Application Setup
        setup_high_dpi()
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
        
        # Apply theme (this checks QSS and token consistency)
        apply_dark_theme(app)
        
        # 3. Instantiate MainWindow (this triggers the bulk of UI initialization)
        print("Stage 1: Instantiating MainWindow...")
        window = MainWindow()
        
        # 4. Show Window (checks window rendering/geometry)
        print("Stage 2: Showing MainWindow...")
        window.show()
        
        # 5. Success and Exit
        # We wait 500ms to ensure any delayed initialization (like QTimers) 
        # doesn't crash the app immediately after showing.
        print("Stage 3: Launch sequence finished successfully. Validating for 500ms...")
        QTimer.singleShot(500, app.quit)
        app.exec()
        
        print("Result: [PASS] Application started and rendered successfully.")
        return 0

    except Exception as e:
        print("\n" + "="*50, file=sys.stderr)
        print("!!! STARTUP FAILURE DETECTED !!!", file=sys.stderr)
        print("="*50, file=sys.stderr)
        print(f"Error Type: {type(e).__name__}", file=sys.stderr)
        print(f"Error Message: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        print("="*50, file=sys.stderr)
        print("\nResult: [FAIL]", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(check_launch())
