"""
Common/ini_util.py — INI 配置文件读取封装

核心功能：读取 Conf/config.ini 配置文件，获取数据库账号、接口域名、全局参数。
设计要点：
  - 使用 configparser 安全读取 INI 文件
  - 支持默认值，避免配置缺失导致崩溃
  - 单例模式，全局只加载一次
"""
from __future__ import annotations

import configparser
from typing import Any

from Common.path_util import CONFIG_INI_PATH


class IniUtil:
    """
    INI 配置文件读取工具类。

    使用方式：
        base_url = IniUtil.get("api", "base_url")
        db_host = IniUtil.get("database", "host")
    """

    _config: configparser.ConfigParser | None = None

    @classmethod
    def _load_config(cls) -> configparser.ConfigParser:
        """
        加载 INI 配置文件（单例）。

        Returns:
            configparser.ConfigParser: 配置解析器
        """
        if cls._config is not None:
            return cls._config

        config = configparser.ConfigParser()
        config.read(CONFIG_INI_PATH, encoding="utf-8")
        cls._config = config
        return config

    @classmethod
    def get(cls, section: str, key: str, default: str = "") -> str:
        """
        获取配置值。

        Args:
            section: INI 节名称，如 api、database、global
            key: 配置键名
            default: 默认值

        Returns:
            str: 配置值
        """
        config = cls._load_config()
        try:
            return config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default

    @classmethod
    def get_int(cls, section: str, key: str, default: int = 0) -> int:
        """
        获取整数配置值。

        Args:
            section: INI 节名称
            key: 配置键名
            default: 默认值

        Returns:
            int: 配置值
        """
        value = cls.get(section, key, "")
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @classmethod
    def get_float(cls, section: str, key: str, default: float = 0.0) -> float:
        """
        获取浮点数配置值。

        Args:
            section: INI 节名称
            key: 配置键名
            default: 默认值

        Returns:
            float: 配置值
        """
        value = cls.get(section, key, "")
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    @classmethod
    def get_sections(cls) -> list[str]:
        """
        获取所有节名称。

        Returns:
            list[str]: 节名称列表
        """
        config = cls._load_config()
        return config.sections()

    @classmethod
    def get_section(cls, section: str) -> dict[str, str]:
        """
        获取指定节的所有配置。

        Args:
            section: INI 节名称

        Returns:
            dict[str, str]: 配置字典
        """
        config = cls._load_config()
        try:
            return dict(config.items(section))
        except configparser.NoSectionError:
            return {}
