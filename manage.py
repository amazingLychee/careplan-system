#!/usr/bin/env python
"""Django 的命令行工具入口，比如 runserver、migrate 都从这里走。"""
import os
import sys


def main():
    # 告诉 Django 用哪个 settings 文件
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "careplan_project.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
