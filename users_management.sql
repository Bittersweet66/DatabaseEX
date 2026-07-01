--此部分内容只是database.sql中用户表部分的拷贝品
--仅用于进行用户数据的管理
USE BookOrderDB;
--建表，不要重复建表
CREATE TABLE IF NOT EXISTS Users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash CHAR(64) NOT NULL,
    role ENUM('admin', 'operator', 'viewer') NOT NULL DEFAULT 'viewer',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
--插入用户
INSERT INTO Users (username, password_hash, role) VALUES
('admin',   SHA2('123456', 256), 'admin'),
('operator', SHA2('123456', 256), 'operator'),
('viewer',  SHA2('123456', 256), 'viewer');