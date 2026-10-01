import sys
from PySide6.QtWidgets import QApplication
from src.gui import KRemoverApp

if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    k_app = KRemoverApp()
    k_app.window.show()
    sys.exit(app.exec())