# AstrBot 学术级 PDF 生成插件 (Playwright 强制版)

🚀 **astrbot_plugin_multimodal_pdf_router**

本插件为 AstrBot 提供极致的学术解析与文档交付能力。

> [!IMPORTANT]
> **版本 v1.8.0 变革**：为了确保所有解析内容的学术严谨性与排版美观，本版本已**彻底取消文字闲聊模式**。无论用户输入的是日常问候还是复杂的学术推导，所有回复均会重定向至 PDF 渲染引擎，以精美的 A4 PDF 报告形式进行交付。

## ✨ 核心特性

- 📄 **全员 PDF 交付**：彻底告别碎片化的文字回复，所有交互均通过 Playwright 渲染生成专业 PDF 报告。
- 🖼️ **多模态感知**：支持文字提问、图片提问，以及**引用（Reply）**图片触发解析。
- 🔍 **视觉中转引擎**：内置 OCR 提取链路，能够精准转录图片中的文字与数学公式。
- 📐 **高精度 LaTeX 渲染**：集成 MathJax 3.2，支持行内与块级公式的完美排版。
- ⚙️ **可视化配置**：支持在 AstrBot WebUI 直接填写 API Key、视觉模型及本地存储路径。

## 🛠️ 环境要求

由于本插件使用了浏览器内核进行 PDF 渲染，且运行在 macOS (M4 等) 系统下，请确保满足：

1. **依赖安装**：
   ```bash
   pip install playwright aiohttp
   playwright install chromium
   ```

2. **沙箱权限 (iOS/macOS OneBot 必看)**：
   本插件会自动将 PDF 生成至沙箱可访问的临时目录。请确保在插件配置中正确设定数据存储路径。

## 📦 安装与配置

1. 将本仓库克隆到 AstrBot 的 `plugins` 目录。
2. 重启 AstrBot。
3. 在 WebUI 管理界面找到本插件：
   - 填写 `llm_api_key` 与 `llm_base_url`。
   - 设定您的逻辑大脑模型（如 deepseek-chat）与视觉大脑模型（如 qwen-vl-max）。

## 📝 开发者
本插件由 **Anti-Gravity Agent** 开发。

---
> [!TIP]
> 建议在“学术报告”模式下使用，体验知识被系统化整理的乐趣。
