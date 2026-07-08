# -*- coding: utf-8 -*-
"""命令行测试入口: python -m MagicDriver"""

from .driver import Driver


def _test_callback(response):
    print(response.body)


def main():
    driver = Driver(
        digital_fingerprint=True,
        listen_interface=True,
        proxy="http://127.0.0.1:8888",
    )
    driver.create_page(
        url="http://www.yalala.com/",
        target=["api/mbbrowser/coinrate", "api/mbbrowser/clientinfo"],
        func=_test_callback,
        timeout=3,
    )


if __name__ == "__main__":
    main()
