# dialogs.py
import pymysql
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from db_utils import DBConnection
from utils import populate_table

# ---------- 1. 教材入库对话框 ----------
class AddTextbookDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("教材入库")
        self.setModal(True)
        self.resize(450, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 模式选择
        mode_group = QGroupBox("入库模式")
        mode_layout = QHBoxLayout()
        self.radio_new = QRadioButton("新教材（输入完整信息）")
        self.radio_existing = QRadioButton("已有教材（仅输入ISBN增加库存）")
        self.radio_new.setChecked(True)
        mode_layout.addWidget(self.radio_new)
        mode_layout.addWidget(self.radio_existing)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # 表单
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)

        self.isbn_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.author_edit = QLineEdit()
        self.price_edit = QLineEdit()
        self.stock_edit = QLineEdit()

        form_layout.addRow("ISBN", self.isbn_edit)
        form_layout.addRow("书名", self.name_edit)
        form_layout.addRow("作者", self.author_edit)
        form_layout.addRow("价格", self.price_edit)
        form_layout.addRow("库存数量", self.stock_edit)

        layout.addWidget(form_widget)

        # 提示
        self.hint_label = QLabel("新教材模式：请填写所有字段；已有教材模式：只需填写 ISBN 和库存数量（增加的数量）")
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.hint_label)

        # 按钮
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.do_insert)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        # 信号连接
        self.radio_new.toggled.connect(self.on_mode_changed)
        self.on_mode_changed()

    def on_mode_changed(self):
        is_new = self.radio_new.isChecked()
        self.name_edit.setEnabled(is_new)
        self.author_edit.setEnabled(is_new)
        self.price_edit.setEnabled(is_new)
        if is_new:
            self.hint_label.setText("新教材模式：请填写所有字段，库存为初始库存。")
        else:
            self.hint_label.setText("已有教材模式：只需填写 ISBN 和要增加的库存数量。")

    def do_insert(self):
        isbn = self.isbn_edit.text().strip()
        stock_text = self.stock_edit.text().strip()
        if not isbn or not stock_text:
            QMessageBox.warning(self, "提示", "ISBN 和库存数量为必填项。")
            return
        try:
            stock = int(stock_text)
            if stock <= 0:
                QMessageBox.warning(self, "提示", "库存数量必须大于 0。")
                return
        except ValueError:
            QMessageBox.warning(self, "提示", "库存数量必须是整数。")
            return

        conn = None
        cur = None
        try:
            conn = DBConnection.get_conn()
            cur = conn.cursor()

            if self.radio_new.isChecked():
                name = self.name_edit.text().strip()
                author = self.author_edit.text().strip()
                price_text = self.price_edit.text().strip()
                if not name or not author or not price_text:
                    QMessageBox.warning(self, "提示", "新教材模式下，书名、作者、价格均为必填。")
                    return
                try:
                    price = float(price_text)
                except ValueError:
                    QMessageBox.warning(self, "提示", "价格必须是数字。")
                    return

                cur.execute(
                    "INSERT INTO Textbooks VALUES (%s, %s, %s, %s, %s)",
                    (isbn, name, author, price, stock)
                )
                conn.commit()
                QMessageBox.information(self, "成功", f"新教材 '{name}' 入库成功！")
                self.accept()
            else:
                # 检查教材是否存在
                cur.execute("SELECT ISBN FROM Textbooks WHERE ISBN = %s", (isbn,))
                if not cur.fetchone():
                    QMessageBox.warning(self, "提示", "该 ISBN 不存在，请先录入新教材。")
                    return  # 不关闭对话框，用户可以修改
                # 增加库存
                cur.execute("UPDATE Textbooks SET stock = stock + %s WHERE ISBN = %s", (stock, isbn))
                conn.commit()
                QMessageBox.information(self, "成功", f"教材 ISBN {isbn} 库存增加 {stock} 本。")
                self.accept()
        except Exception as e:
            if conn:
                conn.rollback()
            QMessageBox.critical(self, "错误", f"操作失败：{e}")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()


# ---------- 2. 库存管理对话框 ----------
class ManageStockDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("库存管理")
        self.setModal(True)
        self.resize(500, 400)
        self.books = []
        self.init_ui()
        self.load_books()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 选择教材
        self.combo = QComboBox()
        layout.addWidget(self.combo)

        # 当前信息
        info_group = QGroupBox("当前信息")
        info_layout = QFormLayout()
        self.lbl_isbn = QLabel()
        self.lbl_name = QLabel()
        self.lbl_author = QLabel()
        self.lbl_price = QLabel()
        self.lbl_stock = QLabel()
        info_layout.addRow("ISBN", self.lbl_isbn)
        info_layout.addRow("书名", self.lbl_name)
        info_layout.addRow("作者", self.lbl_author)
        info_layout.addRow("价格", self.lbl_price)
        info_layout.addRow("库存", self.lbl_stock)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 修改区域
        edit_group = QGroupBox("修改信息")
        edit_layout = QFormLayout()
        self.new_price = QLineEdit()
        self.new_stock = QLineEdit()
        edit_layout.addRow("新价格", self.new_price)
        edit_layout.addRow("新库存", self.new_stock)
        edit_group.setLayout(edit_layout)
        layout.addWidget(edit_group)

        # 按钮
        btn_update = QPushButton("更新教材信息")
        btn_update.clicked.connect(self.update_info)
        layout.addWidget(btn_update)

        # 信号
        self.combo.currentIndexChanged.connect(self.on_select)

    def load_books(self):
        try:
            rows = DBConnection.execute_query("SELECT ISBN, book_name, author, price, stock FROM Textbooks")
            if rows:
                self.books = rows
                self.combo.clear()
                for book in rows:
                    display = f"{book[1]} (ISBN: {book[0]})"
                    self.combo.addItem(display, book[0])
                self.on_select(0)
            else:
                QMessageBox.information(self, "提示", "当前没有教材可管理")
                self.reject()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载教材失败：{e}")
            self.reject()

    def on_select(self, index):
        if index < 0:
            return
        isbn = self.combo.currentData()
        for book in self.books:
            if book[0] == isbn:
                self.lbl_isbn.setText(book[0])
                self.lbl_name.setText(book[1])
                self.lbl_author.setText(book[2])
                self.lbl_price.setText(str(book[3]))
                self.lbl_stock.setText(str(book[4]))
                break

    def update_info(self):
        isbn = self.combo.currentData()
        price_text = self.new_price.text().strip()
        stock_text = self.new_stock.text().strip()
        if not price_text and not stock_text:
            QMessageBox.warning(self, "提示", "请至少修改一项")
            return

        updates = []
        params = []
        if price_text:
            try:
                float(price_text)
            except ValueError:
                QMessageBox.warning(self, "提示", "价格必须是数字")
                return
            updates.append("price = %s")
            params.append(float(price_text))
        if stock_text:
            try:
                int(stock_text)
            except ValueError:
                QMessageBox.warning(self, "提示", "库存必须是整数")
                return
            updates.append("stock = %s")
            params.append(int(stock_text))
        params.append(isbn)

        try:
            sql = f"UPDATE Textbooks SET {', '.join(updates)} WHERE ISBN = %s"
            DBConnection.execute_query(sql, params)
            QMessageBox.information(self, "成功", "教材信息更新成功！")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"更新失败：{e}")


# ---------- 3. 领书登记对话框 ----------
class PickupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("学生领书登记")
        self.setModal(True)
        self.resize(300, 200)
        layout = QFormLayout(self)
        self.stu_id = QLineEdit()
        self.isbn = QLineEdit()
        self.qty = QLineEdit()
        layout.addRow("学生ID", self.stu_id)
        layout.addRow("教材ISBN", self.isbn)
        layout.addRow("数量", self.qty)
        btn = QPushButton("确认领书")
        btn.clicked.connect(self.do_pickup)
        layout.addRow(btn)

    def do_pickup(self):
        try:
            stu_id = int(self.stu_id.text().strip())
            isbn = self.isbn.text().strip()
            qty = int(self.qty.text().strip())
            if qty <= 0:
                raise ValueError("数量必须大于0")
            # 插入领书记录，触发器自动减库存
            DBConnection.execute_query(
                "INSERT INTO PickupRecords (student_id, textbook_id, pickup_quantity) VALUES (%s, %s, %s)",
                (stu_id, isbn, qty)
            )
            QMessageBox.information(self, "成功", "领书成功！库存已自动更新。")
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "输入错误", str(e))
        except Exception as e:
            QMessageBox.critical(self, "领书失败", f"错误：{e}")