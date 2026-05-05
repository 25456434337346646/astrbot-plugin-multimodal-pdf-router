import logging
import asyncio
import aiohttp
import os
import time
import json
import re
import base64
from concurrent.futures import ThreadPoolExecutor
from playwright.async_api import async_playwright
from pdf2image import convert_from_path
import tempfile
from aiohttp import web
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Plain, Image, Reply, File
from astrbot.api import AstrBotConfig

logger = logging.getLogger("astrbot")

@register("astrbot_plugin_multimodal_pdf_router", "Anti-Gravity Agent", "基于'视觉中转'链路的深度解析插件", "2.0.0")
class MultimodalPDFRouterPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        
        # PDF 存储目录
        self.data_dir = "/AstrBot/data/pdf_reports"
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 记忆功能初始化
        self.history_file = os.path.join(self.data_dir, "chat_history.json")
        self.chat_history = {}
        self.max_history_rounds = 5  # 默认保留最近 5 轮对话
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.chat_history = json.load(f)
                logger.info(f"[记忆模块] 已成功加载 {len(self.chat_history)} 个会话的记忆")
            except Exception as e:
                logger.error(f"[记忆模块] 历史记录加载失败: {e}")
        
        # 初始化提示冷却池 (1小时冷却)
        self.last_hint_time = {}
        self.hint_cooldown = 3600
        
        # 启动 HTTP 文件服务器
        self.http_port = 8765
        self.http_server = None
        asyncio.create_task(self._start_http_server())
        
        # 启动定时清理任务
        asyncio.create_task(self._schedule_cleanup())
        
        # 缓存上一轮 HTML 源码
        self.last_html = {}
    
    async def _start_http_server(self):
        """启动轻量级 HTTP 文件服务器"""
        try:
            app = web.Application()
            app.router.add_get('/pdf/{filename}', self._serve_pdf)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', self.http_port)
            await site.start()
            self.http_server = runner
            logger.info(f"[PDF服务器] HTTP 文件服务器已启动: http://0.0.0.0:{self.http_port}")
        except Exception as e:
            if "address already in use" in str(e) or "Errno 98" in str(e):
                logger.info(f"[PDF服务器] 端口 {self.http_port} 已被占用，可能由于热重载，将直接复用现有实例。")
            else:
                logger.error(f"[PDF服务器] 启动失败: {e}")
    
    async def _serve_pdf(self, request):
        """处理 PDF 文件请求"""
        filename = request.match_info['filename']
        filepath = os.path.join(self.data_dir, filename)
        
        if not os.path.exists(filepath):
            return web.Response(status=404, text="File not found")
        
        return web.FileResponse(filepath, headers={
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'inline; filename="{filename}"'
        })
    
    async def _cleanup_old_files(self):
        """清理超过 1 天的旧文件"""
        try:
            current_time = time.time()
            one_day_seconds = 24 * 60 * 60
            cleanup_count = 0
            
            # 清理 PDF 报告目录
            if os.path.exists(self.data_dir):
                for filename in os.listdir(self.data_dir):
                    filepath = os.path.join(self.data_dir, filename)
                    try:
                        if os.path.isfile(filepath):
                            file_age = current_time - os.path.getmtime(filepath)
                            if file_age > one_day_seconds:
                                os.remove(filepath)
                                cleanup_count += 1
                                logger.info(f"[文件清理] 已删除旧文件: {filename} (年龄: {file_age/3600:.1f}小时)")
                    except Exception as e:
                        logger.warning(f"[文件清理] 删除文件失败 {filename}: {e}")
            
            # 清理系统临时目录中的远程下载文件
            temp_dir = tempfile.gettempdir()
            for filename in os.listdir(temp_dir):
                if filename.startswith(("remote_", "remote_img_")):
                    filepath = os.path.join(temp_dir, filename)
                    try:
                        if os.path.isfile(filepath):
                            file_age = current_time - os.path.getmtime(filepath)
                            if file_age > one_day_seconds:
                                os.remove(filepath)
                                cleanup_count += 1
                                logger.info(f"[文件清理] 已删除临时文件: {filename}")
                    except Exception as e:
                        logger.warning(f"[文件清理] 删除临时文件失败 {filename}: {e}")
            
            if cleanup_count > 0:
                logger.info(f"[文件清理] 本次清理完成，共删除 {cleanup_count} 个文件")
            else:
                logger.info(f"[文件清理] 本次清理完成，无需删除文件")
                
        except Exception as e:
            logger.error(f"[文件清理] 清理任务异常: {e}")
    
    async def _schedule_cleanup(self):
        """定时清理任务调度器"""
        try:
            # 启动时立即执行一次清理
            await asyncio.sleep(10)  # 等待插件完全启动
            logger.info("[文件清理] 启动时清理任务开始执行...")
            await self._cleanup_old_files()
            
            # 每天凌晨 3:00 执行清理
            while True:
                now = time.localtime()
                # 计算到下一个凌晨 3:00 的秒数
                target_hour = 3
                seconds_until_3am = ((target_hour - now.tm_hour) % 24) * 3600 - now.tm_min * 60 - now.tm_sec
                if seconds_until_3am <= 0:
                    seconds_until_3am += 24 * 3600
                
                logger.info(f"[文件清理] 下次清理将在 {seconds_until_3am/3600:.1f} 小时后执行")
                await asyncio.sleep(seconds_until_3am)
                
                logger.info("[文件清理] 定时清理任务开始执行...")
                await self._cleanup_old_files()
                
        except Exception as e:
            logger.error(f"[文件清理] 调度器异常: {e}")
            
    def _save_history(self):
        """保存聊天历史到文件"""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.chat_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[记忆模块] 历史记录保存失败: {e}")
    
    def _fix_bare_latex(self, html: str) -> str:
        """
        工业级 LaTeX/HTML 混合解析加固方案：
        采用多级掩码机制，确保：
        1. 已有公式不被二次包裹
        2. HTML 标签不被 LaTeX 识别破坏
        3. LaTeX 内部的 < > 安全转义
        """
        if not html: return html

        # 还原可能存在的转义，统一处理
        html = html.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        
        # 掩码池
        mask_pool = {}
        def get_mask(content, prefix="MASK"):
            m = f"\x00{prefix}_{len(mask_pool)}\x00"
            mask_pool[m] = content
            return m

        # --- 第一步：屏蔽 HTML 标签 ---
        # 保护所有的 <tag ...>，防止后续正则误吞
        html = re.sub(r'<[^>]+>', lambda m: get_mask(m.group(0), "TAG"), html)

        # --- 第二步：屏蔽已有的合规公式环境 ---
        # 匹配优先级：$$ > $ > \[ > \( > \begin
        math_patterns = [
            r'\$\$.*?\$\$',
            r'\$.*?\$',
            r'\\\[.*?\\\]',
            r'\\\(.*?\\\)',
            r'\\begin\{([a-z*]+)\}.*?\\end\{\1\}'
        ]
        for p in math_patterns:
            html = re.sub(p, lambda m: get_mask(m.group(0).replace('<', ' \\lt ').replace('>', ' \\gt '), "MATH"), html, flags=re.DOTALL)

        # --- 第三步：处理残留的裸露 LaTeX 命令 ---
        CMDS = (r'\\(?:mathbb|mathcal|overline|underline|frac|dfrac|sqrt|'
                r'int|iint|oint|sum|prod|lim|limsup|liminf|sup|inf|max|min|'
                r'sin|cos|tan|cot|log|ln|exp|det|dim|gcd|'
                r'to|rightarrow|leftarrow|Rightarrow|Leftarrow|Leftrightarrow|implies|mapsto|'
                r'subset|supset|subseteq|supseteq|cup|cap|setminus|emptyset|'
                r'in|notin|ni|not|mid|nmid|'
                r'le|leq|ge|geq|ne|neq|approx|equiv|sim|cong|ll|gg|prec|succ|'
                r'alpha|beta|gamma|delta|epsilon|varepsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|varphi|chi|psi|omega|'
                r'Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Phi|Psi|Omega|'
                r'infty|partial|nabla|forall|exists|neg|land|lor|'
                r'cdot|cdots|ldots|times|div|pm|mp|circ|'
                r'text|textrm|mathrm|mathbf|operatorname|boldsymbol|'
                r'left|right|big|Big|bigg|Bigg|'
                r'begin|end|cases|quad|qquad|displaystyle)')
        
        MC = r"[a-zA-Z0-9_()\[\]|{}=<>+\-*/^,.:;!']"
        # 识别以反斜杠开头且包含后续 LaTeX 特征的字符序列
        bare_pattern = r'(?:' + CMDS + r')(?:' + MC + r'|' + CMDS + r'|\\\\|\s)*'

        def wrap_bare(m):
            content = m.group(0).strip()
            if not content: return m.group(0)
            # 对裸露公式内部也进行转义
            content = content.replace('<', ' \\lt ').replace('>', ' \\gt ')
            return f'${content}$'

        html = re.sub(bare_pattern, wrap_bare, html)

        # --- 第四步：两级还原 ---
        # 1. 还原公式（保持内部已转义的 \lt \gt）
        # 2. 还原标签（保持原始 HTML 结构）
        # 循环还原直到没有占位符，防止嵌套（虽然本逻辑已规避）
        max_iter = 10
        while "\x00" in html and max_iter > 0:
            for mask, original in mask_pool.items():
                html = html.replace(mask, original)
            max_iter -= 1

        return html

    async def _clean_format_with_llm(self, raw_response: str) -> dict:
        """使用配置的清洗模型对输出格式进行规范化"""
        cleaner_enabled = self.config.get("format_cleaner_enabled", True)
        cleaner_api_key = self.config.get("format_cleaner_api_key", "")
        cleaner_api_url = self.config.get("format_cleaner_api_url", "https://api.deepseek.com/v1")
        cleaner_model = self.config.get("format_cleaner_model", "deepseek-chat")
        
        if not cleaner_enabled:
            logger.info("[格式清洗] 清洗层已禁用，跳过")
            return {}
        
        if not cleaner_api_key:
            logger.info("[格式清洗] 未配置清洗层 API Key，跳过清洗")
            return {}
        
        # 规则：
        # 1. 提取或构造 JSON：{"mode": "pdf", "pdf_content": "HTML内容"}
        # 2. 清理 pdf_content 中的 HTML：
        #    - 移除外层标签：<!DOCTYPE>, <html>, <head>, <body>
        #    - 保留内容标签：<h1>, <h2>, <p>, <div>, <table>, <ul>, <ol>, <li>, <strong>, <em>, <br>
        #    - 补全未闭合标签
        #    - 保留 LaTeX 公式中的 $ 和 \ 符号
        # 3. 如果输入是纯文本，转换为：<div style="white-space: pre-wrap;">{文本}</div>
        # 4. 直接返回纯 JSON 对象，不要任何解释文字

        cleaner_prompt = f"""你是 HTML 格式清洗专家。严格按以下规则处理：

输入：可能包含 JSON 或纯文本的 LLM 输出
输出：标准 JSON 格式（不要 markdown 标记，不要 ```json 包裹）

规则：
1. 提取或构造 JSON：{{"mode": "pdf", "pdf_content": "HTML内容"}}
2. 清理 pdf_content 中的 HTML：
   - 移除外层标签：<!DOCTYPE>, <html>, <head>, <body>
   - 保留内容标签：<h1>, <h2>, <p>, <div>, <table>, <ul>, <ol>, <li>, <strong>, <em>, <br>
   - 补全未闭合标签
   - 保留 LaTeX 公式中的 $ 和 \\ 符号
3. 如果输入是纯文本，转换为：<div style="white-space: pre-wrap;">{{文本}}</div>
4. 直接返回纯 JSON 对象，不要任何解释文字

输入内容：
{raw_response[:15000]}"""  # 扩大输入长度，防止长报告被截断
        
        payload = {
            "model": cleaner_model,
            "messages": [
                {"role": "system", "content": "你是格式清洗专家，只返回纯 JSON，不要任何额外文字。"},
                {"role": "user", "content": cleaner_prompt}
            ],
            "temperature": 0.1,  # 降低随机性
            "max_tokens": 4000
        }
        
        try:
            logger.info(f"[格式清洗] 开始调用清洗模型: {cleaner_model}")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{cleaner_api_url.rstrip('/')}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {cleaner_api_key}", "Content-Type": "application/json"},
                    timeout=30,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        cleaned_str = data['choices'][0]['message']['content'].strip()
                        logger.info(f"[格式清洗] 清洗成功，返回长度: {len(cleaned_str)}")
                        
                        # 提取 JSON（移除可能的 markdown 标记）
                        json_match = re.search(r'\{.*\}', cleaned_str, re.DOTALL)
                        if json_match:
                            try:
                                # 使用 strict=False 允许控制字符
                                cleaned_json = json.loads(json_match.group(), strict=False)
                                logger.info(f"[格式清洗] JSON 解析成功，mode={cleaned_json.get('mode')}")
                                return cleaned_json
                            except json.JSONDecodeError as je:
                                logger.error(f"[格式清洗] JSON 解析失败: {je}")
                                return {}
                        else:
                            logger.warning("[格式清洗] 未找到 JSON 格式")
                            return {}
                    else:
                        err_text = await resp.text()
                        logger.error(f"[格式清洗] API 返回错误 {resp.status}: {err_text[:200]}")
                        return {}
        except asyncio.TimeoutError:
            logger.error("[格式清洗] 请求超时")
            return {}
        except Exception as e:
            logger.error(f"[格式清洗] 异常: {e}")
            return {}

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def hint_for_question(self, event: AstrMessageEvent):
        """当检测到用户在问问题或想要切换模型但没有带命令时，给出提示"""
        text = getattr(event, "message_str", "").strip()
        if not text:
            return
            
        # 如果带有触发指令，则跳过
        if any(cmd in text for cmd in ["/ai", "/ask", "/解答", "/解析"]):
            return
            
        # 1. 意图识别：是否在问问题
        is_question = False
        if text.endswith("？") or text.endswith("?"):
            is_question = True
        else:
            q_words = ["怎么", "如何", "为什么", "是什么", "帮我", "请问", "详细解释", "翻译一下", "算一下"]
            if any(w in text for w in q_words) and len(text) > 4:
                is_question = True
                
        # 2. 意图识别：是否想切换模型
        is_model_intent = False
        model_keywords = ["换模型", "改模型", "切换模型", "用什么模型", "模型名", "有哪些模型"]
        common_models = ["gpt-4", "gpt-4o", "claude", "deepseek", "qwen", "gemini", "llama", "mistral", "o1-"]
        if any(k in text for k in model_keywords):
            is_model_intent = True
        elif any(m in text.lower() for m in common_models) and ("模型" in text or "用" in text or "换" in text):
            is_model_intent = True

        if is_question or is_model_intent:
            # 提取 session_id 用于隔离冷却时间
            session_id = getattr(event, "session_id", None)
            if not session_id:
                msg_obj = getattr(event, "message_obj", None)
                sender_id = getattr(getattr(msg_obj, "sender", object()), "user_id", "unknown_user")
                group_id = getattr(msg_obj, "group_id", getattr(event, "group_id", "private"))
                session_id = f"{group_id}_{sender_id}"
                
            now = time.time()
            last_time = self.last_hint_time.get(session_id, 0)
            if now - last_time > self.hint_cooldown:
                self.last_hint_time[session_id] = now
                if is_model_intent:
                    yield event.plain_result("💡 发现您想切换模型？\n如需本轮指定模型，请使用标准格式：\n/ai -m 模型名 您的提问\n(仅对当次对话生效，不影响他人及默认配置)")
                else:
                    yield event.plain_result("💡 提示：如需将该问题的解答整理为精美的 PDF 报告，请在消息前加上 /ai 哦~")

    @filter.command("ai", alias={"ask", "解答", "解析"})
    async def handle_multimodal_query(self, event: AstrMessageEvent):
        """内置大脑的交互逻辑：直接调用 LLM 并根据意图路由"""
        
        # 0. 获取配置
        text_api_key = self.config.get("text_api_key", "")
        ocr_api_key = self.config.get("ocr_api_key", "")
        text_base_url = self.config.get("text_api_url", "https://api.deepseek.com/v1")
        ocr_base_url = self.config.get("ocr_api_url", "https://api.deepseek.com/v1")
        
        if not text_api_key or not ocr_api_key:
            yield event.plain_result("⚠️ 请先在插件配置页面填写 文本 和 OCR 的 API Key！")
            return

        # 1. 提取消息内容
        question_texts = []
        image_urls = []
        pdf_texts = []  # 收集 PDF 文本内容（直接提取）
        pdf_urls = []   # 当 PDF 无可提取文本时，用于 OCR 处理的 PDF 文件路径
        segments = getattr(event.message_obj, "message", []) or getattr(event.message_obj, "components", [])
            
        quoted_texts = []
        # 输出组件数量，简化调试信息，避免在 f-string 中使用复杂的列表推导导致语法错误
        logger.info(f"[诊断_段落解析] 发现 {len(segments)} 个组件。")
        for comp in segments:
            if isinstance(comp, Plain):
                question_texts.append(comp.text)
            elif isinstance(comp, Image):
                img_url = comp.url or comp.file
                if img_url:
                    if os.path.isabs(img_url) and not img_url.startswith("file://"):
                        img_url = f"file://{img_url}"
                    image_urls.append(img_url)
            # 处理文件组件，尤其是 PDF
            elif isinstance(comp, File):
                file_url = comp.url or comp.file
                f_name = getattr(comp, 'name', '') or str(file_url)
                if file_url and f_name.lower().endswith('.pdf'):
                    file_path = ""
                    # 判别是否为网络 HTTP 下载链接
                    if file_url.startswith("http://") or file_url.startswith("https://"):
                        logger.info(f"[PDF处理] 发现远程 PDF 链接，正在下载: {file_url[:80]}...")
                        try:
                            import urllib.request
                            tmp_path = os.path.join(tempfile.gettempdir(), f"remote_{int(time.time())}.pdf")
                            urllib.request.urlretrieve(file_url, tmp_path)
                            file_path = tmp_path
                            logger.info("[PDF处理] 远程 PDF 下载成功。")
                        except Exception as e:
                            logger.warning(f"[PDF处理] 远程 PDF 下载失败: {e}")
                            continue
                    else:
                        if os.path.isabs(file_url) and not file_url.startswith("file://"):
                            file_path = file_url
                        else:
                            file_path = file_url.replace('file://', '')
                            
                    try:
                        # 放弃 PyPDF2 纯文本抽取（因其无法读取 MathJax 及复杂中文排版），强制进入视觉 OCR 队列
                        pdf_urls.append(file_path)
                        logger.info(f"[PDF处理] 已将 PDF 文件排入视觉 OCR 渲染队列，准备转换为高精度图像: {file_path}")
                    except Exception as e:
                        logger.warning(f"[PDF处理] 解析 PDF 失败: {e}")
            elif isinstance(comp, Reply):
                try:
                    logger.info(f"[Reply调试] 拦截到内置引用链: {getattr(comp, 'chain', 'None')}")
                    
                    # 1. 如果 AstrBot 原生解析了被引用消息的所有组件，则直接闪电提取
                    if hasattr(comp, "chain") and comp.chain:
                        for nested in comp.chain:
                            if isinstance(nested, Plain):
                                quoted_texts.append(nested.text)
                            elif isinstance(nested, Image):
                                image_urls.append(nested.url or nested.file)
                            elif isinstance(nested, File):
                                f_url = nested.url or nested.file
                                f_name = getattr(nested, 'name', '') or str(f_url)
                                if f_url and f_name.lower().endswith('.pdf'):
                                    # 将其推入外层重新走一次文件处理逻辑，以便触发 HTTP 下载！
                                    segments.append(nested)
                        logger.info("[Reply] 成功从原生 chain 中解析上下文组件，完美避开 API!")
                        continue
                        
                    # 2. 如果只有 id 没有 chain，则执行原先的容错 fallback
                    target_msg_id = None
                    possible_id_attrs = ['start_id', 'id', 'message_id', 'msg_id', 'reply_id', 'target_id']
                    
                    for attr in possible_id_attrs:
                        if hasattr(comp, attr):
                            attr_value = getattr(comp, attr)
                            if attr_value:
                                target_msg_id = attr_value
                                break
                    
                    if not target_msg_id:
                        continue
                        
                    # 使用异步超时机制获取平台适配器，防止阻塞
                    platform_name = event.get_platform_name()
                    if not platform_name:
                        logger.warning(f"[Reply调试] 无法获取平台名称，跳过适配器获取")
                        continue
                    try:
                        # 在可能阻塞的同步调用上使用线程池执行，并设置超时
                        loop = asyncio.get_event_loop()
                        with ThreadPoolExecutor() as executor:
                            adapter = await asyncio.wait_for(
                                loop.run_in_executor(executor, self.context.get_platform_inst, platform_name),
                                timeout=5.0
                            )
                        # 若直接使用平台名称未能获取到适配器，尝试常见别名作为备选
                        if not adapter:
                            fallback_names = ["default", "qq", "qq_official", "aiocqhttp", "OneBot"]
                            for fn in fallback_names:
                                if fn == platform_name:
                                    continue
                                try:
                                    adapter = await asyncio.wait_for(
                                        loop.run_in_executor(executor, self.context.get_platform_inst, fn),
                                        timeout=2.0
                                    )
                                    if adapter:
                                        logger.info(f"[Reply调试] 使用平台别名 '{fn}' 成功获取适配器")
                                        break
                                except Exception:
                                    # 忽略单个别名的异常，继续尝试其他别名
                                    continue
                    except asyncio.TimeoutError:
                        logger.warning(f"[Reply调试] 获取平台适配器超时 (platform={platform_name})")
                        continue
                    except Exception as e:
                        logger.error(f"[Reply调试] 获取平台适配器异常: {e}")
                        continue
                    if not adapter:
                        logger.warning(f"[Reply调试] 获取平台适配器返回 None (platform={platform_name})")
                        continue
                    
                    # 尝试多种API方法获取消息
                    msg_data = None
                    api_methods = [
                        ("get_msg", {"message_id": target_msg_id}),
                        ("get_group_msg_history", {"group_id": getattr(event, "group_id", None), "message_seq": target_msg_id}),
                        ("get_forward_msg", {"id": target_msg_id})
                    ]
                    
                    for api_name, params in api_methods:
                        try:
                            if api_name == "get_group_msg_history" and not params.get("group_id"):
                                continue
                            logger.info(f"[Reply调试] 尝试API: {api_name}, 参数: {params}")
                            msg_data = await adapter.call_api(api_name, **params)
                            if msg_data:
                                logger.info(f"[Reply调试] {api_name} 成功返回数据")
                                break
                        except Exception as api_e:
                            logger.warning(f"[Reply调试] {api_name} 调用失败: {api_e}")
                            continue
                    
                    if not msg_data:
                        logger.warning(f"[Reply调试] 所有API方法都失败，无法获取引用消息")
                        continue
                        
                    logger.info(f"[Reply调试] 最终获取的消息数据: {json.dumps(msg_data, ensure_ascii=False, default=str)[:800]}")
                    
                    # 解析消息内容 - 支持多种数据结构
                    actual_msg = None
                    if isinstance(msg_data, dict):
                        # 尝试多种可能的消息字段路径
                        msg_paths = [
                            ["message"],
                            ["data", "message"], 
                            ["data", "messages"],
                            ["messages"],
                            ["content"]
                        ]
                        
                        for path in msg_paths:
                            temp_data = msg_data
                            try:
                                for key in path:
                                    temp_data = temp_data.get(key)
                                    if temp_data is None:
                                        break
                                if temp_data is not None:
                                    actual_msg = temp_data
                                    logger.info(f"[Reply调试] 在路径 {' -> '.join(path)} 找到消息内容")
                                    break
                            except (AttributeError, TypeError):
                                continue
                    
                    if actual_msg is None:
                        logger.warning(f"[Reply调试] 无法从返回数据中提取消息内容")
                        continue
                    
                    # 处理结构化消息格式
                    if isinstance(actual_msg, list):
                        logger.info(f"[Reply调试] 处理结构化消息，共 {len(actual_msg)} 个段落")
                        for i, segment in enumerate(actual_msg):
                            if not isinstance(segment, dict): 
                                logger.warning(f"[Reply调试] 段落 {i} 不是字典格式: {type(segment)}")
                                continue
                            seg_type = segment.get("type")
                            seg_data = segment.get("data", {})
                            logger.info(f"[Reply调试] 段落 {i}: type={seg_type}, data={seg_data}")
                            
                            if seg_type == "text":
                                txt = seg_data.get("text", "")
                                if txt: 
                                    quoted_texts.append(txt)
                                    logger.info(f"[Reply调试] 提取文本: {txt[:100]}...")
                            elif seg_type == "image":
                                img_url = seg_data.get("url") or seg_data.get("file") or seg_data.get("path")
                                if img_url: 
                                    if os.path.isabs(img_url) and not img_url.startswith("file://"):
                                        img_url = f"file://{img_url}"
                                    image_urls.append(img_url)
                                    logger.info(f"[Reply调试] 提取图片: {img_url}")
                    
                    # 处理CQ码字符串格式
                    elif isinstance(actual_msg, str):
                        logger.info(f"[Reply调试] 处理CQ码字符串: {actual_msg[:200]}...")
                        
                        # 提取图片
                        cq_images = re.findall(r'\[CQ:image,([^\]]+)\]', actual_msg)
                        for params_str in cq_images:
                            try:
                                params = dict(p.split('=', 1) for p in params_str.split(',') if '=' in p)
                                img_url = params.get("url") or params.get("file") or params.get("path")
                                if img_url:
                                    if os.path.isabs(img_url) and not img_url.startswith("file://"):
                                        img_url = f"file://{img_url}"
                                    image_urls.append(img_url)
                                    logger.info(f"[Reply调试] 从CQ码提取图片: {img_url}")
                            except Exception as cq_e:
                                logger.warning(f"[Reply调试] CQ码解析失败: {cq_e}")
                        
                        # 提取纯文本
                        pure_text = re.sub(r'\[CQ:[^\]]+\]', '', actual_msg).strip()
                        if pure_text:
                            quoted_texts.append(pure_text)
                            logger.info(f"[Reply调试] 提取纯文本: {pure_text[:100]}...")
                    
                    else:
                        logger.warning(f"[Reply调试] 未知的消息格式: {type(actual_msg)}")
                        
                except Exception as e:
                    logger.error(f"[Reply调试] 提取 Reply 内容报错: {e}", exc_info=True)

        question = " ".join(question_texts).replace("/ai", "").replace("/ask", "").replace("/解答", "").replace("/解析", "").strip()
        
        # 提取并临时切换模型 (格式: /ai -m gpt-4o 帮我分析...)
        target_model = None
        model_match = re.search(r'(-m|--model)\s+([^\s]+)', question)
        if model_match:
            target_model = model_match.group(2)
            question = question.replace(model_match.group(0), "").strip()
            logger.info(f"[模型路由] 用户请求临时切换模型至: {target_model}")
        
        if not question and not image_urls or question.lower() in ["help", "帮助", "功能"]:
            help_text = "可用指令: /ai, /ask, /解析, /解答\n附加指令:\n/ai clear (清除当前会话记忆)\n\n用法示例:\n1. /ai 问答内容\n2. /ai [图片]\n3. [回复图片] + /ai"
            yield event.plain_result(help_text)
            return

        # 提取 session_id 用于隔离记忆
        session_id = getattr(event, "session_id", None)
        if not session_id:
            msg_obj = getattr(event, "message_obj", None)
            sender_id = getattr(getattr(msg_obj, "sender", object()), "user_id", "unknown_user")
            group_id = getattr(msg_obj, "group_id", getattr(event, "group_id", "private"))
            session_id = f"{group_id}_{sender_id}"
            
        # 拦截清除记忆指令
        if question.lower() in ["clear", "清除", "清理", "清除记忆", "清空记忆"]:
            if session_id in self.chat_history:
                del self.chat_history[session_id]
                self._save_history()
            yield event.plain_result("🧹 当前会话的记忆已成功清除，我们重新开始吧。")
            return

        max_retries = 2
        # --- 处理 PDF OCR（将扫描 PDF 转为图片并加入 OCR 队列） ---
        if pdf_urls:
            for pdf_path in pdf_urls:
                try:
                    # 优先尝试使用免系统依赖且更高效的 PyMuPDF (fitz)
                    try:
                        import fitz  # PyMuPDF
                        doc = fitz.open(pdf_path)
                        for idx in range(len(doc)):
                            page = doc[idx]
                            # 放大 2 倍渲染以保证 OCR 提取精度
                            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                            tmp_png_path = os.path.join(self.data_dir, f"pdf_{os.path.basename(pdf_path)}_page{idx}.png")
                            pix.save(tmp_png_path)
                            image_urls.append(f"file://{tmp_png_path}")
                            logger.info(f"[PDF OCR] (fitz) 已生成页面图片并加入 OCR 队列: {tmp_png_path}")
                    except ImportError:
                        # 降级到 pdf2image (需要系统安装 poppler-utils)
                        logger.warning("[PDF OCR] 未安装 PyMuPDF(fitz)，将降级使用 pdf2image (需要系统支持 poppler)。建议执行 pip install PyMuPDF。")
                        from pdf2image import convert_from_path
                        pages = convert_from_path(pdf_path, fmt='png')
                        for idx, page_img in enumerate(pages):
                            tmp_png_path = os.path.join(self.data_dir, f"pdf_{os.path.basename(pdf_path)}_page{idx}.png")
                            page_img.save(tmp_png_path, format='PNG')
                            image_urls.append(f"file://{tmp_png_path}")
                            logger.info(f"[PDF OCR] (pdf2image) 已生成页面图片并加入 OCR 队列: {tmp_png_path}")
                except Exception as e:
                    logger.warning(f"[PDF OCR] 将 PDF 转图片失败 ({pdf_path}): {e}")

        # --- 视觉提取逻辑（带备用模型与重试） ---
        image_description = ""
        if image_urls:
            primary_vision_model = self.config.get("llm_vision_model", "qwen-vl-max")
            fallback_vision_str = self.config.get("fallback_vision_models", "")
            
            # 构建视觉模型队列
            vision_fallbacks = [m.strip() for m in fallback_vision_str.split(",") if m.strip()]
            vision_model_queue = [primary_vision_model]
            for m in vision_fallbacks:
                if m not in vision_model_queue:
                    vision_model_queue.append(m)
            
            vision_prompt = "请精准提取图片中的所有文本内容。若包含数学公式，请务必使用清晰且符合规范的 LaTeX 语法输出。不遗漏任何细节。"
            
            import base64
            api_image_urls = []
            for img_url in image_urls:
                logger.info(f"[视觉中转] 处理图片URL: {img_url[:100]}")
                local_path = None
                if img_url.startswith("file://"):
                    local_path = img_url.replace("file://", "")
                elif img_url.startswith("http://") or img_url.startswith("https://"):
                    try:
                        import urllib.request
                        tmp_img_path = os.path.join(tempfile.gettempdir(), f"remote_img_{int(time.time())}.jpg")
                        urllib.request.urlretrieve(img_url, tmp_img_path)
                        local_path = tmp_img_path
                        logger.info(f"[视觉中转] 远程图片下载成功: {tmp_img_path}")
                    except Exception as e:
                        logger.error(f"[视觉中转] 下载远程图片失败: {e}")
                        continue
                elif os.path.isabs(img_url):
                    local_path = img_url
                
                if local_path:
                    try:
                        with open(local_path, "rb") as f:
                            b64_str = base64.b64encode(f.read()).decode("utf-8")
                            ext = local_path.split('.')[-1].lower()
                            mime_type = f"image/{ext}" if ext in ["png", "jpg", "jpeg", "webp"] else "image/png"
                            api_image_urls.append(f"data:{mime_type};base64,{b64_str}")
                            logger.info(f"[视觉中转] 图片已转换为base64，长度: {len(b64_str)}")
                    except Exception as e:
                        logger.error(f"[视觉中转] 无法读取本地图片进行编码: {e}")
                else:
                    logger.warning(f"[视觉中转] 无法识别的图片URL格式: {img_url}")

            # 遍历视觉模型队列
            for v_idx, target_vision_model in enumerate(vision_model_queue):
                success = False
                logger.info(f"[视觉中转] 正在尝试视觉模型 ({v_idx+1}/{len(vision_model_queue)}): {target_vision_model}")
                
                vision_payload = {
                    "model": target_vision_model,
                    "messages": [{"role": "user", "content": [{"type": "text", "text": vision_prompt}, *[{"type": "image_url", "image_url": {"url": url}} for url in api_image_urls]]}]
                }

                # 视觉 OCR 调用带重试
                for attempt in range(max_retries + 1):
                    try:
                        if attempt == 0 and v_idx == 0:
                            yield event.plain_result(f"🔍 正在通过 {target_vision_model} 像素级提取细节...")
                        
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                f"{ocr_base_url.rstrip('/')}/chat/completions",
                                json=vision_payload,
                                headers={"Authorization": f"Bearer {ocr_api_key}", "Content-Type": "application/json"},
                                timeout=90,
                            ) as resp:
                                if resp.status == 200:
                                    v_data = await resp.json()
                                    if not isinstance(v_data, dict) or 'choices' not in v_data or not v_data['choices']:
                                        raise ValueError(f"OCR API 数据异常: {v_data}")
                                    choice = v_data['choices'][0]
                                    message = choice.get('message', {})
                                    image_description = message.get('content') or ""
                                    logger.info(f"[视觉中转] {target_vision_model} 识别成功，字数: {len(image_description)}")
                                    success = True
                                    break
                                elif resp.status == 429:
                                    logger.warning(f"[视觉中转] {target_vision_model} 触发频控 (429)，等待重试...")
                                    await asyncio.sleep(3)
                                else:
                                    err_body = await resp.text()
                                    logger.error(f"[视觉中转] {target_vision_model} 返回异常 HTTP {resp.status}: {err_body}")
                                    raise ValueError(f"HTTP {resp.status}")
                    except Exception as e:
                        logger.error(f"[视觉中转] {target_vision_model} 尝试过程中出现异常: {e}")
                        if attempt < max_retries:
                            await asyncio.sleep(2)
                        else:
                            logger.error(f"[视觉中转] {target_vision_model} 已达最大重试次数。")
                
                if success:
                    break
                else:
                    if v_idx < len(vision_model_queue) - 1:
                        logger.warning(f"[视觉中转] 模型 {target_vision_model} 失败，准备切换至下一个备用模型...")
                        yield event.plain_result(f"⚠️ 视觉模型 {target_vision_model} 异常，正在尝试备用模型 {vision_model_queue[v_idx+1]}...")
                    else:
                        yield event.plain_result(f"❌ 所有视觉模型均提取失败，将尝试纯文字模式进行后续处理。")


        # --- 逻辑大脑逻辑（带重试与正则解析） ---
        text_model = target_model if target_model else self.config.get("llm_model", "deepseek-chat")
        
        # 强制读取 system_prompt.txt 以确保“取消闲聊”指令生效
        prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                final_system_prompt = f.read()
        else:
            final_system_prompt = "你是一个学术助教。严格输出 JSON：{\"mode\": \"pdf\", \"pdf_content\": \"HTML内容\"}"
        
        # --- 新增：知识库检索增强逻辑 ---
        kb_context = ""
        try:
            if question:
                logger.info(f"[知识库增强] 正在检索关键词: {question[:50]}")
                import inspect
                sig = inspect.signature(self.context.kb_manager.retrieve)
                if 'kb_names' in sig.parameters:
                    retrieved_results = await self.context.kb_manager.retrieve(query=question, kb_names=None)
                elif 'kb_ids' in sig.parameters:
                    retrieved_results = await self.context.kb_manager.retrieve(query=question, kb_ids=None)
                else:
                    retrieved_results = await self.context.kb_manager.retrieve(query=question)
                if retrieved_results:
                    kb_context = self.context.kb_manager._format_context(retrieved_results)
                    logger.info(f"[知识库增强] 检索成功，获取到背景内容。")
        except Exception as kb_e:
            logger.warning(f"[知识库增强] 流程异常 (可能未配置知识库): {kb_e}")

        combined_user_input = ""
        if kb_context:
            combined_user_input += f"【内部知识库参考资料】:\n{kb_context}\n\n"
        if quoted_texts:
            quoted_text_str = " ".join(quoted_texts).strip()
            if quoted_text_str:
                combined_user_input += f"【被引用的历史上下文】:\n{quoted_text_str}\n\n"
        # 若有 PDF 文本（OCR/提取），加入上下文
        if pdf_texts:
            pdf_combined = "\n".join(pdf_texts).strip()
            if pdf_combined:
                combined_user_input += f"【引用的 PDF 内容】:\n{pdf_combined}\n\n"
        
        # 添加图片 OCR 识别内容
        if image_description:
            combined_user_input += f"【图片像素级识别记录】:\n{image_description}\n\n"
        
        combined_user_input += f"【用户的当前指令】: {question}"
        
        # 获取当前会话的历史记录
        history_messages = self.chat_history.get(session_id, [])
        
        # 构建完整消息流: System + 历史上下文 + 当前输入
        messages = [{"role": "system", "content": final_system_prompt}]
        messages.extend(history_messages)
        messages.append({"role": "user", "content": combined_user_input})
        
        logger.info(f"[LLM请求] 组合输入长度={len(combined_user_input)}, 包含历史轮数={len(history_messages)//2}, 包含OCR={bool(image_description)}")
        logger.info(f"[LLM请求] 完整输入内容:\n{combined_user_input}")
        text_payload = {"model": text_model, "messages": messages}
        
        # 准备模型降级序列: [当前指定模型] + [配置的备用模型] + [配置的默认模型]
        fallbacks = self.config.get("fallback_models", "").split(",")
        fallbacks = [m.strip() for m in fallbacks if m.strip()]
        default_model = self.config.get("llm_model", "deepseek-chat")
        
        model_queue = [text_model]
        for m in fallbacks:
            if m not in model_queue: model_queue.append(m)
        if default_model not in model_queue: model_queue.append(default_model)
        
        ans_json = {}
        raw_llm_response = ""
        current_used_model = text_model

        for m_idx, target_model in enumerate(model_queue):
            text_payload["model"] = target_model
            current_used_model = target_model
            logger.info(f"[LLM请求] 正在尝试模型 ({m_idx+1}/{len(model_queue)}): {target_model}")
            
            success = False
            for attempt in range(max_retries + 1):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"{text_base_url.rstrip('/')}/chat/completions",
                            json=text_payload,
                            headers={"Authorization": f"Bearer {text_api_key}", "Content-Type": "application/json"},
                            timeout=120,
                        ) as resp:
                            if resp.status == 200:
                                res_data = await resp.json()
                                if not isinstance(res_data, dict) or 'choices' not in res_data or not res_data['choices']:
                                    raise ValueError(f"返回数据异常")
                                
                                choice = res_data['choices'][0]
                                message = choice.get('message')
                                ans_str = message.get('content') or ""
                                raw_llm_response = ans_str
                                
                                json_match = re.search(r'\{.*\}', ans_str, re.DOTALL)
                                if json_match:
                                    try:
                                        ans_json = json.loads(json_match.group(), strict=False)
                                        success = True
                                        break
                                    except:
                                        cleaned_json = await self._clean_format_with_llm(ans_str)
                                        if cleaned_json:
                                            ans_json = cleaned_json
                                            success = True
                                            break
                                else:
                                    cleaned_json = await self._clean_format_with_llm(ans_str)
                                    if cleaned_json:
                                        ans_json = cleaned_json
                                        success = True
                                        break
                                break
                            elif resp.status == 429:
                                logger.warning(f"[LLM请求] {target_model} 触发频控 (429)，等待重试...")
                                await asyncio.sleep(3)
                            else:
                                if attempt == max_retries: raise Exception(f"HTTP {resp.status}")
                except Exception as e:
                    if attempt < max_retries:
                        logger.warning(f"[LLM请求] {target_model} 失败: {e}，准备重试 ({attempt+1}/{max_retries})...")
                        await asyncio.sleep(2)
                        continue
                    else:
                        logger.error(f"[LLM请求] {target_model} 已达最大重试次数: {e}")
            
            if success:
                break
            else:
                if m_idx < len(model_queue) - 1:
                    next_model = model_queue[m_idx+1]
                    logger.warning(f"[LLM请求] 模型 {target_model} 失败，准备切换至下一个备用模型: {next_model}")
                    yield event.plain_result(f"⚠️ 逻辑模型 {target_model} 响应异常，正在尝试备用模型 {next_model}...")
                else:
                    logger.error(f"[LLM请求] 所有文本模型均已尝试且失败。")
        
        if not ans_json:
            yield event.plain_result(f"❌ 逻辑分析全线不可用 (已尝试 {len(model_queue)} 个模型)")
            return
        # 如果 LLM 调用成功，保存到历史记录中
        if raw_llm_response:
            self.chat_history.setdefault(session_id, [])
            self.chat_history[session_id].append({"role": "user", "content": combined_user_input})
            self.chat_history[session_id].append({"role": "assistant", "content": raw_llm_response})
            # 滑动窗口截断（保留最近 max_history_rounds 轮）
            max_msgs = self.max_history_rounds * 2
            if len(self.chat_history[session_id]) > max_msgs:
                self.chat_history[session_id] = self.chat_history[session_id][-max_msgs:]
            self._save_history()

        # 4. 执行路由分发 (主人：已取消闲聊模式，强制 PDF 化)
        mode = ans_json.get("mode", "pdf")
        pdf_content = ans_json.get("pdf_content", "")
        
        # 如果 JSON 解析失败或内容为空，使用原始 LLM 响应
        if not pdf_content and raw_llm_response:
            response_len = len(raw_llm_response)
            logger.info(f"[PDF生成] JSON内容为空，使用原始LLM响应（长度={response_len}）")
            # 将原始文本转换为 HTML，保留换行
            html_text = raw_llm_response.replace('\n', '<br>')
            pdf_content = f"<div style='white-space: pre-wrap; font-family: serif;'>{html_text}</div>"
        
        # 逻辑合并：即便模型返回了 chat 模式，也将其内容包装进 PDF 报告中
        if mode == "chat" or not pdf_content:
            msgs = ans_json.get("chat_messages", ["暂无详细分析内容。"])
            if not isinstance(msgs, list): msgs = [str(msgs)]
            chat_to_html = "".join([f"<p>{m}</p>" for m in msgs])
            pdf_content = f"<h2>内容交互简报</h2><div style='background:#f9f9f9;padding:15px;border-radius:8px;'>{chat_to_html}</div>"
        
        # 进入 PDF 渲染流程
        yield event.plain_result("🚀 发现核心意图，正在为您整理精美 PDF 报告...")
        text_model = current_used_model # 使用最终成功的模型名
        raw_pdf_content = self._fix_bare_latex(pdf_content)
        logger.info(f"[LaTeX修复] 裸露公式自动包裹完成")
        
        # 缓存 HTML 源码供调试
        self.last_html[session_id] = raw_pdf_content
        # 1. 将内容转换为 Base64，防止特殊字符（如引号、< >）破坏 HTML 结构
        b64_content = base64.b64encode(raw_pdf_content.encode('utf-8')).decode('utf-8')

        # 2. 构建增强型 HTML 模板
        html_content = f"""<!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <script>
        window.MathJax = {{
        tex: {{
        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
        processEnvironments: true,
        processRefs: true,
        tags: 'ams'
        }},
        options: {{
        skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
        ignoreHtmlClass: 'tex2jax_ignore',
        processHtmlClass: 'tex2jax_process'
        }},
        startup: {{
        pageReady: () => {{
          return MathJax.startup.defaultPageReady().then(() => {{
            window.MATHJAX_DONE = true;
          }});
        }}
        }}
        }};
        </script>
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&family=JetBrains+Mono&display=swap');

        :root {{
            --primary-color: #2980b9;
            --secondary-color: #34495e;
            --success-color: #27ae60;
            --note-color: #3498db;
            --bg-color: #ffffff;
            --text-color: #2c3e50;
            --border-color: #ecf0f1;
        }}

        body {{ 
            font-family: 'Noto Serif SC', serif; 
            padding: 40px 60px; 
            line-height: 1.8; 
            color: var(--text-color); 
            background: var(--bg-color);
            max-width: 900px;
            margin: 0 auto;
        }}

        .header {{ 
            text-align: center; 
            border-bottom: 2px solid var(--secondary-color); 
            margin-bottom: 40px; 
            padding-bottom: 20px; 
        }}
        .header h1 {{ margin: 0; font-size: 32px; color: var(--secondary-color); font-weight: 700; }}
        .header .meta {{ margin-top: 10px; color: #7f8c8d; font-size: 14px; }}

        .content {{ font-size: 16px; text-align: justify; }}

        h1 {{ color: var(--primary-color); margin-top: 1.8em; border-left: 6px solid var(--primary-color); padding-left: 15px; font-size: 24px; }}
        h2 {{ color: var(--secondary-color); border-bottom: 1px solid var(--border-color); padding-bottom: 8px; margin-top: 1.5em; font-size: 20px; }}
        h3 {{ color: var(--secondary-color); margin-top: 1.2em; font-size: 18px; }}

        p {{ margin: 1.2em 0; }}

        table {{ width: 100%; border-collapse: collapse; margin: 25px 0; font-size: 15px; table-layout: auto; }}
        th, td {{ padding: 12px 15px; border: 1px solid var(--border-color); }}
        th {{ background-color: #f8f9fa; font-weight: bold; text-align: center; }}
        tr:nth-child(even) {{ background-color: #fcfcfc; }}

        blockquote {{ 
            border-left: 5px solid #bdc3c7; 
            background: #fdfdfd; 
            padding: 15px 25px; 
            margin: 25px 0; 
            font-style: italic;
            color: #555;
        }}

        .theorem {{ 
            background: #f9fbf9; 
            border-left: 5px solid var(--success-color); 
            padding: 20px; 
            border-radius: 0 8px 8px 0; 
            margin: 25px 0; 
            position: relative;
        }}
        .theorem::before {{ content: '定理/结论'; font-weight: bold; color: var(--success-color); display: block; margin-bottom: 10px; font-size: 14px; text-transform: uppercase; }}

        .note {{ 
            background: #f4f9ff; 
            border-left: 5px solid var(--note-color); 
            padding: 20px; 
            border-radius: 0 8px 8px 0; 
            margin: 25px 0; 
        }}
        .note::before {{ content: '笔记/提示'; font-weight: bold; color: var(--note-color); display: block; margin-bottom: 10px; font-size: 14px; }}

        .proof {{ 
            font-style: normal; 
            border-top: 1px dashed #ddd; 
            margin-top: 15px; 
            padding-top: 15px; 
            color: #5f6368; 
            font-size: 15px;
        }}
        .proof::before {{ content: '证明:'; font-weight: bold; margin-right: 8px; }}

        .boxed {{ border: 2px solid #e74c3c; padding: 4px 12px; display: inline-block; font-weight: bold; color: #e74c3c; border-radius: 4px; }}

        pre, code {{ font-family: 'JetBrains Mono', monospace; background: #f8f8f8; border-radius: 4px; }}
        pre {{ padding: 15px; overflow-x: auto; border: 1px solid var(--border-color); margin: 20px 0; }}
        code {{ padding: 2px 5px; color: #e83e8c; font-size: 0.9em; }}
        pre code {{ padding: 0; color: inherit; font-size: 14px; background: transparent; }}

        img {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin: 25px auto; display: block; }}

        ul, ol {{ padding-left: 25px; }}
        li {{ margin-bottom: 8px; }}

        .footer {{ text-align: center; font-size: 12px; color: #bdc3c7; margin-top: 60px; border-top: 1px solid var(--border-color); padding-top: 20px; }}
        </style>
        </head>
        <body class="tex2jax_process">
        <div class='header'>
        <h1>学术解析报告</h1>
        <div class="meta">
            <span>执行模型: {text_model}</span> | 
            <span>生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}</span>
        </div>
        </div>
        <div class='content' id='content'>
        <div style="text-align: center; padding: 50px;">
            <p>正在深度渲染学术内容，请稍候...</p>
        </div>
        </div>
        <div class='footer'>基于 AstrBot Multimodal PDF Router (V2.0) 专业排版引擎</div>

        <script>
        (function() {{
            try {{
                const b64 = "{b64_content}";
                // 使用更健壮的 base64 解码方式处理 UTF-8
                const bin = window.atob(b64);
                const bytes = new Uint8Array(bin.length);
                for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
                const raw = new TextDecoder().decode(bytes);

                const contentEl = document.getElementById('content');

                // 配置 marked 选项
                marked.setOptions({{
                    gfm: true,
                    breaks: true,
                    headerIds: false,
                    mangle: false
                }});

                // 渲染 Markdown/HTML
                contentEl.innerHTML = marked.parse(raw);

                // 触发 MathJax 渲染
                if (window.MathJax && window.MathJax.typeset) {{
                    window.MathJax.typeset();
                }}
            }} catch (e) {{
                console.error("Render error:", e);
                document.getElementById('content').innerHTML = "<p style='color:red'>内容渲染失败，请联系管理员检查源码格式。</p>";
            }}

            // 保险机制：如果 MathJax 没在 15s 内完成，强制设置完成位
            setTimeout(() => {{ window.MATHJAX_DONE = true; }}, 15000);
        }})();
        </script>
        </body>
        </html>"""
        
        tmp_pdf_path = os.path.join(self.data_dir, f"report_{int(time.time())}.pdf")
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                # 使用 domcontentloaded 替代 networkidle，减少对不稳网络资源的强依赖
                await page.set_content(html_content, wait_until="domcontentloaded", timeout=60000)
                
                # 精准等待渲染完成信号，增加 try-except 容错
                try:
                    await page.wait_for_function("window.MATHJAX_DONE === true", timeout=20000)
                    await asyncio.sleep(0.5) # 额外缓冲确保重绘完成
                except Exception as we:
                    logger.warning(f"[PDF生成] MathJax 渲染等待超时，将尝试强制导出: {we}")
                
                await page.pdf(path=tmp_pdf_path, format="A4")
                await browser.close()
            # 使用 HTTP URL 发送 PDF
            # Docker bridge 网络模式下，NapCat 需要通过容器名访问 AstrBot
            pdf_filename = os.path.basename(tmp_pdf_path)
            # 获取容器主机名（在 Docker 中是容器名）
            import socket
            hostname = socket.gethostname()
            # 如果是 Docker 环境，使用容器名；否则使用 127.0.0.1
            if hostname and not hostname.startswith('localhost'):
                http_url = f"http://{hostname}:{self.http_port}/pdf/{pdf_filename}"
            else:
                http_url = f"http://127.0.0.1:{self.http_port}/pdf/{pdf_filename}"
            logger.info(f"[PDF发送] 生成 HTTP URL: {http_url} (hostname: {hostname})")
            yield event.chain_result([
                File(name=pdf_filename, url=http_url)
            ])
        except Exception as pe:
            yield event.plain_result(f"PDF 渲染失败: {pe}")

    @filter.command("ai_source")
    async def get_ai_source(self, event: AstrMessageEvent):
        """获取上一轮生成的 HTML 源码（调试用）"""
        # 提取 session_id
        session_id = getattr(event, "session_id", None)
        if not session_id:
            msg_obj = getattr(event, "message_obj", None)
            sender_id = getattr(getattr(msg_obj, "sender", object()), "user_id", "unknown_user")
            group_id = getattr(msg_obj, "group_id", getattr(event, "group_id", "private"))
            session_id = f"{group_id}_{sender_id}"
            
        source = self.last_html.get(session_id)
        if not source:
            yield event.plain_result("🔍 您本轮尚未生成过 PDF 报告，没有缓存的源码。")
            return
            
        # 以文件形式发送，防止文本太长被截断
        source_filename = f"source_{session_id}_{int(time.time())}.html"
        source_path = os.path.join(self.data_dir, source_filename)
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(source)
            
        # 构造 URL
        import socket
        hostname = socket.gethostname()
        if hostname and not hostname.startswith('localhost'):
            http_url = f"http://{hostname}:{self.http_port}/pdf/{source_filename}"
        else:
            http_url = f"http://127.0.0.1:{self.http_port}/pdf/{source_filename}"
            
        yield event.chain_result([
            Plain("📄 这是上一轮生成的 HTML 源码（包含 LaTeX 自动修复后的内容）：\n"),
            File(name=source_filename, url=http_url)
        ])
