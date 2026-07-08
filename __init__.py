# -*- coding: utf-8 -*-
"""
MagicDriver - 基于 DrissionPage 的浏览器自动化库

支持 Cookie 持久化、代理、反检测、网络请求监听。
文档: https://www.drissionpage.cn/


Signature: MagicDriver  E-mail: Hoplnd6@gmail.com   2025-9-25
此构造函数用于构造Driver对象，file_root为您的cookie保存根目录，filename为您的账户名，用于保存cookie，比如:
user@gmail.com.json或者YOUR_PHONE_NUMBER.json,你可以选择proxy参数来使用代理，比如: https://127.0.0.1:7860,
digital_fingerprint是启用完整反检测方案（隐藏 webdriver 标记、统一指纹、Canvas/WebGL/Audio 防护等），
你可以新增listen_interface参数为True，使浏览器开启监听模式
----
Driver实例里面的page的属性实际为Drissionpage的ChromiumPage对象，co为Drissionpage的ChromiumOptions对象
您可以参考官方文档 https://www.drissionpage.cn/
进行拓展功能
        
"""

from .anti_detection import AntiDetection, FingerprintProfile
from .cookie import CookieSettings, Cookie_settings
from .driver import Driver, Response

__all__ = [
    "Driver",
    "Response",
    "AntiDetection",
    "FingerprintProfile",
    "CookieSettings",
    "Cookie_settings",
]

__version__ = "0.1.0"
