# dialogs.py
import pymysql
import subprocess
import os
from datetime import datetime
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

# ---------- 4. 用书计划管理对话框 ----------
class PlanManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用书计划管理（教材征订）")
        self.setModal(True)
        self.resize(700, 500)
        self.init_ui()
        self.load_plans()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 操作区域
        form_layout = QHBoxLayout()
        self.class_combo = QComboBox()
        self.class_combo.addItem("请选择班级")
        self.semester_combo = QComboBox()
        self.semester_combo.addItem("请选择学期")
        self.textbook_combo = QComboBox()
        self.textbook_combo.addItem("请选择教材")
        self.qty_edit = QLineEdit()
        self.qty_edit.setPlaceholderText("数量")
        btn_add = QPushButton("添加计划")
        btn_add.clicked.connect(self.add_plan)

        form_layout.addWidget(QLabel("班级:"))
        form_layout.addWidget(self.class_combo)
        form_layout.addWidget(QLabel("学期:"))
        form_layout.addWidget(self.semester_combo)
        form_layout.addWidget(QLabel("教材:"))
        form_layout.addWidget(self.textbook_combo)
        form_layout.addWidget(QLabel("数量:"))
        form_layout.addWidget(self.qty_edit)
        form_layout.addWidget(btn_add)
        layout.addLayout(form_layout)

        # 计划列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["序号", "班级", "学期", "教材", "数量"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        # 删除按钮
        btn_del = QPushButton("删除选中计划")
        btn_del.clicked.connect(self.delete_plan)
        layout.addWidget(btn_del)

        # 加载基础数据（班级、学期、教材下拉框）
        self.load_combos()

    def load_combos(self):
        try:
            # 加载班级
            rows = DBConnection.execute_query("SELECT class_id, class_name FROM Classes")
            for cid, name in rows:
                self.class_combo.addItem(name, cid)
            # 加载学期
            rows = DBConnection.execute_query("SELECT semester_id, semester_name FROM Semesters")
            for sid, name in rows:
                self.semester_combo.addItem(name, sid)
            # 加载教材
            rows = DBConnection.execute_query("SELECT ISBN, book_name FROM Textbooks")
            for isbn, name in rows:
                self.textbook_combo.addItem(name, isbn)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载基础数据失败：{e}")

    def load_plans(self):
        sql = """
        SELECT cbp.plan_id, c.class_name, s.semester_name, t.book_name, cbp.required_quantity
        FROM ClassBookPlans cbp
        JOIN Classes c ON cbp.class_id = c.class_id
        JOIN Semesters s ON cbp.semester_id = s.semester_id
        JOIN Textbooks t ON cbp.textbook_id = t.ISBN
        """
        try:
            rows = DBConnection.execute_query(sql, fetch_all=True)
            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                # row 结构: (plan_id, class_name, semester_name, book_name, required_quantity)
                # 第一列显示序号（行号+1）
                seq_item = QTableWidgetItem(str(i + 1))
                seq_item.setData(Qt.UserRole, row[0])   # 存储真实 plan_id
                self.table.setItem(i, 0, seq_item)
                
                # 其他列正常填充
                self.table.setItem(i, 1, QTableWidgetItem(row[1]))  # 班级
                self.table.setItem(i, 2, QTableWidgetItem(row[2]))  # 学期
                self.table.setItem(i, 3, QTableWidgetItem(row[3]))  # 教材
                self.table.setItem(i, 4, QTableWidgetItem(str(row[4])))  # 数量
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载计划失败：{e}")

    def add_plan(self):
        class_id = self.class_combo.currentData()
        semester_id = self.semester_combo.currentData()
        textbook_id = self.textbook_combo.currentData()
        qty_text = self.qty_edit.text().strip()
        if class_id is None or semester_id is None or textbook_id is None:
            QMessageBox.warning(self, "提示", "请完整选择班级、学期和教材")
            return
        try:
            qty = int(qty_text)
            if qty <= 0:
                raise ValueError
        except:
            QMessageBox.warning(self, "提示", "数量必须为正整数")
            return

        try:
            # 插入计划（检查唯一性由数据库约束保证）
            DBConnection.execute_query(
                "INSERT INTO ClassBookPlans (class_id, textbook_id, semester_id, required_quantity) VALUES (%s, %s, %s, %s)",
                (class_id, textbook_id, semester_id, qty)
            )
            QMessageBox.information(self, "成功", "用书计划添加成功")
            self.load_plans()
            self.qty_edit.clear()
        except Exception as e:
            # 如果违反唯一约束，提示用户
            if "Duplicate entry" in str(e):
                QMessageBox.warning(self, "提示", "该班级、学期、教材的计划已存在，请勿重复添加")
            else:
                QMessageBox.critical(self, "错误", f"添加失败：{e}")

    def delete_plan(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选中要删除的计划行")
            return
        # 从第一列的 data 中获取真实 plan_id
        plan_id_item = self.table.item(current_row, 0)
        if not plan_id_item:
            return
        plan_id = plan_id_item.data(Qt.UserRole)
        if plan_id is None:
            QMessageBox.warning(self, "错误", "无法获取计划ID")
            return
        reply = QMessageBox.question(self, "确认删除", f"确定删除序号 {current_row+1} 的计划吗？",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                DBConnection.execute_query("DELETE FROM ClassBookPlans WHERE plan_id = %s", (plan_id,))
                QMessageBox.information(self, "成功", "计划已删除")
                self.load_plans()   # 刷新列表，序号重新连续排列
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败：{e}")
import os
from datetime import datetime
from PyQt5.QtWidgets import QFileDialog

# ---------- 5. 备份与恢复对话框 ----------
class BackupRestoreDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("数据库备份与恢复")
        self.setModal(True)
        self.resize(400, 200)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 备份按钮
        btn_backup = QPushButton("备份整个数据库")
        btn_backup.clicked.connect(self.do_backup)
        layout.addWidget(btn_backup)

        # 恢复按钮
        btn_restore = QPushButton("从备份文件恢复")
        btn_restore.clicked.connect(self.do_restore)
        layout.addWidget(btn_restore)

        # 提示
        lbl = QLabel("注意：恢复操作将覆盖现有数据，请谨慎操作。\n备份文件为SQL格式，可选择部分表恢复。")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: gray;")
        layout.addWidget(lbl)

        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)

    def do_backup(self):
        # 选择保存路径
        default_name = f"BookOrderDB_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        file_path, _ = QFileDialog.getSaveFileName(self, "保存备份文件", default_name, "SQL files (*.sql)")
        if not file_path:
            return

        # 从 config.py 读取数据库配置
        from config import DB_CONFIG
        host = DB_CONFIG.get('host', 'localhost')
        user = DB_CONFIG.get('user', 'root')
        password = DB_CONFIG.get('password', '')
        database = DB_CONFIG.get('database', 'BookOrderDB')

        # 构造 mysqldump 命令
        cmd = [
            'mysqldump',
            f'--host={host}',
            f'--user={user}',
            f'--password={password}',
            '--databases', database,
            '--single-transaction',
            '--routines',   # 备份存储过程/函数
            '--triggers',
            '--add-drop-database'
        ]
        try:
            self.status_label.setText("正在备份，请稍候...")
            QApplication.processEvents()
            with open(file_path, 'w', encoding='utf-8') as f:
                subprocess.run(cmd, stdout=f, check=True, stderr=subprocess.PIPE)
            self.status_label.setText(f"备份成功！文件保存在：{file_path}")
            QMessageBox.information(self, "成功", f"数据库备份完成！\n文件：{file_path}")
        except subprocess.CalledProcessError as e:
            self.status_label.setText("备份失败")
            QMessageBox.critical(self, "错误", f"备份失败：{e.stderr.decode() if e.stderr else '未知错误'}")
        except Exception as e:
            self.status_label.setText("备份失败")
            QMessageBox.critical(self, "错误", f"备份异常：{e}")

    def do_restore(self):
        # 选择备份文件
        file_path, _ = QFileDialog.getOpenFileName(self, "选择备份文件", "", "SQL files (*.sql)")
        if not file_path:
            return

        reply = QMessageBox.question(self, "确认恢复",
                                     "恢复操作将删除当前数据库并重新创建，数据将被覆盖！\n确定继续吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        from config import DB_CONFIG
        host = DB_CONFIG.get('host', 'localhost')
        user = DB_CONFIG.get('user', 'root')
        password = DB_CONFIG.get('password', '')
        database = DB_CONFIG.get('database', 'BookOrderDB')

        # mysql 命令用于执行 SQL 文件
        cmd = [
            'mysql',
            f'--host={host}',
            f'--user={user}',
            f'--password={password}',
            database
        ]
        try:
            self.status_label.setText("正在恢复，请稍候...")
            QApplication.processEvents()
            with open(file_path, 'r', encoding='utf-8') as f:
                subprocess.run(cmd, stdin=f, check=True, stderr=subprocess.PIPE)
            self.status_label.setText("恢复成功！")
            QMessageBox.information(self, "成功", "数据库恢复完成！")
            # 恢复后刷新主界面
            self.parent().refresh_table() if self.parent() else None
        except subprocess.CalledProcessError as e:
            self.status_label.setText("恢复失败")
            QMessageBox.critical(self, "错误", f"恢复失败：{e.stderr.decode() if e.stderr else '未知错误'}")
        except Exception as e:
            self.status_label.setText("恢复失败")
            QMessageBox.critical(self, "错误", f"恢复异常：{e}")