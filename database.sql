CREATE DATABASE IF NOT EXISTS BookOrderDB;
USE BookOrderDB;

-- 教材表
CREATE TABLE Textbooks (
    ISBN CHAR(17) PRIMARY KEY,
    book_name VARCHAR(100) NOT NULL,
    author VARCHAR(50) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    CONSTRAINT chk_price CHECK (price > 0),
    CONSTRAINT chk_stock CHECK (stock >= 0)
);

-- 班级表
CREATE TABLE Classes (
    class_id INT PRIMARY KEY AUTO_INCREMENT,
    class_name VARCHAR(50) UNIQUE NOT NULL
);

-- 学期表
CREATE TABLE Semesters (
    semester_id VARCHAR(20) PRIMARY KEY,
    semester_name VARCHAR(50) NOT NULL
);

-- 用书计划表
CREATE TABLE ClassBookPlans (
    plan_id INT PRIMARY KEY AUTO_INCREMENT,
    class_id INT NOT NULL,
    textbook_id CHAR(17) NOT NULL,
    semester_id VARCHAR(20) NOT NULL,
    required_quantity INT NOT NULL CHECK (required_quantity > 0),
    FOREIGN KEY (class_id) REFERENCES Classes(class_id) ON DELETE CASCADE,
    FOREIGN KEY (textbook_id) REFERENCES Textbooks(ISBN) ON DELETE CASCADE,
    FOREIGN KEY (semester_id) REFERENCES Semesters(semester_id) ON DELETE CASCADE,
    UNIQUE KEY unique_plan (class_id, textbook_id, semester_id)
);

-- 学生表
CREATE TABLE Students (
    student_id INT PRIMARY KEY AUTO_INCREMENT,
    student_name VARCHAR(50) NOT NULL,
    class_id INT NOT NULL,
    FOREIGN KEY (class_id) REFERENCES Classes(class_id)
);

-- 领书登记表
CREATE TABLE PickupRecords (
    record_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    textbook_id CHAR(17) NOT NULL,
    pickup_quantity INT NOT NULL CHECK (pickup_quantity > 0),
    pickup_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES Students(student_id),
    FOREIGN KEY (textbook_id) REFERENCES Textbooks(ISBN)
);

-- 创建索引（优化查询用）
CREATE INDEX idx_pickup_student_date ON PickupRecords(student_id, pickup_date);
CREATE FULLTEXT INDEX ft_book_name ON Textbooks(book_name);

INSERT INTO Textbooks VALUES
('978-7-111-12345-6', '数据结构（C语言版）', '严蔚敏', 45.00, 20),
('978-7-302-45678-9', '计算机组成原理', '唐朔飞', 52.00, 5);  -- 这一本库存只有5，低于10，后面预警视图能看到

INSERT INTO Classes VALUES (1, '计科2101'), (2, '软件2102');
INSERT INTO Semesters VALUES ('2025-2026-1', '2025-2026学年第一学期');
INSERT INTO Students VALUES (1, '张三', 1), (2, '李四', 1);
INSERT INTO ClassBookPlans (class_id, textbook_id, semester_id, required_quantity) VALUES
(1, '978-7-111-12345-6', '2025-2026-1', 30);


-- 创建视图（库存低于10）
CREATE OR REPLACE VIEW LowStockView AS
SELECT ISBN, book_name, author, stock
FROM Textbooks
WHERE stock < 10;

-- 创建存储过程（用 $$ 替代 //）
CREATE PROCEDURE GetClassBookListAndCost(
    IN p_class_name VARCHAR(50),
    IN p_semester_id VARCHAR(20),
    OUT total_cost DECIMAL(10,2)
)
BEGIN
    SELECT
        t.book_name,
        t.author,
        t.price,
        cbp.required_quantity,
        (t.price * cbp.required_quantity) AS subtotal
    FROM ClassBookPlans cbp
    JOIN Textbooks t ON cbp.textbook_id = t.ISBN
    JOIN Classes c ON cbp.class_id = c.class_id
    WHERE c.class_name = p_class_name AND cbp.semester_id = p_semester_id;

    SELECT SUM(t.price * cbp.required_quantity) INTO total_cost
    FROM ClassBookPlans cbp
    JOIN Textbooks t ON cbp.textbook_id = t.ISBN
    JOIN Classes c ON cbp.class_id = c.class_id
    WHERE c.class_name = p_class_name AND cbp.semester_id = p_semester_id;

    IF total_cost IS NULL THEN SET total_cost = 0; END IF;
END;

CREATE TRIGGER trg_BeforePickup
BEFORE INSERT ON PickupRecords
FOR EACH ROW
BEGIN
    DECLARE v_available_stock INT;
    SELECT stock INTO v_available_stock
    FROM Textbooks
    WHERE ISBN = NEW.textbook_id;

    IF v_available_stock < NEW.pickup_quantity THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = '库存不足，无法完成领书登记！';
    ELSE
        UPDATE Textbooks
        SET stock = stock - NEW.pickup_quantity
        WHERE ISBN = NEW.textbook_id;
    END IF;
END;

-- 测试代码
-- 已知 '978-7-111-12345-6' 库存是20，我们领5本，应该成功
INSERT INTO PickupRecords (student_id, textbook_id, pickup_quantity) VALUES (1, '978-7-111-12345-6', 5);
-- 去查一下库存，发现变成了15
SELECT stock FROM Textbooks WHERE ISBN = '978-7-111-12345-6';

-- 再试一次领20本（此时库存只有15），会报错：库存不足，无法完成领书登记！
INSERT INTO PickupRecords (student_id, textbook_id, pickup_quantity) VALUES (1, '978-7-111-12345-6', 20);

-- 调用存储过程
CALL GetClassBookListAndCost('计科2101', '2025-2026-1', @total);
-- 查看输出的总费用
SELECT @total;

SELECT * FROM LowStockView;

-- 创建专用应用程序用户 (仅赋予必要的增删改查权限)
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'SecurePass123!';
GRANT SELECT, INSERT, UPDATE, DELETE ON BookOrderDB.* TO 'app_user'@'localhost';
GRANT EXECUTE ON PROCEDURE BookOrderDB.GetClassBookListAndCost TO 'app_user'@'localhost';
REVOKE DROP, ALTER, CREATE ON BookOrderDB.* FROM 'app_user'@'localhost';
FLUSH PRIVILEGES;