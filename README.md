# AstrBot 多模态 PDF 路由插件 (Playwright 版)

🚀 **astrbot_plugin_multimodal_pdf_router**

本插件为 AstrBot 提供强大的“双轨意图路由”能力。它能自动识别用户的问题复杂度，并智能选择回复方式：简单问题通过聊天回复，复杂学术问题或推导请求则自动生成高精度的 A4 PDF 报告。

## ✨ 核心特性

- 🤖 **意图自动路由**：内置双轨判定，智能区分“闲聊”与“深度学术解答”。
- 🖼️ **多模态感知**：支持文字提问、图片提问，以及**引用（Reply）**图片触发解析。
- 📄 **高精度 PDF 导出**：使用 Chromium 内核（Playwright）进行 PDF 渲染，支持 LaTeX 数学公式与精美排版。
- ⚡ **仿真交互**：Chat 模式支持分段模拟真人打字时延发送。
- ⚙️ **灵活配置**：支持在 AstrBot 管理界面直接配置后端 API URL 与发送时延。

## 🛠️ 环境要求

由于本插件使用了 Playwright 渲染引擎，且运行在 Mac/Linux 环境下，请确保满足以下条件：

1. **安装核心依赖**：
   在终端运行以下命令：
   ```bash
   pip install playwright aiohttp
   playwright install chromium
   ```

2. **系统权限 (重要)**：
   在 macOS 上，请确保运行 AstrBot 的终端或本程序已加入 **“完全磁盘访问权限”**（系统设置 -> 隐私与安全性 -> Full Disk Access）。

3. **后端 API**：
   本插件需要一个配套的 LLM 路由后端。默认请求地址为 `http://127.0.0.1:8000/v1/bot/route_intent`。

## 📦 安装与配置

1. 在 AstrBot 插件市场搜索并安装，或将本仓库克隆到 `plugins` 目录。
2. 重启 AstrBot。
3. 在 WebUI 管理界面找到本插件，配置您的 `llm_api_url` 即可。

## 📝 贡献与支持

如果您在使用过程中遇到问题，欢迎提交 Issue。
本插件由 Anti-Gravity Agent 开发。

---
> [!TIP]
> 建议关闭 Mac 的硬盘睡眠选项，以保证异步 PDF 服务的长期稳定性。
