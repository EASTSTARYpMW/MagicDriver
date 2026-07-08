# -*- coding: utf-8 -*-
"""MagicDriver 浏览器驱动核心"""

from __future__ import annotations

from typing import Callable, Optional

from DrissionPage import ChromiumOptions, ChromiumPage

from .anti_detection import AntiDetection, FingerprintProfile
from .cookie import CookieSettings


class Response:
    """网络响应封装"""

    def __init__(self):
        self.url: str | None = None
        self.method: Optional[str] = None
        self.status_code: int | None = None
        self.headers: Optional[dict] = {}
        self.params: Optional[str | dict] = None
        self.data: Optional[str | dict] = None
        self.body: Optional[str | dict] = None


class Driver:
    """
    基于 DrissionPage 的浏览器驱动。

    page 为 ChromiumPage 实例，co 为 ChromiumOptions 实例。
    文档: https://www.drissionpage.cn/
    """

    def __init__(
        self,
        filename: Optional[str] = None,
        file_root: Optional[str] = None,
        proxy: Optional[str] = None,
        digital_fingerprint: bool = False,
        listen_interface: bool = False,
    ):
        self.file_root: Optional[str] = file_root
        self.filename: Optional[str] = filename
        self.proxy: Optional[str] = proxy
        self.digital_fingerprint: bool = digital_fingerprint
        self.co: ChromiumOptions = ChromiumOptions()
        self.isLogin: Optional[bool] = None
        self.page: Optional[ChromiumPage] = None
        self.url: Optional[str] = None
        self.cookies: Optional[list | dict] = None
        self.listen_status: bool = False
        self.listen_interface: bool = listen_interface
        self.fingerprint_profile: Optional[FingerprintProfile] = None

        if digital_fingerprint:
            self.fingerprint_profile = AntiDetection.create_profile(seed=filename)

        if filename:
            self.cookies = CookieSettings.load_cookies(filename, self.file_root)

    def create_page(
        self,
        url: str,
        target: Optional[list] = None,
        func: Optional[Callable] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> None:
        """
        打开页面。若开启 listen_interface，可传入 target 与 func 监听网络请求。
        target 为 URL 片段列表，func 签名为 func(response, **kwargs)，返回 False 时停止监听。
        """
        self.url = url
        self._page_set()

        if self.listen_interface:
            self.page.listen.start()
            self.listen_status = True
        elif target:
            raise ValueError("未开启监听模式，请在创建 Driver 实例时设置 listen_interface=True")

        self._get_page()

        if self.listen_status and target and func:
            self.listen_page(target=target, func=func, timeout=timeout, **kwargs)

    def _apply_anti_detection(self) -> None:
        """应用反检测：启动参数 + CDP + 注入脚本"""
        profile = self.fingerprint_profile
        AntiDetection.apply_chromium_options(self.co, profile)

        if self.proxy:
            self.co.set_proxy(self.proxy)
        self.page = ChromiumPage(addr_or_opts=self.co)
        self._load_cookies_into_page()

        stealth_script = AntiDetection.build_stealth_script(profile)
        self.page.run_cdp("Page.addScriptToEvaluateOnNewDocument", source=stealth_script)
        AntiDetection.apply_cdp(self.page, profile)

    def _page_set(self) -> None:
        if self.digital_fingerprint:
            self._apply_anti_detection()
            return

        if self.proxy:
            self.co.set_proxy(self.proxy)
        self.page = ChromiumPage(addr_or_opts=self.co)
        self._load_cookies_into_page()

    def _load_cookies_into_page(self) -> None:
        if self.cookies:
            for cookie in self.cookies:
                self.page.set.cookies(cookie)
            self.isLogin = True
        else:
            self.isLogin = False

    def _get_page(self) -> None:
        self.page.get(self.url)

    def listen_page(
        self,
        target: list,
        func: Callable,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> None:
        for packet in self.page.listen.steps(timeout=timeout):
            for pattern in target:
                if pattern not in packet.url:
                    continue

                response = Response()
                response.url = packet.url
                response.method = packet.method
                response.status_code = packet.response.status
                response.headers = dict(packet.request.headers)

                if hasattr(packet.request, "postData") and packet.request.postData:
                    response.data = packet.request.postData

                if "?" in packet.url:
                    response.params = packet.url.split("?")[1]

                response.body = packet.response.body

                if func(response, **kwargs) is False:
                    return

    def save_cookies(self) -> None:
        """登录成功后保存当前页面的 cookie"""
        if not self.filename:
            raise ValueError("未设置 filename，无法保存 cookie")
        if not self.page:
            raise RuntimeError("浏览器未初始化，请先调用 create_page")
        CookieSettings.save_cookies(self.page, self.filename, self.file_root)
        self.isLogin = True
