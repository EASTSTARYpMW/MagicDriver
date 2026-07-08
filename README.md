# MagicDriver

基于 [DrissionPage](https://www.drissionpage.cn/) 封装的浏览器自动化库，适用于需要登录态、动态页面或 API 监听的爬虫场景。

**版本：** 0.1.0  
**依赖：** Python 3.10+、DrissionPage 4.0+、Chromium 内核浏览器（Chrome / Edge）

---

## 目录

- [功能特性](#功能特性)
- [安装](#安装)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [API 参考](#api-参考)
  - [Driver](#driver)
  - [Response](#response)
  - [CookieSettings](#cookiesettings)
  - [AntiDetection](#antidetection)
  - [FingerprintProfile](#fingerprintprofile)
- [使用示例](#使用示例)
- [反检测方案](#反检测方案)
- [网络监听](#网络监听)
- [Cookie 管理](#cookie-管理)
- [扩展 DrissionPage](#扩展-drissionpage)
- [常见问题](#常见问题)

---

## 功能特性

| 功能 | 说明 |
|------|------|
| 浏览器自动化 | 封装 DrissionPage `ChromiumPage`，支持页面导航与元素操作 |
| Cookie 持久化 | 按账号文件名读写 JSON，支持自定义存储目录 |
| 代理 | 支持 HTTP/HTTPS 代理 |
| 反检测 | 隐藏 webdriver 标记、统一浏览器指纹、Canvas/WebGL/Audio 防护 |
| 网络监听 | 拦截匹配 URL 片段的请求，通过回调处理响应体 |

---

## 安装

### 开发模式（推荐）

在项目根目录执行：

```bash
pip install -e .
```

### 仅安装依赖

```bash
pip install DrissionPage
```

---

## 项目结构

```
MagicDriver/
├── __init__.py          # 公开 API 导出
├── __main__.py          # 命令行入口
├── driver.py            # Driver、Response
├── anti_detection.py    # 反检测与指纹配置
├── cookie.py            # Cookie 读写
└── README.md            # 本文档
```

---

## 快速开始

```python
from MagicDriver import Driver

# 创建驱动（启用反检测 + 账号 Cookie）
driver = Driver(
    filename="my_account",
    digital_fingerprint=True,
)

# 打开页面
driver.create_page(url="https://example.com")

# 手动完成登录后，保存 Cookie
driver.save_cookies()
```

---

## API 参考

### Driver

浏览器驱动主类。

#### 构造函数

```python
Driver(
    filename: str | None = None,
    file_root: str | None = None,
    proxy: str | None = None,
    digital_fingerprint: bool = False,
    listen_interface: bool = False,
)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `filename` | `str` | `None` | 账号标识，用于 Cookie 文件名（如 `user@gmail.com`） |
| `file_root` | `str` | `None` | Cookie 存储根目录，默认 `cookies/` |
| `proxy` | `str` | `None` | 代理地址，如 `http://127.0.0.1:8888` |
| `digital_fingerprint` | `bool` | `False` | 是否启用完整反检测方案 |
| `listen_interface` | `bool` | `False` | 是否开启网络请求监听 |

#### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `page` | `ChromiumPage` | DrissionPage 页面对象，可直接操作 DOM |
| `co` | `ChromiumOptions` | 浏览器启动配置 |
| `isLogin` | `bool` | 是否已加载/保存 Cookie |
| `url` | `str` | 当前访问的 URL |
| `fingerprint_profile` | `FingerprintProfile` | 反检测指纹配置（启用时） |

#### 方法

##### `create_page(url, target=None, func=None, timeout=None, **kwargs)`

打开指定 URL，可选开启网络监听。

```python
driver.create_page(
    url="https://example.com",
    target=["/api/user"],   # 可选：监听的 URL 片段
    func=callback,          # 可选：匹配到请求时的回调
    timeout=30,             # 可选：监听超时（秒），默认一直监听
)
```

##### `listen_page(target, func, timeout=None, **kwargs)`

单独启动网络监听（通常由 `create_page` 内部调用）。

##### `save_cookies()`

将当前浏览器 Cookie 保存到 `{file_root}/{filename}.json`。

---

### Response

网络响应封装，由监听回调接收。

| 属性 | 类型 | 说明 |
|------|------|------|
| `url` | `str` | 请求完整 URL |
| `method` | `str` | HTTP 方法（GET、POST 等） |
| `status_code` | `int` | 响应状态码 |
| `headers` | `dict` | 请求头 |
| `params` | `str` | URL 查询参数字符串 |
| `data` | `str \| dict` | POST 请求体 |
| `body` | `str \| dict` | 响应体 |

---

### CookieSettings

Cookie 文件读写工具类。

```python
from MagicDriver import CookieSettings

# 加载
cookies = CookieSettings.load_cookies("my_account", file_root="cookies")

# 保存（需传入 ChromiumPage 实例）
CookieSettings.save_cookies(driver.page, "my_account", file_root="cookies")
```

> 兼容旧版类名：`Cookie_settings = CookieSettings`

Cookie 文件路径规则：`{file_root}/{filename}.json`

---

### AntiDetection

反检测配置与注入，通常由 `Driver(digital_fingerprint=True)` 自动调用。

```python
from MagicDriver import AntiDetection

# 生成指纹（相同 seed 得到相同配置）
profile = AntiDetection.create_profile(seed="my_account")

# 手动应用到 ChromiumOptions
co = ChromiumOptions()
AntiDetection.apply_chromium_options(co, profile)
```

| 方法 | 说明 |
|------|------|
| `create_profile(seed)` | 生成会话级指纹配置 |
| `apply_chromium_options(co, profile)` | 设置 Chromium 启动参数 |
| `apply_cdp(page, profile)` | 通过 CDP 设置时区、语言、UA 等 |
| `build_stealth_script(profile)` | 生成注入脚本字符串 |

---

### FingerprintProfile

单次会话内保持一致的浏览器指纹对象。

主要字段：`user_agent`、`platform`、`timezone`、`locale`、`languages`、`screen_width`、`screen_height`、`webgl_vendor`、`webgl_renderer`、`device_memory`、`hardware_concurrency` 等。

传入 `filename` 作为 seed 时，同一账号每次启动指纹保持一致。

---

## 使用示例

### 基础爬取

```python
from MagicDriver import Driver

driver = Driver(digital_fingerprint=True)
driver.create_page(url="https://example.com")

# 直接使用 DrissionPage API 操作页面
title = driver.page.title
print(title)
```

### 带 Cookie 复用

```python
from MagicDriver import Driver

driver = Driver(
    filename="user@gmail.com",
    file_root="cookies",
    digital_fingerprint=True,
)

driver.create_page(url="https://example.com/dashboard")

if not driver.isLogin:
    # 首次使用：手动登录后保存
    input("请在浏览器中完成登录，按回车继续...")
    driver.save_cookies()
```

### 代理 + 反检测

```python
from MagicDriver import Driver

driver = Driver(
    filename="my_account",
    proxy="http://127.0.0.1:8888",
    digital_fingerprint=True,
)
driver.create_page(url="https://example.com")
```

### 监听 API 响应

```python
from MagicDriver import Driver

def on_api(response, **kwargs):
    print(f"[{response.status_code}] {response.url}")
    print(response.body)
    return False  # 返回 False 停止监听

driver = Driver(
    digital_fingerprint=True,
    listen_interface=True,
)
driver.create_page(
    url="https://example.com",
    target=["/api/user/info", "/api/data"],
    func=on_api,
    timeout=60,
)
```

### 命令行测试

```bash
python -m MagicDriver
```

---

## 反检测方案

启用 `digital_fingerprint=True` 后，库会在三个层面施加防护：

### 1. Chromium 启动参数

- 禁用 `AutomationControlled` 特征
- WebRTC IP 泄露防护
- 随机窗口尺寸与语言

### 2. CDP 命令

- 时区覆盖（`Emulation.setTimezoneOverride`）
- 语言覆盖（`Emulation.setLocaleOverride`）
- User-Agent 覆盖（`Network.setUserAgentOverride`）
- 设备尺寸覆盖（`Emulation.setDeviceMetricsOverride`）

### 3. JS 注入脚本

在新文档加载前注入，覆盖以下检测点：

| 检测点 | 处理方式 |
|--------|----------|
| `navigator.webdriver` | 删除/置为 undefined |
| `cdc_` 等自动化变量 | 清理 window 上的残留 |
| `window.chrome` | 补齐 runtime、loadTimes 等 |
| `navigator.plugins` | 模拟 Chrome PDF 插件 |
| `navigator.platform` | 与 UA 保持一致 |
| Canvas 指纹 | 固定 seed 噪声 |
| WebGL 指纹 | 统一 vendor/renderer |
| AudioContext 指纹 | Analyser 微扰 |
| ClientRects | 固定微扰 |
| `Intl.DateTimeFormat` | 时区 hook |
| `Function.prototype.toString` | 伪装为 `[native code]` |

### 指纹一致性

- 同一 `filename` 作为 seed，每次启动生成相同指纹
- UA、platform、WebGL、分辨率、时区等字段互相匹配，避免矛盾暴露

### 验证反检测效果

可访问以下站点自检：

- [bot.sannysoft.com](https://bot.sannysoft.com)
- [browserleaks.com](https://browserleaks.com)

---

## 网络监听

### 工作流程

```
create_page()
  ├── 启动 listen（listen_interface=True）
  ├── 访问目标 URL
  └── listen_page() 循环匹配 target 中的 URL 片段
        └── 调用 func(response, **kwargs)
              └── 返回 False → 停止监听
```

### 注意事项

1. 必须在构造 `Driver` 时设置 `listen_interface=True`
2. `target` 为 URL **子串**列表，如 `"/api/user"` 会匹配所有包含该片段的请求
3. 每次匹配都会创建新的 `Response` 对象，无状态残留
4. `timeout` 单位为秒，`None` 表示一直监听直到回调返回 `False`

---

## Cookie 管理

### 文件格式

Cookie 以 JSON 数组形式存储：

```
cookies/
└── my_account.json
```

### 典型流程

```
首次使用                    后续使用
   │                          │
   ▼                          ▼
无 Cookie 文件            加载已有 Cookie
   │                          │
   ▼                          ▼
手动登录                  自动注入 Cookie
   │                          │
   ▼                          ▼
save_cookies()            直接访问目标页
```

### 自定义存储路径

```python
driver = Driver(
    filename="account_001",
    file_root="D:/my_cookies",
)
# Cookie 文件：D:/my_cookies/account_001.json
```

---

## 扩展 DrissionPage

`Driver.page` 即为 DrissionPage 的 `ChromiumPage` 对象，可直接使用其全部 API：

```python
driver = Driver(digital_fingerprint=True)
driver.create_page(url="https://example.com")

# 元素查找
elem = driver.page.ele("#username")
elem.input("my_user")

# 点击
driver.page.ele("#login-btn").click()

# 执行 JS
driver.page.run_js("return document.title")

# 截图
driver.page.get_screenshot(path="screenshot.png")

# 更多用法见 DrissionPage 官方文档
# https://www.drissionpage.cn/
```

`Driver.co` 为 `ChromiumOptions`，可在 `create_page` 之前自定义：

```python
driver = Driver()
driver.co.headless()          # 无头模式
driver.co.incognito()         # 无痕模式
driver.create_page(url="...")
```

---

## 常见问题

### Q: 导入报错 `ModuleNotFoundError: No module named 'MagicDriver'`

在项目根目录执行 `pip install -e .` 安装包。

### Q: 反检测开启后仍被识别

- 确认代理 IP 与指纹时区/语言匹配
- 同一账号始终传入相同的 `filename` 保持指纹一致
- 部分站点检测手段超出 JS 层，需配合人工行为模拟

### Q: Cookie 加载失败

```
FileNotFoundError: cookie 文件不存在: cookies/my_account.json
```

首次使用属正常，登录后调用 `save_cookies()` 即可。

### Q: 监听模式报错

```
ValueError: 未开启监听模式，请在创建 Driver 实例时设置 listen_interface=True
```

构造 `Driver` 时需传入 `listen_interface=True`。

### Q: 与 requests 爬虫如何选择

| 场景 | 推荐方案 |
|------|----------|
| 静态 HTML 页面 | `requests` + BeautifulSoup |
| 需要登录 / JS 渲染 | MagicDriver |
| 需要拦截 XHR/Fetch API | MagicDriver + 网络监听 |

---

## 公开 API 一览

```python
from MagicDriver import (
    Driver,              # 浏览器驱动
    Response,            # 网络响应
    AntiDetection,       # 反检测工具
    FingerprintProfile,  # 指纹配置
    CookieSettings,      # Cookie 读写
    Cookie_settings,     # CookieSettings 别名（兼容）
)

print(__import__("MagicDriver").__version__)  # 0.1.0
```
