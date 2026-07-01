# main.py
import sys
from PyQt5.QtWidgets import QApplication, QDialog   # ← 添加 QDialog
from login_dialog import LoginDialog
from main_window import BookOrderSystem

if __name__ == "__main__":
    app = QApplication(sys.argv)

    login = LoginDialog()
    if login.exec_() != QDialog.Accepted:
        sys.exit(0)

    role = login.role
    window = BookOrderSystem(role)
    window.show()
    sys.exit(app.exec_())