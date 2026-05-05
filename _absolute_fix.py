import os

CONTENT = """
import logging
import asyncio
import aiohttp
import os
import time
import json
import re
from concurrent.futures import ThreadPoolExecutor
from playwright.async_api import async_playwright
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
        
        self.data_dir = "/AstrBot/data/pdf_reports"
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.history_file = os.path.join(self.data_dir, "chat_history.json")
        self.chat_history = {}
        self.max_history_rounds = 5
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.chat_history = json.load(f)
            except Exception as e:
                logger.error(f"Error loading history: {e}")
        
        self.last_hint_time = {}
        self.hint_cooldown = 3600
        self.http_port = 8765
        self.http_server = None
        asyncio.create_task(self._start_http_server())
        asyncio.create_task(self._schedule_cleanup())

    async def _start_http_server(self):
        try:
            app = web.Application()
            app.router.add_get('/pdf/{filename}', self._serve_pdf)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', self.http_port)
            await site.start()
            self.http_server = runner
        except Exception as e:
            logger.error(f"HTTP server error: {e}")

    async def _serve_pdf(self, request):
        filename = request.match_info['filename']
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath): return web.Response(status=404)
        return web.FileResponse(filepath)

    async def _cleanup_old_files(self):
        try:
            current_time = time.time()
            one_day = 86400
            for filename in os.listdir(self.data_dir):
                fp = os.path.join(self.data_dir, filename)
                if os.path.isfile(fp) and (current_time - os.path.getmtime(fp) > one_day):
                    os.remove(fp)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    async def _schedule_cleanup(self):
        while True:
            await self._cleanup_old_files()
            await asyncio.sleep(3600)

    def _save_history(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.chat_history, f, ensure_ascii=False, indent=2)
        except: pass

    async def _clean_format_with_llm(self, raw_response: str) -> dict:
        api_key = self.config.get("format_cleaner_api_key", "")
        api_url = self.config.get("format_cleaner_api_url", "https://api.deepseek.com/v1")
        model = self.config.get("format_cleaner_model", "deepseek-chat")
        if not api_key: return {}
        
        prompt = (
            "你是 HTML 清洗专家。规则：1. 提取 JSON: {\\"mode\\": \\"pdf\\", \\"pdf_content\\": \\"HTML\\"}. "
            "2. 清理标签. 3. 直接返回 JSON.\\n输入内容:\\n" + raw_response[:3000]
        )
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(f"{api_url.rstrip('/')}/chat/completions", json=payload, headers={"Authorization": f"Bearer {api_key}"}) as r:
                    if r.status == 200:
                        data = await r.json()
                        content = data['choices'][0]['message']['content']
                        match = re.search(r'\\{.*\\}', content, re.DOTALL)
                        if match: return json.loads(match.group(), strict=False)
        except: pass
        return {}

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def hint_for_question(self, event: AstrMessageEvent):
        text = getattr(event, "message_str", "").strip()
        if not text or any(c in text for c in ["/ai", "/ask", "/解答", "/解析"]): return
        is_q = text.endswith("？") or text.endswith("?") or any(w in text for w in ["怎么", "如何", "为什么"])
        is_m = any(k in text for k in ["换模型", "改模型", "切换模型"])
        if is_q or is_m:
            sid = f"{getattr(event, 'group_id', 'p')}_{getattr(event.message_obj.sender, 'user_id', 'u')}"
            now = time.time()
            if now - self.last_hint_time.get(sid, 0) > 3600:
                self.last_hint_time[sid] = now
                yield event.plain_result("💡 提示：如需 PDF 请加 /ai ；换模型用 /ai -m 模型名")

    @filter.command("ai", alias={"ask", "解答", "解析"})
    async def handle_multimodal_query(self, event: AstrMessageEvent):
        text_api_key = self.config.get("text_api_key", "")
        ocr_api_key = self.config.get("ocr_api_key", "")
        text_url = self.config.get("text_api_url", "https://api.deepseek.com/v1")
        ocr_url = self.config.get("ocr_api_url", "https://api.deepseek.com/v1")
        if not text_api_key:
            yield event.plain_result("⚠️ 请配置 API Key")
            return

        question = ""
        image_urls = []
        pdf_paths = []
        segments = getattr(event.message_obj, "message", []) or getattr(event.message_obj, "components", [])
        for comp in segments:
            if isinstance(comp, Plain): question += comp.text
            elif isinstance(comp, Image): image_urls.append(comp.url or comp.file)
            elif isinstance(comp, File) and (comp.url or comp.file).lower().endswith(".pdf"): pdf_paths.append(comp.url or comp.file)
        
        question = question.replace("/ai", "").strip()
        target_model = None
        m_match = re.search(r'(-m|--model)\\s+([^\\s]+)', question)
        if m_match:
            target_model = m_match.group(2)
            question = question.replace(m_match.group(0), "").strip()

        if pdf_paths:
            import fitz
            for p in pdf_paths:
                try:
                    doc = fitz.open(p)
                    for idx in range(len(doc)):
                        pix = doc[idx].get_pixmap(matrix=fitz.Matrix(2,2))
                        png = os.path.join(self.data_dir, f"tmp_{int(time.time())}_{idx}.png")
                        pix.save(png)
                        image_urls.append(f"file://{png}")
                except: pass

        ocr_text = ""
        if image_urls and ocr_api_key:
            import base64
            b64_imgs = []
            for u in image_urls:
                try:
                    p = u.replace("file://", "")
                    with open(p, "rb") as f:
                        b64_imgs.append(f"data:image/png;base64,{base64.b64encode(f.read()).decode()}")
                except: pass
            
            payload = {"model": self.config.get("llm_vision_model", "qwen-vl-max"), "messages": [{"role": "user", "content": [{"type": "text", "text": "提取文字和 LaTeX"}, *[{"type": "image_url", "image_url": {"url": b}} for b in b64_imgs]]}]}
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.post(f"{ocr_url.rstrip('/')}/chat/completions", json=payload, headers={"Authorization": f"Bearer {ocr_api_key}"}) as r:
                        if r.status == 200:
                            d = await r.json()
                            ocr_text = d['choices'][0]['message']['content']
            except: pass

        model = target_model or self.config.get("llm_model", "deepseek-chat")
        sys_prompt = ""
        prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f: sys_prompt = f.read()
        
        user_input = f"参考: {ocr_text}\\n指令: {question}"
        messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_input}]
        
        ans_json = {}
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(f"{text_url.rstrip('/')}/chat/completions", json={"model": model, "messages": messages}, headers={"Authorization": f"Bearer {text_api_key}"}) as r:
                    if r.status == 200:
                        d = await r.json()
                        ans_str = d['choices'][0]['message']['content']
                        match = re.search(r'\\{.*\\}', ans_str, re.DOTALL)
                        if match: ans_json = json.loads(match.group(), strict=False)
        except: pass

        pdf_content = ans_json.get("pdf_content", "解析失败")
        yield event.plain_result("🚀 正在生成 PDF...")
        
        mj = "<script>window.MathJax={tex:{inlineMath:[['$','$']]},startup:{pageReady:()=>MathJax.startup.defaultPageReady().then(()=>window.MATH_DONE=true)}};</script><script src='https://npm.elemecdn.com/mathjax@3/es5/tex-mml-chtml.js'></script>"
        style = "body{font-family:serif;padding:40px;line-height:1.6} h1{color:#2980b9} .theorem{background:#fff9db;padding:15px;border-radius:8px;margin:20px 0}"
        html = f"<!DOCTYPE html><html><head><meta charset='UTF-8'>{mj}<style>{style}</style></head><body>{pdf_content}</body></html>"
        
        out = os.path.join(self.data_dir, f"r_{int(time.time())}.pdf")
        try:
            async with async_playwright() as p:
                b = await p.chromium.launch()
                pg = await b.new_page()
                await pg.set_content(html, wait_until="networkidle")
                await pg.wait_for_function("window.MATH_DONE===true")
                await pg.pdf(path=out, format="A4")
                await b.close()
            
            import socket
            host = socket.gethostname()
            url = f"http://{host}:{self.http_port}/pdf/{os.path.basename(out)}"
            yield event.chain_result([File(name=os.path.basename(out), url=url)])
        except Exception as e:
            yield event.plain_result(f"失败: {e}")
"""

# 执行覆写逻辑
with open("main.py", "w", encoding="utf-8") as f:
    f.write(CONTENT.strip())
print("main.py 已被物理覆写！")
