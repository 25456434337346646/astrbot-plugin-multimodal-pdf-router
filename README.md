# AstrBot 多模态 PDF 生成插件

🚀 **astrbot_plugin_multimodal_pdf_router**

基于意图路由与多模态能力的 PDF 生成插件，为 AstrBot 提供强大的图文解析与文档交付能力。

## ✨ 核心特性

- 📄 **智能 PDF 生成**：自动将 LLM 回复渲染为精美的 A4 PDF 报告
- 🖼️ **多模态支持**：支持文字、图片、PDF 文件的智能识别和解析
- 🔍 **OCR 识别**：内置视觉识别引擎，精准提取图片中的文字和数学公式（LaTeX 格式）
- 📐 **LaTeX 渲染**：完美支持数学公式的专业排版
- 🔄 **PDF 引用解析**：支持引用 PDF 文件，自动转换为图片并进行 OCR 识别
- 🧹 **自动清理**：定时清理超过 24 小时的临时文件，节省存储空间
- 📡 **HTTP 文件服务**：内置文件服务器，支持通过 URL 访问生成的 PDF

## 🛠️ 环境要求

### 系统依赖

```bash
# 安装 Poppler (PDF 转图片工具)
# Ubuntu/Debian
apt-get install poppler-utils

# CentOS/RHEL
yum install poppler-utils

# macOS
brew install poppler
```

### Python 依赖

```bash
pip install playwright aiohttp pdf2image Pillow reportlab
playwright install chromium
```

## 📦 安装与配置

### 1. 安装插件

将本仓库克隆到 AstrBot 的 `data/plugins` 目录：

```bash
cd /path/to/AstrBot/data/plugins
git clone https://github.com/25456434337346646/astrbot-plugin-multimodal-pdf-router.git
```

### 2. 安装依赖

```bash
cd astrbot-plugin-multimodal-pdf-router
pip install -r requirements.txt
playwright install chromium
```

### 3. 配置 AstrBot

在 AstrBot WebUI 中配置：
- **LLM 提供商**：设置你的 LLM API（如 OpenAI、DeepSeek 等）
- **视觉模型**（可选）：如果需要 OCR 功能，配置支持视觉的模型（如 qwen-vl-plus）

### 4. 重启 AstrBot

```bash
# 如果使用 Docker/Podman
podman restart astrbot

# 或直接重启 AstrBot 进程
```

## 🎯 使用方法

### 基础使用

直接向机器人发送消息，插件会自动判断是否需要生成 PDF：

```
用户：解释一下量子纠缠
机器人：🚀 发现核心意图，正在为您整理精美 PDF 报告...
机器人：[发送 PDF 文件]
```

### 图片识别

发送图片，插件会自动进行 OCR 识别：

```
用户：[发送数学题图片]
用户：解决这道题
机器人：🔍 正在通过像素级提取细节...
机器人：[发送包含解答的 PDF]
```

### PDF 引用

引用之前的 PDF 文件进行追问：

```
用户：[引用之前的 PDF] 详细解释第二步
机器人：[下载并识别 PDF 内容]
机器人：[发送新的 PDF 解答]
```

### 🧠 多轮对话记忆

插件会自动记忆并隔离不同用户/群组最近的 5 轮上下文。你可以直接追问：

```
用户：解答上面的第一题。
用户：这部分再讲详细点。
```

当话题结束或上下文发生混乱时，你可以随时重置记忆：

```
用户：/ai clear
机器人：🧹 当前会话的记忆已成功清除，我们重新开始吧。
```

## ⚙️ 配置说明

### 插件配置项

在 AstrBot 插件配置页面填写以下参数：

**基础配置**：
- `text_api_url`: 文本模型 API 地址（如 `https://api.deepseek.com/v1`）
- `text_api_key`: 文本模型 API 密钥
- `ocr_api_url`: 视觉模型 API 地址（如 `https://api.deepseek.com/v1`）
- `ocr_api_key`: 视觉模型 API 密钥
- `llm_model`: 文本模型名称（如 `deepseek-chat`）
- `llm_vision_model`: 视觉模型名称（如 `qwen-vl-max`）
- `delay_between_chat`: 消息发送间隔（秒）

**格式清洗层配置**：
- `format_cleaner_enabled`: 是否启用格式清洗层（默认 `true`）
- `format_cleaner_api_key`: 清洗层 API Key（选填，不填则禁用）
- `format_cleaner_api_url`: 清洗层 API 地址（选填，默认 `https://api.deepseek.com/v1`）
- `format_cleaner_model`: 清洗层模型名称（选填，默认 `deepseek-chat`）

> **格式清洗层说明**：使用指定的 LLM 模型自动修复不同模型输出的格式差异，提取和规范化 JSON 结构，清理 HTML 标签。显著提升 PDF 渲染成功率，默认推荐使用 DeepSeek 系列模型。

### HTTP 服务器

插件会在端口 **8765** 启动 HTTP 文件服务器，用于提供 PDF 文件访问。

如果需要外部访问，请确保：
1. 防火墙开放 8765 端口
2. 配置公网 IP 或域名（在代码中修改 `public_host` 参数）

### 文件清理

插件会自动清理旧文件：
- **清理时间**：每天凌晨 3:00
- **清理规则**：删除修改时间超过 24 小时的文件
- **清理范围**：
  - `/AstrBot/data/pdf_reports/` 下的所有 PDF 和 PNG 文件
  - `/tmp/` 下以 `remote_` 开头的临时文件

### 存储路径

默认 PDF 存储路径：`/AstrBot/data/pdf_reports/`

如需修改，请在代码中更改 `self.data_dir` 参数。

## 🔧 故障排查

### 端口冲突

如果 8765 端口被占用：
```
[PDF服务器] 启动失败: [Errno 98] address already in use
```

解决方法：修改 `main.py` 中的 `self.http_port` 参数。

### 字体问题

如果 PDF 中文显示为方块，安装中文字体：

```bash
# Ubuntu/Debian
apt-get install fonts-noto-cjk

# CentOS/RHEL
yum install google-noto-sans-cjk-fonts
```

### OCR 识别失败

检查：
1. 是否配置了支持视觉的 LLM 模型
2. 图片是否成功转换为 base64
3. 查看日志中的 `[视觉中转]` 标签

## 📊 版本历史

查看 [CHANGELOG.md](CHANGELOG.md) 了解详细更新记录。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

> [!TIP]
> 建议在学术讨论、问题解答等场景下使用，体验专业的知识整理与交付。
