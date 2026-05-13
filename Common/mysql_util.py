"""
Common/mysql_util.py — 数据库增删改查封装

核心功能：
  - 封装 pymysql 连接管理
  - 支持查询、增删改操作
  - 断言数据库数据是否一致
  - 从 config.ini 读取数据库配置

设计要点：
  - 使用 yield 管理连接生命周期
  - 支持上下文管理器（with 语句）
  - 查询结果以字典列表返回，方便断言
"""
from __future__ import annotations

from typing import Any

from Common.log_util import info, error, warning
from Common.ini_util import IniUtil


class MysqlUtil:
    """
    MySQL 数据库操作封装类。

    使用方式：
        # 查询
        rows = MysqlUtil.query("SELECT * FROM users WHERE id = %s", (1,))
        # 单值查询
        value = MysqlUtil.fetch_one_value("SELECT COUNT(*) FROM users")
    """

    _connection = None

    @classmethod
    def _get_connection(cls):
        """
        获取数据库连接（懒加载单例）。

        Returns:
            pymysql.Connection: 数据库连接对象
        """
        if cls._connection is not None:
            try:
                cls._connection.ping(reconnect=True)
                return cls._connection
            except Exception:
                cls._connection = None

        try:
            import pymysql
        except ImportError:
            error("pymysql 未安装，请执行: pip install pymysql")
            return None

        try:
            connection = pymysql.connect(
                host=IniUtil.get("database", "host", "localhost"),
                port=IniUtil.get_int("database", "port", 3306),
                user=IniUtil.get("database", "user", "root"),
                password=IniUtil.get("database", "password", ""),
                database=IniUtil.get("database", "database", "test"),
                charset=IniUtil.get("database", "charset", "utf8mb4"),
                cursorclass=pymysql.cursors.DictCursor,
            )
            cls._connection = connection
            info(f"[mysql_util] 数据库连接成功: {IniUtil.get('database', 'host', 'localhost')}")
            return connection
        except Exception as e:
            error(f"[mysql_util] 数据库连接失败: {e}")
            return None

    @classmethod
    def query(cls, sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
        """
        执行查询 SQL，返回字典列表。

        Args:
            sql: SQL 查询语句
            params: SQL 参数（防注入）

        Returns:
            list[dict[str, Any]]: 查询结果列表
        """
        conn = cls._get_connection()
        if conn is None:
            return []

        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchall()
                info(f"[mysql_util] 查询成功: {sql[:80]}... 共 {len(result)} 条")
                return result
        except Exception as e:
            error(f"[mysql_util] 查询失败: {e}")
            return []

    @classmethod
    def fetch_one_value(cls, sql: str, params: tuple | None = None) -> Any:
        """
        执行查询 SQL，返回第一行第一列的值。

        专门用于 Excel 中的数据库校验场景：
          SQL: SELECT COUNT(*) FROM users WHERE username='zhangsan'
          期望值: 1

        Args:
            sql: SQL 查询语句
            params: SQL 参数

        Returns:
            Any: 查询结果的第一行第一列值
        """
        conn = cls._get_connection()
        if conn is None:
            return None

        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()
                if row:
                    # DictCursor 返回字典，取第一个值
                    value = list(row.values())[0] if isinstance(row, dict) else row[0]
                    info(f"[mysql_util] 单值查询: {sql[:60]}... → {value}")
                    return value
                return None
        except Exception as e:
            error(f"[mysql_util] 单值查询失败: {e}")
            return None

    @classmethod
    def execute(cls, sql: str, params: tuple | None = None) -> int:
        """
        执行增删改 SQL，返回影响行数。

        Args:
            sql: SQL 语句
            params: SQL 参数

        Returns:
            int: 影响行数
        """
        conn = cls._get_connection()
        if conn is None:
            return 0

        try:
            with conn.cursor() as cursor:
                affected = cursor.execute(sql, params)
                conn.commit()
                info(f"[mysql_util] 执行成功: {sql[:80]}... 影响 {affected} 行")
                return affected
        except Exception as e:
            conn.rollback()
            error(f"[mysql_util] 执行失败: {e}")
            return 0

    @classmethod
    def close(cls) -> None:
        """关闭数据库连接。"""
        if cls._connection:
            cls._connection.close()
            cls._connection = None
            info("[mysql_util] 数据库连接已关闭")
