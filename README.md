# DatabaseEX
## 环境准备
- Windows/Linux
- Mysql
- python 3.11(or upper)
- pymysql
- PyQt5
- PyQt5-tools
## 运行命令
```bash
python main.py
```

#### 安装依赖
首先安装pymysql
```bash
pip install pymysql
```
然后安装pyqt5
```bash
pip install PyQt5
pip install PyQt5-tools
```
### 基于用户的访问控制
目前用户：

('operator', SHA2('123456', 256), 'operator'),

('viewer',  SHA2('123456', 256), 'viewer');

#### 用户权限表

| 功能模块                 | 库存操作员 (operator) | 查看者 (viewer) |
|--------------------------|:---------------------:|:---------------:|
| 查看全部教材             | ✔                     | ✔               |
| 教材入库（新增/增加库存）| ✔                     | ✘               |
| 库存管理（修改价格/库存）| ✔                     | ✘               |
| 领书登记（消耗库存）     | ✔                     | ✘               |
| 余量预警（低库存查询）   | ✔                     | ✔               |
| 班级采购清单（只读）     | ✔                     | ✔               |
| 征订计划                | ✔                     | ✘               |
| 备份与恢复              | ✔                     | ✘               |

> **说明**：  
> - ✔ 表示该角色可使用此功能。  
> - ✘ 表示该角色无权限，按钮将被禁用或操作时提示权限不足。  
> - 库存操作员拥有全部读写权限，查看者仅拥有只读权限（查看、预警、清单）。
