# NapCat 与 AstrBot 网络配置指南

## 📡 网络架构说明

本插件在 **8765 端口**启动 HTTP 文件服务器，用于向 QQ 客户端提供 PDF 文件访问。NapCat 作为 QQ 协议适配器，需要能够访问 AstrBot 的文件服务。

## 🔌 OneBot v11 协议配置（必须）

在配置网络之前，需要先建立 AstrBot 与 NapCat 之间的 OneBot v11 连接。

### 1. 配置 AstrBot（反向 WebSocket 服务端）

1. 进入 AstrBot 的 WebUI 管理界面
2. 点击左侧边栏 **机器人**
3. 点击右侧界面的 **+ 创建机器人**
4. 选择 **OneBot v11**
5. 填写配置表单：

| 配置项 | 说明 | 推荐值 |
|--------|------|--------|
| **ID** | 实例标识符，用于区分不同平台 | `napcat_qq` |
| **启用** | 是否启用此机器人实例 | ✅ 勾选 |
| **反向 WebSocket 主机地址** | AstrBot 监听地址 | `0.0.0.0` |
| **反向 WebSocket 端口** | AstrBot 监听端口 | `6199` |
| **反向 WebSocket Token** | 鉴权令牌（可选） | 留空或设置强密码 |

6. 点击 **保存**

### 2. 配置 NapCat（反向 WebSocket 客户端）

编辑 NapCat 配置文件（通常为 `config/onebot11.json`）：

```json
{
  "http": {
    "enable": false,
    "host": "",
    "port": 3000,
    "secret": "",
    "enableHeart": false,
    "enablePost": false,
    "postUrls": []
  },
  "ws": {
    "enable": false,
    "host": "",
    "port": 3001
  },
  "reverseWs": {
    "enable": true,
    "urls": [
      "ws://astrbot:6199/ws"
    ]
  },
  "GroupLocalTime": {
    "Record": false,
    "RecordList": []
  },
  "debug": false,
  "heartInterval": 30000,
  "messagePostFormat": "array",
  "enableLocalFile2Url": true,
  "musicSignUrl": "",
  "reportSelfMessage": false,
  "token": ""
}
```

**关键配置说明**：
- `reverseWs.enable`: 必须设置为 `true`
- `reverseWs.urls`: 填写 AstrBot 的反向 WebSocket 地址
  - **Host 网络模式**：`ws://127.0.0.1:6199/ws`
  - **Bridge 网络模式**：`ws://astrbot:6199/ws`（使用容器名）
- `token`: 如果 AstrBot 配置了 Token，此处需保持一致

### 3. 验证连接

重启 NapCat 和 AstrBot 后，检查连接状态：

#### AstrBot 日志
前往 AstrBot WebUI 控制台，应看到：
```
[INFO] aiocqhttp(OneBot v11) 适配器已连接。
```

如果出现以下日志则表示连接失败：
```
[WARN] aiocqhttp 适配器已被关闭
```

#### NapCat 日志
```bash
# 查看 NapCat 日志
podman logs napcat | grep -i "websocket"

# 成功连接示例
[INFO] WebSocket 连接成功: ws://astrbot:6199/ws
```

#### 常见连接问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `ECONNREFUSED 127.0.0.1:6199` | AstrBot 未启动或端口未监听 | 1. 确认 AstrBot 已启动<br>2. 检查 AstrBot WebUI 中 OneBot v11 配置是否已保存<br>3. 查看 AstrBot 日志确认端口监听状态 |
| 连接超时 | 网络不通或端口错误 | 检查容器网络配置和端口映射 |
| 鉴权失败 | Token 不匹配 | 确保两端 Token 一致或都留空 |
| 地址解析失败 | 容器名无法解析 | 确认容器在同一网络或使用 IP 地址 |

#### 排查 ECONNREFUSED 错误的步骤

如果 NapCat 日志显示 `Error: connect ECONNREFUSED 127.0.0.1:6199`，说明无法连接到 AstrBot 的 6199 端口：

```bash
# 1. 检查 AstrBot 是否正在运行
docker ps | grep astrbot

# 2. 检查 6199 端口是否被监听
netstat -tuln | grep 6199
# 或使用 ss 命令
ss -tuln | grep 6199

# 3. 查看 AstrBot 日志
docker logs astrbot | grep -i "onebot\|6199"
```

**如果端口未监听（netstat 无输出），说明 OneBot v11 配置未生效，请按以下步骤操作：**

#### 步骤 1：访问 AstrBot WebUI
```bash
# AstrBot WebUI 默认端口是 6185
# 在浏览器中访问：http://你的服务器IP:6185
```

#### 步骤 2：创建 OneBot v11 机器人实例
1. 登录 WebUI 后，点击左侧边栏 **"机器人"** 或 **"平台"**
2. 点击右侧的 **"+ 创建机器人"** 或 **"添加平台"**
3. 在弹出的列表中选择 **"OneBot v11"**
4. 填写表单：
   - **ID**：`napcat_qq`（或任意名称）
   - **启用**：✅ **必须勾选**
   - **反向 WebSocket 主机地址**：`0.0.0.0`
   - **反向 WebSocket 端口**：`6199`
   - **反向 WebSocket Token**：留空（或与 NapCat 配置一致）
5. 点击 **"保存"** 按钮

#### 步骤 3：重启 AstrBot
```bash
# 重启容器使配置生效
docker restart astrbot

# 等待 10 秒后检查端口
sleep 10
netstat -tuln | grep 6199

# 应该看到类似输出：
# tcp        0      0 0.0.0.0:6199            0.0.0.0:*               LISTEN
```

#### 步骤 4：查看 AstrBot 日志确认
```bash
docker logs astrbot --tail 50

# 应该看到类似日志：
# [INFO] [Platform] OneBot v11 反向 WebSocket 服务器已启动: 0.0.0.0:6199
# [INFO] [Platform] 等待 OneBot v11 客户端连接...
```

#### 步骤 5：重启 NapCat
```bash
docker restart napcat

# 查看 NapCat 日志
docker logs napcat --tail 20

# 成功连接应该看到：
# [INFO] WebSocket 连接成功: ws://127.0.0.1:6199/ws
```

---

## 🐳 Docker/Podman 部署配置

> **macOS 用户注意**：macOS 不支持 `--network host` 模式，请使用方案二（Bridge 网络）或方案三（Docker Compose）。

### 方案一：Host 网络模式（推荐 - 仅限 Linux）

**适用场景**：NapCat 和 AstrBot 在同一台 Linux 主机上运行

#### NapCat 配置
```bash
# 使用 Docker（推荐）
docker run -d \
  --name napcat \
  --network host \
  -v /path/to/napcat/config:/app/napcat/config \
  mlikiowa/napcat-docker:latest
```

#### AstrBot 配置
```bash
# 使用 Docker
docker run -d \
  --name astrbot \
  --network host \
  -v /path/to/AstrBot/data:/AstrBot/data \
  your-astrbot-image:latest
```

> **注意**：如果你的系统使用 Podman，只需将上述命令中的 `docker` 替换为 `podman` 即可。

**优势**：
- 容器直接使用宿主机网络栈
- NapCat 可通过 `127.0.0.1:8765` 访问 AstrBot 文件服务
- 无需端口映射，配置简单

---

### 方案二：Bridge 网络 + 端口映射

**适用场景**：需要网络隔离或多容器编排

#### 1. 创建自定义网络
```bash
podman network create astrbot-network
```

#### 2. 启动 AstrBot（暴露 8765 端口）
```bash
podman run -d \
  --name astrbot \
  --network astrbot-network \
  -p 8765:8765 \
  -v /path/to/AstrBot/data:/AstrBot/data \
  your-astrbot-image:latest
```

#### 3. 启动 NapCat（加入同一网络）
```bash
podman run -d \
  --name napcat \
  --network astrbot-network \
  -v /path/to/napcat/config:/app/napcat/config \
  mlikiowa/napcat-docker:latest
```

#### 4. 修改插件配置
编辑 `astrbot-plugin-multimodal-pdf-router/main.py`，将 HTTP URL 生成逻辑修改为容器名：

```python
# 第 619 行附近
# 原代码：
http_url = f"http://127.0.0.1:{self.http_port}/pdf/{pdf_filename}"

# 修改为：
http_url = f"http://astrbot:{self.http_port}/pdf/{pdf_filename}"
```

**优势**：
- 网络隔离更安全
- 容器间通过容器名通信
- 适合 Docker Compose 编排

---

### 方案三：Docker Compose 一键部署

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  astrbot:
    image: your-astrbot-image:latest
    container_name: astrbot
    ports:
      - "6199:6199"  # OneBot v11 反向 WebSocket 端口
      - "8765:8765"  # PDF 文件服务端口
    volumes:
      - ./AstrBot/data:/AstrBot/data
    networks:
      - astrbot-net
    restart: unless-stopped

  napcat:
    image: mlikiowa/napcat-docker:latest
    container_name: napcat
    volumes:
      - ./napcat/config:/app/napcat/config
    networks:
      - astrbot-net
    depends_on:
      - astrbot
    restart: unless-stopped

networks:
  astrbot-net:
    driver: bridge
```

启动命令：
```bash
docker-compose up -d
```

**注意事项**：
- 确保 NapCat 配置文件中 `reverseWs.urls` 设置为 `ws://astrbot:6199/ws`
- 如果使用 Host 网络模式，需要修改为 `ws://127.0.0.1:6199/ws`

---

## 🔧 防火墙配置

### Linux (firewalld)
```bash
# 开放 8765 端口
sudo firewall-cmd --permanent --add-port=8765/tcp
sudo firewall-cmd --reload
```

### Linux (iptables)
```bash
sudo iptables -A INPUT -p tcp --dport 8765 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

### macOS
```bash
# macOS 默认不启用防火墙，如已启用：
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /path/to/astrbot
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /path/to/astrbot
```

---

## 🌐 外网访问配置（可选）

如果需要从外网访问 PDF 文件（如服务器部署场景）：

### 1. 配置公网 IP/域名
编辑 `main.py` 第 619 行：
```python
# 使用公网 IP
http_url = f"http://YOUR_PUBLIC_IP:{self.http_port}/pdf/{pdf_filename}"

# 或使用域名
http_url = f"https://your-domain.com/pdf/{pdf_filename}"
```

### 2. Nginx 反向代理（推荐）
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /pdf/ {
        proxy_pass http://127.0.0.1:8765/pdf/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. 配置 HTTPS（可选）
```bash
# 使用 Let's Encrypt
sudo certbot --nginx -d your-domain.com
```

---

## 🔍 故障排查

### 问题 1：NapCat 无法下载 PDF
**症状**：QQ 显示"文件下载失败"

**排查步骤**：
```bash
# 1. 检查 AstrBot 文件服务是否启动
curl http://127.0.0.1:8765/pdf/test.pdf

# 2. 检查容器网络连通性
podman exec napcat ping astrbot

# 3. 查看 AstrBot 日志
podman logs astrbot | grep "PDF服务器"
```

**解决方案**：
- 确认 8765 端口未被占用：`netstat -tuln | grep 8765`
- 检查防火墙规则
- 验证容器网络配置

---

### 问题 2：端口冲突
**症状**：日志显示 `[Errno 98] address already in use`

**解决方案**：
```bash
# 查找占用进程
sudo lsof -i :8765

# 修改插件端口（编辑 main.py 第 31 行）
self.http_port = 8766  # 改为其他端口
```

---

### 问题 3：容器间无法通信
**症状**：Na 无法访问 `http://astrbot:8765`

**排查步骤**：
```bash
# 检查容器是否在同一网络
podman network inspect astrbot-network

# 测试 DNS 解析
podman exec napcat nslookup astrbot

# 测试端口连通性
podman exec napcat telnet astrbot 8765
```

---

## 📊 性能优化建议

### 1. 文件清理策略
插件默认每天凌晨 3:00 清理超过 24 小时的文件，可根据需求调整：

```python
# main.py 第 69 行
one_day_seconds = 24 * 60 * 60  # 改为 12 * 60 * 60 缩短为 12 小时
```

### 2. HTTP 服务器性能
如果并发访问量大，建议使用 Nginx 作为前端代理：
```nginx
upstream astrbot_backend {
    server 127.0.0.1:8765;
    keepalive 32;
}

server {
    location /pdf/ {
        proxy_pass http://astrbot_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

---

## 📝 配置检查清单

部署前请确认：

### OneBot v11 连接
- [ ] AstrBot WebUI 中已创建 OneBot v11 机器人实例
- [ ] 反向 WebSocket 端口设置为 6199
- [ ] NapCat 配置文件中 `reverseWs.enable` 为 `true`
- [ ] NapCat 配置文件中 `reverseWs.urls` 正确指向 AstrBot
- [ ] Token 配置一致（如果使用）
- [ ] AstrBot 日志显示 "aiocqhttp(OneBot v11) 适配器已连接"

### 网络配置
- [ ] 6199 端口（OneBot v11）未被占用
- [ ] 8765 端口（PDF 文件服务）未被占用
- [ ] 防火墙已开放必要端口（如需外网访问）
- [ ] NapCat 与 AstrBot 网络互通
- [ ] 容器使用 host 网络或在同一 bridge 网络

### 插件配置
- [ ] AstrBot 插件已正确安装在 `data/plugins` 目录
- [ ] PDF 存储目录 `/AstrBot/data/pdf_reports` 有写入权限
- [ ] 已安装 Playwright 和 Chromium：`playwright install chromium`
- [ ] 已安装插件依赖：`pip install -r requirements.txt`
- [ ] 已配置 LLM API Key（文本模型和视觉模型）

---

## 🆘 获取帮助

如遇到问题，请提供以下信息：

1. 部署方式（Docker/Podman/裸机）
2. 网络模式（host/bridge）
3. AstrBot 日志：`podman logs astrbot`
4. NapCat 日志：`podman logs napcat`
5. 网络诊断结果：`podman network inspect`\最后更新**：2026-04-26  
**维护者**：Anti-Gravity Agent
