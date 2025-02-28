为了在本地 MySQL 数据库中创建一个新的数据库、用户和密码，并确保它们与 `test_db_uri` 中的连接一致，可以按照以下步骤操作：

### 1. 登录到 MySQL

首先，登录到 MySQL 服务器：

```bash
mysql -u root -p
```

然后输入 root 用户的密码。

### 2. 创建数据库

在 MySQL 中创建 `test_woniunote` 数据库：

```sql
CREATE DATABASE test_woniunote;
```

### 3. 创建用户

接着创建 `testuser` 用户，并为其设置密码为 `testpass`：

```sql
CREATE USER 'testuser'@'localhost' IDENTIFIED BY 'testpass';
```

### 4. 授予权限

授予 `testuser` 对 `test_woniunote` 数据库的所有权限：

```sql
GRANT ALL PRIVILEGES ON test_woniunote.* TO 'testuser'@'localhost';
```

### 5. 刷新权限

刷新权限，以便修改立即生效：

```sql
FLUSH PRIVILEGES;
```

### 6. 验证连接

现在你应该能够使用以下连接字符串连接到 `test_woniunote` 数据库：

```python
mysql+pymysql://testuser:testpass@localhost/test_woniunote
```

如果一切顺利，你的 MySQL 数据库、用户和密码已经设置好，并且与 `pytest.fixture` 中定义的连接 URI 一致。

如果你有其他问题或需要进一步的帮助，随时告诉我！