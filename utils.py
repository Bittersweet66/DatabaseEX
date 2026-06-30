# utils.py
from PyQt5.QtWidgets import QTableWidgetItem

def populate_table(table, rows, columns=None):
    """
    填充表格，自动适配列数
    """
    if not rows:
        table.setRowCount(0)
        return
    if columns is None:
        # 取第一行长度作为列数
        col_count = len(rows[0])
    else:
        col_count = len(columns)
    table.setColumnCount(col_count)
    if columns:
        table.setHorizontalHeaderLabels(columns)
    table.setRowCount(len(rows))
    for i, row in enumerate(rows):
        for j in range(col_count):
            table.setItem(i, j, QTableWidgetItem(str(row[j])))