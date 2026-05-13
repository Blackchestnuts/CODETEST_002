"""
main.py — 框架入口文件

功能：
  1. 调用路径、日志初始化
  2. 支持 --project 参数切换不同接口项目
  3. pytest 批量收集 TestCases 下所有用例
  4. 集成失败重跑配置
  5. 执行用例并生成 Allure 报告
  6. 统一控制整个框架一键运行

使用方式：
  python3 main.py                           # 默认项目（httpbin）
  python3 main.py --project=jsonplaceholder # 指定项目
  python3 main.py --project=httpbin         # 指定项目
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

from Common.path_util import ensure_dirs, TESTCASES_DIR, ALLURE_REPORT_DIR, PROJECT_ROOT
from Common.log_util import info, error
from Common.ini_util import IniUtil


def parse_args() -> argparse.Namespace:
    """
    解析命令行参数。

    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(description="ApiAutoTest 接口自动化框架")
    parser.add_argument(
        "--project",
        type=str,
        default="httpbin",
        help="指定测试项目名称，对应 config.ini 中的 [project_项目名] 节 (默认: httpbin)",
    )
    return parser.parse_args()


def show_available_projects() -> None:
    """显示所有可用的项目配置。"""
    info("可用项目列表:")
    info("-" * 50)
    for section in IniUtil.get_sections():
        if section.startswith("project_"):
            project_name = section.replace("project_", "")
            excel_file = IniUtil.get(section, "excel_file", "")
            base_url = IniUtil.get(section, "base_url", "")
            description = IniUtil.get(section, "description", "")
            info(f"  项目: {project_name}")
            info(f"    域名: {base_url}")
            info(f"    Excel: {excel_file}")
            info(f"    描述: {description}")
            info("-" * 50)


def main() -> None:
    """
    框架入口主函数。

    执行流程：
      1. 解析命令行参数
      2. 初始化目录和日志
      3. 显示可用项目
      4. 调用 pytest 执行用例
      5. 生成 Allure 报告
      6. 输出执行摘要
    """
    # 1. 解析参数
    args = parse_args()
    project_name: str = args.project

    # 2. 初始化
    ensure_dirs()
    info("=" * 60)
    info(f"ApiAutoTest 框架启动 | 项目: {project_name}")
    info("=" * 60)

    # 3. 显示可用项目
    show_available_projects()

    # 4. 验证项目配置
    section = f"project_{project_name}"
    if not IniUtil.get(section, "excel_file"):
        error(f"项目 '{project_name}' 未在 config.ini 中配置！")
        error(f"请在 config.ini 中添加 [project_{project_name}] 节")
        error("可用项目: " + ", ".join(
            s.replace("project_", "") for s in IniUtil.get_sections() if s.startswith("project_")
        ))
        sys.exit(1)

    excel_file = IniUtil.get(section, "excel_file")
    base_url = IniUtil.get(section, "base_url")
    info(f"当前项目: {project_name}")
    info(f"  接口域名: {base_url}")
    info(f"  用例文件: {excel_file}")

    # 5. 构建 pytest 命令
    pytest_cmd = [
        sys.executable, "-m", "pytest",
        TESTCASES_DIR,
        "-v", "-s",
        f"--project={project_name}",
        f"--alluredir={ALLURE_REPORT_DIR}",
        "--reruns=2",              # 失败重跑2次
        "--reruns-delay=3",        # 重跑间隔3秒
        "-c", os.path.join(PROJECT_ROOT, "pytest.ini"),
    ]

    info(f"执行命令: {' '.join(pytest_cmd)}")

    # 6. 执行 pytest
    result = subprocess.run(pytest_cmd, cwd=PROJECT_ROOT)

    # 7. 生成 Allure HTML 报告
    try:
        allure_cmd = [
            "allure", "generate",
            ALLURE_REPORT_DIR,
            "-o", os.path.join(PROJECT_ROOT, "Outputs", "allure_html"),
            "--clean",
        ]
        subprocess.run(allure_cmd, cwd=PROJECT_ROOT, capture_output=True)
        info("Allure HTML 报告生成成功")
    except FileNotFoundError:
        info("Allure 命令未安装，跳过 HTML 报告生成")
    except Exception as e:
        error(f"Allure 报告生成失败: {e}")

    # 8. 输出摘要
    info("=" * 60)
    if result.returncode == 0:
        info(f"所有测试通过！项目: {project_name}")
    else:
        info(f"测试完成，退出码: {result.returncode} | 项目: {project_name}")
    info("=" * 60)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
