"""
Common/re_replace.py — 正则 #变量# 数据替换封装

核心功能：扫描字符串中的 #变量名# 占位符，
自动从全局变量（GlobalData）或 INI 配置中查找对应值进行替换。

典型场景：
  - Excel 中填写请求头 {"Authorization": "Bearer #token#"}
  - 框架执行时自动将 #token# 替换为 GlobalData 中存储的真实 Token
  - 支持多层嵌套替换，如 #base_url#/api/user
"""
from __future__ import annotations

import re
from typing import Any

from Common.global_data import GlobalData
from Common.ini_util import IniUtil


# ---------------------------------------------------------------------------
# 正则模式：匹配 #变量名#
# ---------------------------------------------------------------------------
_VARIABLE_PATTERN = re.compile(r"#(\w+)#")


def replace(data: Any) -> Any:
    """
    递归替换数据中的 #变量名# 占位符。

    支持替换的数据类型：
      - 字符串：扫描并替换所有 #变量名#
      - 字典：递归替换所有 value
      - 列表：递归替换所有元素
      - 其他类型：原样返回

    替换优先级：
      1. 全局变量（GlobalData）
      2. INI 配置文件（config.ini 中的 [global] 节）

    Args:
        data: 待替换的数据（任意类型）

    Returns:
        Any: 替换后的数据
    """
    if isinstance(data, str):
        return _replace_string(data)
    elif isinstance(data, dict):
        return {key: replace(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [replace(item) for item in data]
    else:
        return data


def _replace_string(text: str) -> str:
    """
    替换字符串中的 #变量名# 占位符。

    Args:
        text: 待替换的字符串

    Returns:
        str: 替换后的字符串
    """
    if "#" not in text:
        return text

    def _match_handler(match: re.Match) -> str:
        """单个 #变量名# 的替换处理函数。"""
        var_name: str = match.group(1)

        # 优先从全局变量获取
        if GlobalData.has(var_name):
            value = GlobalData.get(var_name)
            print(f"[re_replace] 替换 #{var_name}# → {value}（来源：全局变量）")
            return str(value)

        # 其次从 INI 配置的 [global] 节获取
        try:
            ini_value: str | None = IniUtil.get("global", var_name)
            if ini_value:
                print(f"[re_replace] 替换 #{var_name}# → {ini_value}（来源：config.ini）")
                return ini_value
        except Exception:
            pass

        # 找不到对应变量，保持原样不替换
        print(f"[re_replace] ⚠ 未找到变量 #{var_name}#，保持原样")
        return match.group(0)

    return _VARIABLE_PATTERN.sub(_match_handler, text)
