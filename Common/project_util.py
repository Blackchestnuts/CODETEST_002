"""
Common/project_util.py — 项目配置管理

核心功能：读取 Conf/projects.yaml，获取指定项目的配置信息。
支持 --project 参数切换不同接口项目。

设计要点：
  - 使用 PyYAML 解析 projects.yaml
  - 单例模式，全局只加载一次
  - 项目不存在时给出友好提示
"""
from __future__ import annotations

from typing import Any

import yaml

from Common.path_util import CONF_DIR
from Common.log_util import info, warning, error

import os


# ---------------------------------------------------------------------------
# 项目配置缓存
# ---------------------------------------------------------------------------
_projects_data: dict[str, Any] | None = None


def _load_projects() -> dict[str, Any]:
    """
    加载 projects.yaml 配置文件（单例）。

    Returns:
        dict[str, Any]: YAML 解析后的完整配置
    """
    global _projects_data

    if _projects_data is not None:
        return _projects_data

    yaml_path = os.path.join(CONF_DIR, "projects.yaml")

    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"项目配置文件不存在: {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        _projects_data = yaml.safe_load(f)

    info(f"[project_util] 加载项目配置: {yaml_path}")
    return _projects_data


def get_project_config(project_name: str) -> dict[str, str]:
    """
    获取指定项目的配置信息。

    Args:
        project_name: 项目名称，如 httpbin、jsonplaceholder

    Returns:
        dict[str, str]: 项目配置，包含 name、excel_file、base_url、description

    Raises:
        ValueError: 项目不存在或未启用时抛出
    """
    data = _load_projects()

    projects = data.get("projects", {})
    if project_name not in projects:
        available = list(projects.keys())
        raise ValueError(
            f"项目 '{project_name}' 未在 projects.yaml 中注册！\n"
            f"可用项目: {', '.join(available)}"
        )

    project = projects[project_name]

    # 检查是否启用
    if project.get("enabled", "Y") == "N":
        warning(f"项目 '{project_name}' 已禁用，仍可执行")

    config = {
        "name": project.get("name", project_name),
        "excel_file": project.get("excel_file", "api_test_data.xlsx"),
        "base_url": project.get("base_url", ""),
        "description": project.get("description", ""),
    }

    info(f"[project_util] 当前项目: {config['name']} | 域名: {config['base_url']} | Excel: {config['excel_file']}")
    return config


def get_default_project() -> str:
    """
    获取默认项目名称。

    Returns:
        str: 默认项目名称
    """
    data = _load_projects()
    return data.get("default_project", "httpbin")


def get_all_projects() -> list[dict[str, str]]:
    """
    获取所有已注册的项目列表。

    Returns:
        list[dict[str, str]]: 项目配置列表
    """
    data = _load_projects()
    projects = data.get("projects", {})
    result = []
    for name, config in projects.items():
        result.append({
            "name": name,
            "description": config.get("description", ""),
            "excel_file": config.get("excel_file", ""),
            "base_url": config.get("base_url", ""),
            "enabled": config.get("enabled", "Y"),
        })
    return result


def show_available_projects() -> None:
    """显示所有可用的项目配置（用于框架启动时日志输出）。"""
    projects = get_all_projects()
    default = get_default_project()

    info("可用项目列表:")
    info("-" * 55)
    for p in projects:
        marker = " (默认)" if p["name"] == default else ""
        status = "启用" if p["enabled"] == "Y" else "禁用"
        info(f"  项目: {p['name']}{marker}")
        info(f"    域名: {p['base_url']}")
        info(f"    Excel: {p['excel_file']}")
        info(f"    描述: {p['description']}")
        info(f"    状态: {status}")
        info("-" * 55)
