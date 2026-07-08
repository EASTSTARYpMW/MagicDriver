# -*- coding: utf-8 -*-
"""Cookie 持久化读写"""

from __future__ import annotations

import json
import os
from typing import Optional

from DrissionPage import ChromiumPage


class CookieSettings:
    """Cookie 文件读写"""

    @staticmethod
    def cookie_path(file_name: str, file_root: Optional[str] = None) -> str:
        root = file_root or "cookies"
        return os.path.join(root, f"{file_name}.json")

    @staticmethod
    def load_cookies(file_name: str, file_root: Optional[str] = None) -> list | dict:
        """从文件加载 cookie"""
        path = CookieSettings.cookie_path(file_name, file_root)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"cookie 文件不存在: {path}")

    @staticmethod
    def save_cookies(page: ChromiumPage, file_name: str, file_root: Optional[str] = None) -> None:
        """保存当前页面的 cookie 到文件"""
        path = CookieSettings.cookie_path(file_name, file_root)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(page.cookies(), f)


# 兼容旧类名
Cookie_settings = CookieSettings
