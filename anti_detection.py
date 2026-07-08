# -*- coding: utf-8 -*-
"""浏览器反检测：Chromium 启动参数、CDP 与注入脚本"""

from __future__ import annotations

import json
import random
from typing import Optional

from DrissionPage import ChromiumOptions, ChromiumPage


# 预设指纹模板，UA / platform / WebGL 等字段保持一致
_PROFILE_TEMPLATES = [
    {
        "platform": "Win32",
        "oscpu": None,
        "vendor": "Google Inc.",
        "webgl_vendor": "Google Inc. (Intel)",
        "webgl_renderer": "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "user_agents": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        ],
        "languages": [["zh-CN", "zh", "en-US", "en"], ["zh-CN", "zh"]],
        "timezones": ["Asia/Shanghai", "Asia/Hong_Kong"],
        "resolutions": [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864},
        ],
    },
    {
        "platform": "MacIntel",
        "oscpu": None,
        "vendor": "Google Inc.",
        "webgl_vendor": "Google Inc. (Apple)",
        "webgl_renderer": "ANGLE (Apple, ANGLE Metal Renderer: Apple M1, Unspecified Version)",
        "user_agents": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        ],
        "languages": [["zh-CN", "zh", "en-US", "en"]],
        "timezones": ["Asia/Shanghai", "Asia/Tokyo"],
        "resolutions": [
            {"width": 1440, "height": 900},
            {"width": 1680, "height": 1050},
        ],
    },
]


class FingerprintProfile:
    """单次会话内保持一致的浏览器指纹"""

    def __init__(self, seed: Optional[str] = None):
        rng = random.Random(seed)
        template = rng.choice(_PROFILE_TEMPLATES)

        resolution = rng.choice(template["resolutions"])
        languages = rng.choice(template["languages"])

        self.user_agent: str = rng.choice(template["user_agents"])
        self.platform: str = template["platform"]
        self.vendor: str = template["vendor"]
        self.webgl_vendor: str = template["webgl_vendor"]
        self.webgl_renderer: str = template["webgl_renderer"]
        self.languages: list[str] = languages
        self.locale: str = languages[0]
        self.timezone: str = rng.choice(template["timezones"])
        self.screen_width: int = resolution["width"]
        self.screen_height: int = resolution["height"]
        self.avail_height: int = resolution["height"] - rng.choice([40, 48, 56])
        self.color_depth: int = rng.choice([24, 30])
        self.device_memory: int = rng.choice([4, 8, 16])
        self.hardware_concurrency: int = rng.choice([4, 8, 12, 16])
        self.max_touch_points: int = 0
        self.canvas_seed: float = rng.random()
        self.audio_seed: float = rng.random()
        self.client_rects_noise: float = rng.uniform(0.00001, 0.00005)

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class AntiDetection:
    """反检测配置与注入"""

    CHROME_ARGS = [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-popup-blocking",
        "--disable-dev-shm-usage",
        "--webrtc-ip-handling-policy=disable_non_proxied_udp",
        "--force-webrtc-ip-handling-policy",
    ]

    @staticmethod
    def create_profile(seed: Optional[str] = None) -> FingerprintProfile:
        """生成指纹；相同 seed 得到相同配置，便于账号复用"""
        return FingerprintProfile(seed)

    @staticmethod
    def apply_chromium_options(co: ChromiumOptions, profile: FingerprintProfile) -> None:
        """应用 Chromium 启动参数"""
        for arg in AntiDetection.CHROME_ARGS:
            co.set_argument(arg)

        co.set_user_agent(profile.user_agent)
        co.set_argument(f"--window-size={profile.screen_width},{profile.screen_height}")
        co.set_argument(f"--lang={profile.locale}")

        # 关闭自动化扩展提示
        co.set_pref("credentials_enable_service", False)
        co.set_pref("profile.password_manager_enabled", False)
        co.set_pref("webrtc.ip_handling_policy", "disable_non_proxied_udp")
        co.set_pref("webrtc.multiple_routes_enabled", False)
        co.set_pref("webrtc.nonproxied_udp_enabled", False)

    @staticmethod
    def apply_cdp(page: ChromiumPage, profile: FingerprintProfile) -> None:
        """通过 CDP 设置时区、语言等"""
        page.run_cdp("Emulation.setTimezoneOverride", timezoneId=profile.timezone)
        page.run_cdp("Emulation.setLocaleOverride", locale=profile.locale)
        page.run_cdp(
            "Network.setUserAgentOverride",
            userAgent=profile.user_agent,
            acceptLanguage=",".join(f"{lang};q={1 - i * 0.1:.1f}" for i, lang in enumerate(profile.languages)),
            platform=profile.platform,
        )
        page.run_cdp(
            "Emulation.setDeviceMetricsOverride",
            width=profile.screen_width,
            height=profile.screen_height,
            deviceScaleFactor=1,
            mobile=False,
        )

    @staticmethod
    def build_stealth_script(profile: FingerprintProfile) -> str:
        """构建在新文档加载前注入的反检测脚本"""
        cfg = {
            "platform": profile.platform,
            "vendor": profile.vendor,
            "languages": profile.languages,
            "locale": profile.locale,
            "timezone": profile.timezone,
            "screenWidth": profile.screen_width,
            "screenHeight": profile.screen_height,
            "availHeight": profile.avail_height,
            "colorDepth": profile.color_depth,
            "deviceMemory": profile.device_memory,
            "hardwareConcurrency": profile.hardware_concurrency,
            "maxTouchPoints": profile.max_touch_points,
            "webglVendor": profile.webgl_vendor,
            "webglRenderer": profile.webgl_renderer,
            "canvasSeed": profile.canvas_seed,
            "audioSeed": profile.audio_seed,
            "clientRectsNoise": profile.client_rects_noise,
        }
        cfg_json = json.dumps(cfg, ensure_ascii=False)

        return f"""
(() => {{
    'use strict';
    const CFG = {cfg_json};
    const UNMASKED_VENDOR_WEBGL = 37445;
    const UNMASKED_RENDERER_WEBGL = 37446;

    const nativeToString = Function.prototype.toString;
    const nativeCache = new Map();
    const markNative = (fn, name) => {{
        nativeCache.set(fn, `function ${{name || fn.name || ''}}() {{ [native code] }}`);
    }};
    Function.prototype.toString = new Proxy(nativeToString, {{
        apply(target, thisArg, args) {{
            if (nativeCache.has(thisArg)) {{
                return nativeCache.get(thisArg);
            }}
            return Reflect.apply(target, thisArg, args);
        }},
    }});
    markNative(Function.prototype.toString, 'toString');

    const defineProp = (obj, prop, value) => {{
        try {{
            Object.defineProperty(obj, prop, {{
                get: () => value,
                configurable: true,
            }});
        }} catch (e) {{}}
    }};

    const patchGetter = (obj, prop, value) => {{
        try {{
            const desc = Object.getOwnPropertyDescriptor(obj, prop);
            if (!desc || desc.configurable) {{
                Object.defineProperty(obj, prop, {{
                    get: () => value,
                    configurable: true,
                }});
            }}
        }} catch (e) {{}}
    }};

    // 移除 webdriver 标记
    try {{
        delete Object.getPrototypeOf(navigator).webdriver;
    }} catch (e) {{}}
    patchGetter(navigator, 'webdriver', undefined);

    // 清理自动化残留变量
    for (const key of Object.keys(window)) {{
        if (/^(cdc_|__webdriver|__driver|__selenium|__fxdriver|__chrome)/i.test(key)) {{
            try {{ delete window[key]; }} catch (e) {{}}
        }}
    }}

    // 补齐 chrome 对象
    if (!window.chrome) {{
        window.chrome = {{}};
    }}
    window.chrome.runtime = window.chrome.runtime || {{
        connect: () => ({{}}),
        sendMessage: () => ({{}}),
        id: undefined,
    }};
    window.chrome.loadTimes = window.chrome.loadTimes || (() => ({{
        commitLoadTime: Date.now() / 1000 - Math.random(),
        connectionInfo: 'h2',
        finishDocumentLoadTime: Date.now() / 1000 - Math.random() * 0.5,
        finishLoadTime: Date.now() / 1000 - Math.random() * 0.3,
        firstPaintAfterLoadTime: 0,
        firstPaintTime: Date.now() / 1000 - Math.random(),
        navigationType: 'Other',
        npnNegotiatedProtocol: 'h2',
        requestTime: Date.now() / 1000 - Math.random(),
        startLoadTime: Date.now() / 1000 - Math.random(),
        wasAlternateProtocolAvailable: false,
        wasFetchedViaSpdy: true,
        wasNpnNegotiated: true,
    }}));
    window.chrome.csi = window.chrome.csi || (() => ({{
        onloadT: Date.now(),
        pageT: Date.now() - performance.timing.navigationStart,
        startE: performance.timing.navigationStart,
        tran: 15,
    }}));
    window.chrome.app = window.chrome.app || {{
        isInstalled: false,
        InstallState: {{ DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }},
        RunningState: {{ CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' }},
    }};

    // navigator 基础属性
    patchGetter(navigator, 'platform', CFG.platform);
    patchGetter(navigator, 'vendor', CFG.vendor);
    patchGetter(navigator, 'language', CFG.locale);
    patchGetter(navigator, 'languages', Object.freeze([...CFG.languages]));
    patchGetter(navigator, 'deviceMemory', CFG.deviceMemory);
    patchGetter(navigator, 'hardwareConcurrency', CFG.hardwareConcurrency);
    patchGetter(navigator, 'maxTouchPoints', CFG.maxTouchPoints);
    patchGetter(navigator, 'pdfViewerEnabled', true);

    // plugins / mimeTypes
    const makePlugin = (name, filename, description) => {{
        const plugin = {{ name, filename, description, length: 1, 0: {{ type: 'application/pdf', suffixes: 'pdf', description }} }};
        plugin.item = (i) => plugin[i];
        plugin.namedItem = (n) => (n === name ? plugin : null);
        return plugin;
    }};
    const pdfPlugin = makePlugin(
        'Chrome PDF Plugin',
        'internal-pdf-viewer',
        'Portable Document Format'
    );
    const pdfViewer = makePlugin(
        'Chrome PDF Viewer',
        'mhjfbmdgcfjbbpaeojofohoefgiehjai',
        ''
    );
    const plugins = [pdfPlugin, pdfViewer];
    plugins.item = (i) => plugins[i];
    plugins.namedItem = (n) => plugins.find(p => p.name === n) || null;
    plugins.refresh = () => {{}};
    patchGetter(navigator, 'plugins', plugins);

    const mimeTypes = [{{
        type: 'application/pdf',
        suffixes: 'pdf',
        description: 'Portable Document Format',
        enabledPlugin: pdfPlugin,
    }}];
    mimeTypes.item = (i) => mimeTypes[i];
    mimeTypes.namedItem = (n) => mimeTypes.find(m => m.type === n) || null;
    patchGetter(navigator, 'mimeTypes', mimeTypes);

    // screen
    patchGetter(screen, 'width', CFG.screenWidth);
    patchGetter(screen, 'height', CFG.screenHeight);
    patchGetter(screen, 'availWidth', CFG.screenWidth);
    patchGetter(screen, 'availHeight', CFG.availHeight);
    patchGetter(screen, 'colorDepth', CFG.colorDepth);
    patchGetter(screen, 'pixelDepth', CFG.colorDepth);

    // permissions
    if (navigator.permissions && navigator.permissions.query) {{
        const originalQuery = navigator.permissions.query.bind(navigator.permissions);
        const patchedQuery = (parameters) => {{
            if (parameters && parameters.name === 'notifications') {{
                return Promise.resolve({{ state: Notification.permission, onchange: null }});
            }}
            return originalQuery(parameters);
        }};
        markNative(patchedQuery, 'query');
        navigator.permissions.query = patchedQuery;
    }}

    // 时区
    const originalDateTimeFormat = Intl.DateTimeFormat;
    const patchedDateTimeFormat = function(locales, options) {{
        options = options || {{}};
        if (!options.timeZone) {{
            options.timeZone = CFG.timezone;
        }}
        return new originalDateTimeFormat(locales, options);
    }};
    patchedDateTimeFormat.prototype = originalDateTimeFormat.prototype;
    patchedDateTimeFormat.supportedLocalesOf = originalDateTimeFormat.supportedLocalesOf;
    markNative(patchedDateTimeFormat, 'DateTimeFormat');
    Intl.DateTimeFormat = patchedDateTimeFormat;

    const originalResolvedOptions = originalDateTimeFormat.prototype.resolvedOptions;
    originalDateTimeFormat.prototype.resolvedOptions = function() {{
        const result = originalResolvedOptions.call(this);
        result.timeZone = CFG.timezone;
        return result;
    }};

    // Canvas 噪声（固定 seed，同会话内稳定）
    const seededRandom = (seed) => {{
        let s = seed;
        return () => {{
            s = (s * 9301 + 49297) % 233280;
            return s / 233280;
        }};
    }};
    const canvasRand = seededRandom(CFG.canvasSeed * 100000);

    const patchCanvas = (context) => {{
        const originalGetImageData = context.getImageData.bind(context);
        const patchedGetImageData = function(x, y, w, h) {{
            const imageData = originalGetImageData(x, y, w, h);
            for (let i = 0; i < imageData.data.length; i += 4) {{
                const noise = Math.floor(canvasRand() * 3) - 1;
                imageData.data[i] = Math.min(255, Math.max(0, imageData.data[i] + noise));
            }}
            return imageData;
        }};
        markNative(patchedGetImageData, 'getImageData');
        context.getImageData = patchedGetImageData;
    }};

    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    const patchedGetContext = function(type, attributes) {{
        const context = originalGetContext.call(this, type, attributes);
        if (context && type === '2d') {{
            patchCanvas(context);
        }}
        return context;
    }};
    markNative(patchedGetContext, 'getContext');
    HTMLCanvasElement.prototype.getContext = patchedGetContext;

    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    const patchedToDataURL = function(...args) {{
        const context = originalGetContext.call(this, '2d');
        if (context) {{
            patchCanvas(context);
        }}
        return originalToDataURL.apply(this, args);
    }};
    markNative(patchedToDataURL, 'toDataURL');
    HTMLCanvasElement.prototype.toDataURL = patchedToDataURL;

    // WebGL
    const patchWebGL = (Prototype) => {{
        if (!Prototype || !Prototype.prototype) return;
        const originalGetParameter = Prototype.prototype.getParameter;
        const patchedGetParameter = function(parameter) {{
            if (parameter === UNMASKED_VENDOR_WEBGL) {{
                return CFG.webglVendor;
            }}
            if (parameter === UNMASKED_RENDERER_WEBGL) {{
                return CFG.webglRenderer;
            }}
            return originalGetParameter.call(this, parameter);
        }};
        markNative(patchedGetParameter, 'getParameter');
        Prototype.prototype.getParameter = patchedGetParameter;
    }};
    patchWebGL(window.WebGLRenderingContext);
    patchWebGL(window.WebGL2RenderingContext);

    // AudioContext 指纹
    if (window.OfflineAudioContext || window.AudioContext) {{
        const AudioCtx = window.OfflineAudioContext || window.AudioContext;
        const originalCreateAnalyser = AudioCtx.prototype.createAnalyser;
        if (originalCreateAnalyser) {{
            const patchedCreateAnalyser = function() {{
                const analyser = originalCreateAnalyser.call(this);
                const originalGetFloatFrequencyData = analyser.getFloatFrequencyData.bind(analyser);
                const patchedGetFloatFrequencyData = function(array) {{
                    originalGetFloatFrequencyData(array);
                    for (let i = 0; i < array.length; i++) {{
                        array[i] += CFG.audioSeed * 0.0001;
                    }}
                }};
                markNative(patchedGetFloatFrequencyData, 'getFloatFrequencyData');
                analyser.getFloatFrequencyData = patchedGetFloatFrequencyData;
                return analyser;
            }};
            markNative(patchedCreateAnalyser, 'createAnalyser');
            AudioCtx.prototype.createAnalyser = patchedCreateAnalyser;
        }}
    }}

    // ClientRects 微扰
    const originalGetClientRects = Element.prototype.getClientRects;
    const patchedGetClientRects = function() {{
        const rects = originalGetClientRects.call(this);
        if (!rects || rects.length === 0) {{
            return rects;
        }}
        const noise = CFG.clientRectsNoise;
        const result = [];
        for (let i = 0; i < rects.length; i++) {{
            const rect = rects[i];
            result.push({{
                x: rect.x + noise,
                y: rect.y + noise,
                width: rect.width,
                height: rect.height,
                top: rect.top + noise,
                right: rect.right + noise,
                bottom: rect.bottom + noise,
                left: rect.left + noise,
                toJSON: () => rect.toJSON(),
            }});
        }}
        result.item = (index) => result[index];
        return result;
    }};
    markNative(patchedGetClientRects, 'getClientRects');
    Element.prototype.getClientRects = patchedGetClientRects;

    // iframe 中的 webdriver
    const originalAttachShadow = Element.prototype.attachShadow;
    if (originalAttachShadow) {{
        Element.prototype.attachShadow = function(...args) {{
            return originalAttachShadow.apply(this, args);
        }};
    }}
}})();
"""
