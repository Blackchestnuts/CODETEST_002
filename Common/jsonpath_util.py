"""
Common/jsonpath_util.py — jsonpath 数据提取封装

核心功能：传入响应 JSON 和 jsonpath 表达式，提取指定字段值。
用于接口关联场景：从上一个接口的响应中提取 token、user_id 等字段，
存入全局变量供后续接口引用。

设计要点：
  - 兼容 jsonpath 库和手动点号路径两种方式
  - 提取失败时返回 None 而非抛异常，保证流程不中断
  - 支持同时提取多个字段
"""
from __future__ import annotations

import json
from typing import Any

try:
    import jsonpath
    HAS_JSONPATH = True
except ImportError:
    HAS_JSONPATH = False
    print("[jsonpath_util] jsonpath 库未安装，将使用内置点号路径解析")


def extract(response_json: dict | list, expression: str) -> Any:
    """
    使用 jsonpath 表达式从响应 JSON 中提取数据。

    支持两种表达式格式：
      1. 标准 jsonpath：如 $.data.token、$.users[0].name
      2. 简化点号路径：如 data.token、users.0.name

    Args:
        response_json: 响应 JSON 数据（dict 或 list）
        expression: jsonpath 表达式

    Returns:
        Any: 提取到的值，提取失败返回 None
    """
    if not expression or not expression.strip():
        return None

    expression = expression.strip()

    # 方式1：使用 jsonpath 库
    if HAS_JSONPATH and expression.startswith("$"):
        try:
            result = jsonpath.jsonpath(response_json, expression)
            if result and len(result) > 0:
                value = result[0]
                print(f"[jsonpath_util] 提取成功: {expression} → {value}")
                return value
            else:
                print(f"[jsonpath_util] 提取为空: {expression}")
                return None
        except Exception as e:
            print(f"[jsonpath_util] jsonpath 提取异常: {expression} → {e}")

    # 方式2：使用内置点号路径解析
    return _extract_by_path(response_json, expression)


def extract_and_store(response_json: dict | list, expression: str, var_name: str) -> Any:
    """
    提取数据并自动存入全局变量。

    典型场景：Excel 中填写提取表达式和变量名，
    框架自动提取响应字段并存入全局变量，供后续接口引用。

    Args:
        response_json: 响应 JSON 数据
        expression: jsonpath 表达式
        var_name: 全局变量名

    Returns:
        Any: 提取到的值
    """
    if not expression or not var_name:
        return None

    value = extract(response_json, expression)

    if value is not None:
        from Common.global_data import GlobalData
        GlobalData.set(var_name, value)
        print(f"[jsonpath_util] 提取并存储: {expression} → {var_name} = {value}")
    else:
        print(f"[jsonpath_util] ⚠ 提取为空，未存储: {expression} → {var_name}")

    return value


def _extract_by_path(data: Any, path: str) -> Any:
    """
    内置点号路径解析器，不依赖第三方库。

    支持格式：
      - data.token → data["token"]
      - users.0.name → data["users"][0]["name"]
      - $.data.token → 去掉 $ 前缀后按点号解析

    Args:
        data: JSON 数据
        path: 点号分隔的路径

    Returns:
        Any: 提取到的值
    """
    # 去掉 $. 前缀
    if path.startswith("$."):
        path = path[2:]
    elif path.startswith("$"):
        path = path[1:]

    keys = path.split(".")
    current = data

    for key in keys:
        if current is None:
            return None

        # 尝试数组索引
        if isinstance(current, list):
            try:
                idx = int(key)
                current = current[idx]
                continue
            except (ValueError, IndexError):
                return None

        # 字典键访问
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None

    if current is not None:
        print(f"[jsonpath_util] 内置路径提取成功: {path} → {current}")

    return current
