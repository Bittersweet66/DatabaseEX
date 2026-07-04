# main_window.py
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from db_utils import DBConnection
from dialogs import AddTextbookDialog, ManageStockDialog, PickupDialog, PlanManagementDialog,BackupRestoreDialog
from utils import populate_table

class BookOrderSystem(QMainWindow):
    def __init__(self, role, parent=None):   # 增加 role 参数
        super().__init__(parent)
        self.role = role   # 保存角色
        self.setWindowTitle("教材订购管理系统 v2.0")
        self.setGeometry(200, 200, 1000, 600)
        self.init_ui()
        self.refresh_table()
        self.apply_permissions()   # 根据角色控制按钮

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)   # 水平主布局

        # ---------- 左侧按钮面板 ----------
        left_panel = QWidget()
        left_panel.setFixedWidth(160)               # 固定宽度，可根据文字调整
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignTop)       # 按钮靠上排列
        left_layout.setSpacing(8)                   # 按钮间距
        left_panel.setStyleSheet("""
        QPushButton {
            text-align: left;
            padding: 8px 10px;
            font-size: 12px;
            border: 1px solid #ccc;
            border-radius: 4px;
            background-color: #f9f9f9;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        QPushButton:disabled {
            color: #999;
            background-color: #f0f0f0;
        }
    """)

        # 创建所有功能按钮
        self.btn_all = QPushButton("📖 全部教材")
        self.btn_add = QPushButton("📚 教材入库")
        self.btn_stock = QPushButton("📦 库存管理")
        self.btn_pickup = QPushButton("📋 领书登记")
        self.btn_warning = QPushButton("⚠️ 余量预警")
        self.btn_print = QPushButton("🖨️ 班级采购清单")
        self.btn_plan = QPushButton("📝 用书计划")
        self.btn_backup = QPushButton("💾 备份/恢复")

        # 连接信号（使用 lambda 忽略 checked 参数）
        self.btn_all.clicked.connect(lambda: self.refresh_table())
        self.btn_add.clicked.connect(lambda: self.add_textbook())
        self.btn_stock.clicked.connect(lambda: self.manage_stock())
        self.btn_pickup.clicked.connect(lambda: self.pickup_book())
        self.btn_warning.clicked.connect(lambda: self.show_subscription_warning())
        self.btn_print.clicked.connect(lambda: self.print_class_list())
        self.btn_plan.clicked.connect(lambda: self.manage_plans())
        self.btn_backup.clicked.connect(lambda: self.backup_restore())

        # 添加到左侧布局
        left_layout.addWidget(self.btn_all)
        left_layout.addWidget(self.btn_add)
        left_layout.addWidget(self.btn_stock)
        left_layout.addWidget(self.btn_pickup)
        left_layout.addWidget(self.btn_warning)
        left_layout.addWidget(self.btn_print)
        left_layout.addWidget(self.btn_plan)
        left_layout.addWidget(self.btn_backup)

        # ---------- 搜索框（放在左侧底部） ----------
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入书名或ISBN")
        self.search_edit.returnPressed.connect(self.search_textbooks)

        self.search_btn = QPushButton("搜索")
        self.search_btn.clicked.connect(self.search_textbooks)

        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_edit, 1)
        search_layout.addWidget(self.search_btn)
        left_layout.addLayout(search_layout)

        left_layout.addStretch()   # 底部弹簧，使上方内容靠上

        # ---------- 右侧表格区域 ----------
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.table = QTableWidget()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        right_layout.addWidget(self.table)

        # 添加到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_widget, 1)   # 右侧占更多空间

        # 状态栏（不变）
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        

    # ---------- 刷新表格 ----------
    def refresh_table(self, query="SELECT * FROM Textbooks", params=()):
        self.search_edit.clear()   # 清空搜索框
        try:
            rows = DBConnection.execute_query(query, params, fetch_all=True)
            if rows:
                # 获取列名
                conn = DBConnection.get_conn()
                cursor = conn.cursor()
                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description]
                cursor.close()
                conn.close()
                populate_table(self.table, rows, columns)
                self.status_bar.showMessage(f"加载了 {len(rows)} 条记录")
            else:
                self.table.setRowCount(0)
                self.status_bar.showMessage("无数据")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查询失败：{e}")
        self.status_bar.showMessage("当前显示：全部教材")

    # ---------- 功能按钮 ----------
    def add_textbook(self):
        dialog = AddTextbookDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_table()

    def manage_stock(self):
        dialog = ManageStockDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_table()

    def pickup_book(self):
        dialog = PickupDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_table()

    def show_subscription_warning(self):
        query = """
        SELECT 
            t.ISBN,
            t.book_name,
            t.author,
            t.price,
            t.stock,
            COALESCE(SUM(cbp.required_quantity), 0) AS total_required,
            (t.stock - COALESCE(SUM(cbp.required_quantity), 0)) AS remaining
        FROM Textbooks t
        LEFT JOIN ClassBookPlans cbp ON t.ISBN = cbp.textbook_id
        GROUP BY t.ISBN
        HAVING remaining <= 10
        ORDER BY remaining
        """
        try:
            rows = DBConnection.execute_query(query, fetch_all=True)
            if not rows:
                QMessageBox.information(self, "余量预警", "所有教材库存充足，无预警！")
                return
            columns = ["ISBN", "书名", "作者", "价格", "库存", "总征订量", "剩余库存"]
            populate_table(self.table, rows, columns)
            self.status_bar.showMessage(f"余量预警：{len(rows)} 种教材库存不足（剩余≤10）")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查询失败：{e}")
        self.status_bar.showMessage("当前显示：余量预警")

    def print_class_list(self):
        class_name, ok1 = QInputDialog.getText(self, "班级采购清单", "请输入班级名称 (如 计科2101):")
        if not ok1:
            return
        semester, ok2 = QInputDialog.getText(self, "班级采购清单", "请输入学期ID (如 2025-2026-1):")
        if not ok2:
            return

        try:
            conn = DBConnection.get_conn()
            cursor = conn.cursor()
            cursor.execute("CALL GetClassBookListAndCost(%s, %s, @total)", (class_name, semester))
            rows = cursor.fetchall()
            if not rows:
                QMessageBox.information(self, "清单", "该班级本学期的采购计划为空。")
                cursor.close()
                conn.close()
                return
            cursor.execute("SELECT @total")
            total = cursor.fetchone()[0]
            if total is None:
                total = 0
            cursor.close()
            conn.close()

            text = f"班级：{class_name}  学期：{semester}\n"
            text += "=" * 60 + "\n"
            text += f"{'书名':<20} {'作者':<12} {'单价':>8} {'数量':>6} {'小计':>10}\n"
            text += "-" * 60 + "\n"
            for r in rows:
                text += f"{r[0]:<20} {r[1]:<12} {r[2]:>8.2f} {r[3]:>6} {r[4]:>10.2f}\n"
            text += "-" * 60 + "\n"
            text += f"总费用合计：{total:.2f} 元"

            msg = QMessageBox(self)
            msg.setWindowTitle("班级采购清单")
            msg.setText(text)
            msg.setTextInteractionFlags(Qt.TextSelectableByMouse)
            msg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取清单失败：{e}")

    def apply_permissions(self):
        """根据角色启用/禁用功能按钮"""
        if self.role == 'operator':
            self.btn_all.setEnabled(True)
            self.btn_add.setEnabled(True)
            self.btn_stock.setEnabled(True)
            self.btn_pickup.setEnabled(True)
            self.btn_warning.setEnabled(True)
            self.btn_print.setEnabled(True)
            self.btn_plan.setEnabled(True)
            self.btn_backup.setEnabled(True)
        else:  # viewer
            self.btn_all.setEnabled(True)
            self.btn_add.setEnabled(False)
            self.btn_stock.setEnabled(False)
            self.btn_pickup.setEnabled(False)
            self.btn_warning.setEnabled(True)
            self.btn_print.setEnabled(True)
            self.btn_plan.setEnabled(False)
            self.btn_backup.setEnabled(False)

        # 在每个可能修改数据的操作前再检查一次权限（防御性编程）
    def add_textbook(self):
        if self.role not in ('operator'):
            QMessageBox.warning(self, "权限不足", "您没有执行此操作的权限")
            return
        dialog = AddTextbookDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_table()

    def manage_stock(self):
        if self.role not in ('operator'):
            QMessageBox.warning(self, "权限不足", "您没有执行此操作的权限")
            return
        dialog = ManageStockDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_table()

    def pickup_book(self):
        if self.role not in ('operator'):
            QMessageBox.warning(self, "权限不足", "您没有执行此操作的权限")
            return
        dialog = PickupDialog(self)
        if dialog.exec_() == QDialog.Accepted:
                self.refresh_table()
    def manage_plans(self):
        if self.role not in ('operator',):
            QMessageBox.warning(self, "权限不足", "您没有执行此操作的权限")
            return
        dialog = PlanManagementDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_table()   # 可刷新，但计划变更不影响教材表，可不必刷新
    def backup_restore(self):
        if self.role not in ('operator',):
            QMessageBox.warning(self, "权限不足", "您没有执行此操作的权限")
            return
        dialog = BackupRestoreDialog(self)
        dialog.exec_()
    def search_textbooks(self):
        keyword = self.search_edit.text().strip()
        if not keyword:
            self.refresh_table()   # 空搜索则显示全部
            return
        # 使用全文索引或模糊查询
        query = """
        SELECT * FROM Textbooks
        WHERE book_name LIKE %s OR ISBN LIKE %s
        """
        like = f"%{keyword}%"
        try:
            rows = DBConnection.execute_query(query, (like, like), fetch_all=True)
            if rows:
                conn = DBConnection.get_conn()
                cursor = conn.cursor()
                cursor.execute(query, (like, like))
                columns = [desc[0] for desc in cursor.description]
                cursor.close()
                conn.close()
                populate_table(self.table, rows, columns)
                self.status_bar.showMessage(f"搜索结果：{len(rows)} 条记录")
            else:
                self.table.setRowCount(0)
                self.status_bar.showMessage("未找到匹配教材")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"搜索失败：{e}")