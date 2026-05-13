"""
Common/path_util.py — 项目路径统一管理

集中管理所有路径常量，其他模块统一从此处引用，
避免路径硬编码散落各处，确保项目迁移时只改一处。
"""
from __future__ import annotations

import os


# ---------------------------------------------------------------------------
# 核心路径常量
# ---------------------------------------------------------------------------

# 项目根目录（ApiAutoTest/）
PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Common 公共工具层
COMMON_DIR: str = os.path.join(PROJECT_ROOT, "Common")

# Conf 配置层
CONF_DIR: str = os.path.join(PROJECT_ROOT, "Conf")
CONFIG_INI_PATH: str = os.path.join(CONF_DIR, "config.ini")
LOG_CONFIG_INI_PATH: str = os.path.join(CONF_DIR, "log_config.ini")

# TestDatas 测试数据层
TESTDATAS_DIR: str = os.path.join(PROJECT_ROOT, "TestDatas")

# TestCases 测试用例层
TESTCASES_DIR: str = os.path.join(PROJECT_ROOT, "TestCases")

# Outputs 输出层
OUTPUTS_DIR: str = os.path.join(PROJECT_ROOT, "Outputs")
LOGS_DIR: str = os.path.join(OUTPUTS_DIR, "logs")
ALLURE_REPORT_DIR: str = os.path.join(OUTPUTS_DIR, "allure_report")


def ensure_dirs() -> None:
    """
    确保所有必要的输出目录存在。

    在框架启动时调用，自动创建 logs/ 和 allure_report/ 目录，
    避免首次运行时因目录不存在导致文件写入失败。
    """
    for dir_path in [LOGS_DIR, ALLURE_REPORT_DIR]:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            print(f"[path_util] 创建目录: {dir_path}")


def get_excel_path(file_name: str) -> str:
    """
    获取 TestDatas 目录下 Excel 文件的绝对路径。

    Args:
        file_name: Excel 文件名，如 api_test_data.xlsx

    Returns:
        str: Excel 文件的绝对路径
    """
    return os.path.join(TESTDATAS_DIR, file_name)
