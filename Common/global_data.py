"""
Common/global_data.py — 全局变量管理

提供全局变量的存取能力，用于接口之间的数据传递。
典型场景：登录接口返回 token，提取后存入全局变量，
后续接口的请求头中通过 #token# 引用，框架自动替换。

设计要点：
  - 使用类变量 + 类方法，无需实例化即可使用
  - 线程安全：多线程环境下使用 threading.Lock 保护
  - 支持批量设置和清空
"""
from __future__ import annotations

import threading
from typing import Any


class GlobalData:
    """
    全局变量仓库。

    所有接口提取的变量统一存储在此类中，
    供正则替换模块（re_replace）在下一个接口请求前读取替换。
    """

    # 全局变量存储字典
    _data: dict[str, Any] = {}

    # 线程锁，确保多线程安全
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """
        存入全局变量。

        Args:
            key: 变量名
            value: 变量值
        """
        with cls._lock:
            cls._data[key] = value
            print(f"[global_data] 设置全局变量: {key} = {value}")

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        获取全局变量。

        Args:
            key: 变量名
            default: 变量不存在时的默认值

        Returns:
            Any: 变量值，不存在则返回 default
        """
        with cls._lock:
            value = cls._data.get(key, default)
            if value is not default and value is not None:
                print(f"[global_data] 读取全局变量: {key} = {value}")
            return value

    @classmethod
    def has(cls, key: str) -> bool:
        """
        判断全局变量是否存在。

        Args:
            key: 变量名

        Returns:
            bool: 是否存在
        """
        return key in cls._data

    @classmethod
    def set_all(cls, data: dict[str, Any]) -> None:
        """
        批量设置全局变量。

        Args:
            data: 变量字典
        """
        with cls._lock:
            cls._data.update(data)
            print(f"[global_data] 批量设置 {len(data)} 个全局变量")

    @classmethod
    def get_all(cls) -> dict[str, Any]:
        """
        获取所有全局变量的副本。

        Returns:
            dict[str, Any]: 全局变量字典副本
        """
        with cls._lock:
            return cls._data.copy()

    @classmethod
    def clear(cls) -> None:
        """清空所有全局变量。"""
        with cls._lock:
            cls._data.clear()
            print("[global_data] 已清空所有全局变量")
