# main.py
import sys
from PyQt5.QtWidgets import QApplication
from main_window import BookOrderSystem

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BookOrderSystem()
    window.show()
    sys.exit(app.exec_())