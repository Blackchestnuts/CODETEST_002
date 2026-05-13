"""
main.py — 框架入口文件

功能：
  1. 调用路径、日志初始化
  2. pytest 批量收集 TestCases 下所有用例
  3. 集成失败重跑配置
  4. 执行用例并生成 Allure 报告
  5. 统一控制整个框架一键运行
"""
from __future__ import annotations

import os
import subprocess
import sys

from Common.path_util import ensure_dirs, TESTCASES_DIR, ALLURE_REPORT_DIR, PROJECT_ROOT
from Common.log_util import info, error


def main() -> None:
    """
    框架入口主函数。

    执行流程：
      1. 初始化目录和日志
      2. 调用 pytest 执行用例
      3. 生成 Allure 报告
      4. 输出执行摘要
    """
    # 1. 初始化
    ensure_dirs()
    info("=" * 60)
    info("ApiAutoTest 框架启动")
    info("=" * 60)

    # 2. 构建 pytest 命令
    pytest_cmd = [
        sys.executable, "-m", "pytest",
        TESTCASES_DIR,
        "-v", "-s",
        f"--alluredir={ALLURE_REPORT_DIR}",
        "--reruns=2",              # 失败重跑2次
        "--reruns-delay=3",        # 重跑间隔3秒
        "-c", os.path.join(PROJECT_ROOT, "pytest.ini"),
    ]

    info(f"执行命令: {' '.join(pytest_cmd)}")

    # 3. 执行 pytest
    result = subprocess.run(pytest_cmd, cwd=PROJECT_ROOT)

    # 4. 生成 Allure HTML 报告
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

    # 5. 输出摘要
    info("=" * 60)
    if result.returncode == 0:
        info("✅ 所有测试通过！")
    else:
        info(f"⚠ 测试完成，退出码: {result.returncode}")
    info("=" * 60)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
