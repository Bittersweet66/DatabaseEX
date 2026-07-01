# login_dialog.py
import hashlib
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from db_utils import DBConnection

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户登录")
        self.setModal(True)
        self.resize(300, 150)
        self.role = None   # 登录成功后的角色
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        form.addRow("用户名:", self.username_edit)
        form.addRow("密码:", self.password_edit)
        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.do_login)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def do_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入用户名和密码")
            return

        # 计算密码哈希（SHA-256）
        hasher = hashlib.sha256()
        hasher.update(password.encode('utf-8'))
        pwd_hash = hasher.hexdigest()

        try:
            conn = DBConnection.get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role FROM Users WHERE username = %s AND password_hash = %s",
                (username, pwd_hash)
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                self.role = row[0]
                self.accept()
            else:
                QMessageBox.warning(self, "登录失败", "用户名或密码错误")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"数据库查询失败: {e}")