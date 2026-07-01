# main_window.py
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from db_utils import DBConnection
from dialogs import AddTextbookDialog, ManageStockDialog, PickupDialog
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
        layout = QVBoxLayout(central_widget)

        # 工具栏
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        # 为后续权限控制保存按钮引用
        self.btn_all = toolbar.addAction("📖 全部教材", self.refresh_table)
        self.btn_add = toolbar.addAction("📚 教材入库", self.add_textbook)
        self.btn_stock = toolbar.addAction("📦 库存管理", self.manage_stock)
        self.btn_pickup = toolbar.addAction("📋 领书登记", self.pickup_book)
        self.btn_warning = toolbar.addAction("⚠️ 余量预警", self.show_subscription_warning)
        self.btn_print = toolbar.addAction("🖨️ 班级采购清单", self.print_class_list)

        # 表格
        self.table = QTableWidget()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

        

    # ---------- 刷新表格 ----------
    def refresh_table(self, query="SELECT * FROM Textbooks", params=()):
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
                # 可以根据需求微调，例如允许操作员修改库存和领书
            elif self.role == 'viewer':
                self.btn_all.setEnabled(True)
                self.btn_add.setEnabled(False)
                self.btn_stock.setEnabled(False)
                self.btn_pickup.setEnabled(False)
                self.btn_warning.setEnabled(True)
                self.btn_print.setEnabled(True)

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