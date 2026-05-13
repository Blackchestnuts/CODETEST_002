"""
Common/log_util.py — 日志统一封装

核心功能：
  - 控制台 + 文件双输出
  - 自动按日期生成日志文件
  - 统一日志格式
  - 从 log_config.ini 读取日志配置

设计要点：
  - 使用 Python 内置 logging 模块
  - 单例模式，整个框架共用一个 Logger
  - 日志级别可配置
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from typing import Optional

from Common.path_util import LOGS_DIR, LOG_CONFIG_INI_PATH


# ---------------------------------------------------------------------------
# 日志格式
# ---------------------------------------------------------------------------
_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class LogUtil:
    """
    统一日志工具类。

    使用方式：
        logger = LogUtil.get_logger()
        logger.info("请求成功")
        logger.error("断言失败")
    """

    _logger: Optional[logging.Logger] = None

    @classmethod
    def get_logger(cls, name: str = "ApiAutoTest") -> logging.Logger:
        """
        获取 Logger 实例（单例模式）。

        Args:
            name: Logger 名称

        Returns:
            logging.Logger: Logger 实例
        """
        if cls._logger is not None:
            return cls._logger

        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # 避免重复添加 Handler
        if logger.handlers:
            cls._logger = logger
            return logger

        # 日志格式
        formatter = logging.Formatter(_LOG_FORMAT, _DATE_FORMAT)

        # 控制台 Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 文件 Handler（按日期命名）
        try:
            os.makedirs(LOGS_DIR, exist_ok=True)
        except Exception:
            pass

        log_file = os.path.join(
            LOGS_DIR,
            f"api_test_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        cls._logger = logger
        logger.info(f"[log_util] 日志初始化完成，日志文件: {log_file}")
        return logger


# ---------------------------------------------------------------------------
# 便捷函数：全局可直接使用
# ---------------------------------------------------------------------------

def debug(msg: str) -> None:
    """输出 DEBUG 级别日志。"""
    LogUtil.get_logger().debug(msg)


def info(msg: str) -> None:
    """输出 INFO 级别日志。"""
    LogUtil.get_logger().info(msg)


def warning(msg: str) -> None:
    """输出 WARNING 级别日志。"""
    LogUtil.get_logger().warning(msg)


def error(msg: str) -> None:
    """输出 ERROR 级别日志。"""
    LogUtil.get_logger().error(msg)


def critical(msg: str) -> None:
    """输出 CRITICAL 级别日志。"""
    LogUtil.get_logger().critical(msg)
