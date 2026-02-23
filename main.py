import websocket
import json
import threading
import time
import re
import logging
import requests
import traceback
import random
from datetime import datetime

# ================= 配置区域 =================

# NapCat WebSocket 地址
WS_URL = "ws://YourIP:Port"
WS_TOKEN = "Your Token"

# 机器人与主人信息
BOT_QQ = 12345678
OWNER_QQ = 12345678
TARGET_111_QQ = 12345678

# DeepSeek API 配置
DEEPSEEK_API_KEY = "sk-xxxxx"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# 阿里云配置
DASHSCOPE_API_KEY = "sk-xxxxx"
# 文生图 (同步接口)
DASHSCOPE_T2I_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
# 图生图/图片编辑 (异步接口)
DASHSCOPE_I2I_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/image2image/image-synthesis"
# 异步任务查询接口
DASHSCOPE_TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/"
# 识图 (Qwen-VL)
DASHSCOPE_CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

# 绘图限制
DRAW_DAILY_LIMIT = 5

# 启用的群组 (私聊不受此限制)
ENABLED_GROUPS = [123456789] 

# 违禁词库
BAN_WORDS = {
    # 1级：禁言10分钟
    "level_1": [r"一级违禁词1", r"一级违禁词2"],  
    # 2级：禁言1小时
    "level_2": [r"二级违禁词1", r"二级违禁词2"],  
    # 3级：踢出
    "level_3": [r"三级违禁词1", r"三级违禁词2"] 
}

# 刷屏检测阈值
SPAM_MAX_LEN = 1000
SPAM_MAX_LINES = 15   

# ================= 日志配置 =================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ================= 逻辑代码 =================

class QQBot:
    def __init__(self, ws_url, token):
        self.ws_url = ws_url
        self.token = token
        self.ws = None
        self.draw_usage = {"date": "", "counts": {}}

    def start(self):
        websocket.enableTrace(False)
        headers = {"Authorization": f"Bearer {self.token}"}
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            header=headers,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.run_forever(ping_interval=30, ping_timeout=10)

    def on_open(self, ws):
        logger.info(f"WebSocket 连接成功")

    def on_close(self, ws, close_status_code, close_msg):
        logger.warning(f"WebSocket 连接关闭: {close_msg}")

    def on_error(self, ws, error):
        logger.error(f"WebSocket 错误: {error}")

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if "echo" in data: return
            
            post_type = data.get('post_type')

            # 处理群消息
            if post_type == 'message' and data.get('message_type') == 'group':
                self.handle_group_message(data)
            
            # [新增] 处理私聊消息
            elif post_type == 'message' and data.get('message_type') == 'private':
                self.handle_private_message(data)

            # 处理通知 (戳一戳等)
            elif post_type == 'notice':
                self.handle_notice(data)
            
            # [新增] 处理请求 (加好友)
            elif post_type == 'request':
                self.handle_request(data)

        except Exception as e:
            logger.error(f"处理消息异常: {e}")
            logger.error(traceback.format_exc())

    # ---------------- API 封装 ----------------

    def send_ws(self, action, params):
        payload = {"action": action, "params": params, "echo": str(int(time.time()))}
        try:
            self.ws.send(json.dumps(payload))
        except Exception as e:
            logger.error(f"发送 WebSocket 数据失败: {e}")

    def send_group_msg(self, group_id, message):
        self.send_ws("send_group_msg", {"group_id": group_id, "message": message})
    
    # [新增] 发送私聊消息
    def send_private_msg(self, user_id, message):
        self.send_ws("send_private_msg", {"user_id": user_id, "message": message})

    def set_group_ban(self, group_id, user_id, duration):
        self.send_ws("set_group_ban", {"group_id": group_id, "user_id": user_id, "duration": duration})

    def set_group_kick(self, group_id, user_id, reject_add_request=False):
        self.send_ws("set_group_kick", {"group_id": group_id, "user_id": user_id, "reject_add_request": reject_add_request})

    def send_like(self, user_id, times=10):
        self.send_ws("send_like", {"user_id": user_id, "times": times})
    
    def recall_msg(self, message_id):
        if message_id:
            self.send_ws("delete_msg", {"message_id": message_id})

    # ---------------- 事件处理 (通知/请求) ----------------

    # [新增] 处理好友请求
    def handle_request(self, data):
        if data.get('request_type') == 'friend':
            user_id = data.get('user_id')
            comment = data.get('comment', '')
            flag = data.get('flag')
            logger.info(f"收到好友请求 - 用户:{user_id} 备注:{comment}")
            
            # 自动同意
            self.send_ws("set_friend_add_request", {"flag": flag, "approve": True})
            
            # 延迟发送欢迎语 (防止好友未建立成功发不出去)
            time.sleep(2)
            self.send_private_msg(user_id, "你好喵！我是瞌睡猫，已经自动通过你的好友请求啦 ( >ω<)ﾉ\n试试对我说“/绘画”或者直接聊天吧！")

    def handle_notice(self, data):
        notice_type = data.get('notice_type')
        sub_type = data.get('sub_type')
        group_id = data.get('group_id')
        user_id = data.get('user_id')

        if group_id and group_id not in ENABLED_GROUPS: return

        if notice_type == 'notify' and sub_type == 'poke':
            target_id = data.get('target_id')
            if target_id == BOT_QQ:
                logger.info(f"被戳了 - 群:{group_id} 用户:{user_id}")
                replies = [
                    f"[CQ:at,qq={user_id}] 呜哇... 谁在戳我呀？( >﹏< )",
                    f"[CQ:at,qq={user_id}] 哼，不理你 (扭头)",
                    f"[CQ:at,qq={user_id}] 别戳啦，毛都要被你戳掉啦！qwq",
                    f"[CQ:at,qq={user_id}] ( >ω<)ﾉ"
                ]
                self.send_group_msg(group_id, random.choice(replies))

        elif notice_type == 'group_increase':
            logger.info(f"新人进群 - 群:{group_id} 用户:{user_id}")
            welcome_msg = f"欢迎新人 [CQ:at,qq={user_id}] 加入本群喵！ ( >ω<)ﾉ"
            self.send_group_msg(group_id, welcome_msg)

    # ---------------- AI 绘图 / 识图 功能 ----------------

    def check_draw_limit(self, user_id, role='member'):
        if role in ['admin', 'owner'] or user_id == OWNER_QQ:
            return True, 999
        today = datetime.now().strftime("%Y-%m-%d")
        if self.draw_usage["date"] != today:
            self.draw_usage = {"date": today, "counts": {}}
        current_count = self.draw_usage["counts"].get(user_id, 0)
        if current_count >= DRAW_DAILY_LIMIT:
            return False, 0
        return True, DRAW_DAILY_LIMIT - current_count

    def add_draw_count(self, user_id):
        today = datetime.now().strftime("%Y-%m-%d")
        if self.draw_usage["date"] == today:
            self.draw_usage["counts"][user_id] = self.draw_usage["counts"].get(user_id, 0) + 1

    # [修改] 文生图 (兼容群/私聊)
    def generate_image_t2i(self, target_id, user_id, prompt, is_group=True):
        send_func = self.send_group_msg if is_group else self.send_private_msg
        prefix = f"[CQ:at,qq={user_id}] " if is_group else ""
        
        logger.info(f"文生图请求 - ID:{target_id} 用户:{user_id} 提示词:{prompt}")
        send_func(target_id, f"{prefix}正在努力画画喵 (文生图)，稍等一下哦 ( >ω<) ...")

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DASHSCOPE_API_KEY}"}
        payload = {
            "model": "qwen-image",
            "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
            "parameters": {
                "negative_prompt": "低分辨率，低画质，肢体畸形，手指畸形，画面过饱和，蜡像感，人脸无细节，过度光滑，画面具有AI感。构图混乱。文字模糊，扭曲，过于写实。",
                "size": "1280*720"
            }
        }
        try:
            response = requests.post(DASHSCOPE_T2I_URL, headers=headers, json=payload, timeout=90)
            if response.status_code == 200:
                res_json = response.json()
                try:
                    image_url = res_json['output']['choices'][0]['message']['content'][0]['image']
                    send_func(target_id, f"{prefix}\n画好啦！(≧∀≦)ゞ \n[CQ:image,file={image_url}]")
                    self.add_draw_count(user_id)
                except:
                    send_func(target_id, f"{prefix}呜呜... 画笔断掉了 (解析失败) qwq")
            else:
                send_func(target_id, f"{prefix}连接绘画服务器失败惹")
        except Exception as e:
            logger.error(f"文生图异常: {e}")
            send_func(target_id, f"{prefix}绘画发生内部错误...")

    # [新增] 图生图/图片编辑 (异步轮询)
    def generate_image_i2i(self, target_id, user_id, prompt, image_urls, is_group=True):
        send_func = self.send_group_msg if is_group else self.send_private_msg
        prefix = f"[CQ:at,qq={user_id}] " if is_group else ""

        # 限制最多3张图
        input_images = image_urls[:3]
        
        logger.info(f"图生图请求 - ID:{target_id} 用户:{user_id} 图片数:{len(input_images)} 提示词:{prompt}")
        send_func(target_id, f"{prefix}收到图片啦，正在施展魔法 (图生图/编辑)，这可能需要一点时间喵... (¦3[▓▓]")

        headers = {
            "X-DashScope-Async": "enable", # 开启异步
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "wan2.5-i2i-preview",
            "input": {
                "prompt": prompt,
                "images": input_images
            },
            "parameters": {
                "prompt_extend": True,
                "n": 1
            }
        }

        try:
            # 1. 提交任务
            response = requests.post(DASHSCOPE_I2I_URL, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                logger.error(f"图生图提交失败: {response.text}")
                send_func(target_id, f"{prefix}任务提交失败惹 (Status: {response.status_code})")
                return

            task_id = response.json()['output']['task_id']
            logger.info(f"图生图任务已提交 TaskID: {task_id}")

            # 2. 轮询结果 (最多等待 3 分钟)
            start_time = time.time()
            while True:
                if time.time() - start_time > 180:
                    send_func(target_id, f"{prefix}处理超时啦，下次再试试吧 qwq")
                    return

                time.sleep(4) # 每4秒查一次
                
                check_res = requests.get(DASHSCOPE_TASK_URL + task_id, headers={"Authorization": f"Bearer {DASHSCOPE_API_KEY}"}, timeout=20)
                if check_res.status_code == 200:
                    task_data = check_res.json()
                    status = task_data['output']['task_status']
                    
                    if status == 'SUCCEEDED':
                        result_url = task_data['output']['results'][0]['url']
                        send_func(target_id, f"{prefix}\n魔法完成啦！✨ \n[CQ:image,file={result_url}]")
                        self.add_draw_count(user_id)
                        return
                    elif status == 'FAILED':
                        code = task_data['output'].get('code', 'Unknown')
                        msg = task_data['output'].get('message', 'Error')
                        logger.error(f"图生图任务失败: {code} - {msg}")
                        send_func(target_id, f"{prefix}生成失败惹... (Error: {code})")
                        return
                    # PENDING 或 RUNNING 继续循环
                else:
                    logger.warning(f"查询任务状态失败: {check_res.status_code}")

        except Exception as e:
            logger.error(f"图生图处理异常: {e}")
            send_func(target_id, f"{prefix}图片魔法发生内部错误...")

    # 图片解析功能
    def analyze_image_content(self, image_url):
        logger.info(f"正在解析图片: {image_url}")
        headers = {
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "qwen3-vl-plus",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": "用简短的语言描述此图。"}
                    ]
                }
            ]
        }
        try:
            response = requests.post(DASHSCOPE_CHAT_URL, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                logger.info(f"图片解析结果: {content}")
                return content
            else:
                return "（图片解析失败，可能链接已过期或服务器繁忙）"
        except Exception as e:
            logger.error(f"图片解析异常: {e}")
            return "（图片解析发生错误）"

    # ---------------- AI 聊天功能 ----------------

    # [修改] 聊天函数，增加 context_type 参数来区分私聊/群聊
    def chat_with_deepseek(self, target_id, user_id, content, image_url=None, context_type="group"):
        logger.info(f"AI聊天请求 ({context_type}) - ID:{target_id} 用户:{user_id} 图片:{'有' if image_url else '无'}")
        
        send_func = self.send_group_msg if context_type == "group" else self.send_private_msg
        prefix = f"[CQ:at,qq={user_id}] " if context_type == "group" else ""

        # 1. 如果有图片，先解析图片内容
        image_description = ""
        if image_url:
            send_func(target_id, f"{prefix}看到图片啦，稍微看一眼... (OvO)")
            image_description = self.analyze_image_content(image_url)
            user_input_with_context = f"【QQ用户:{user_id}】发送了一张图片，图片内容描述为：【{image_description}】。同时他说：{content}"
        else:
            user_input_with_context = f"【QQ用户:{user_id}】说：{content}"

        # 动态提示词
        context_desc = f"你现在正处于一个QQ群中聊天（群号：{target_id}）。" if context_type == "group" else "你现在正在和用户进行一对一私聊。"

        system_prompt = (
            f"你现在的设定如下：\n"
            f"1. 你的名字叫瞌睡猫，是一只可爱的猫娘，说话要带颜文字 ( >ω<), awa, qwq等。\n"
            f"2. {context_desc}\n"
            f"3. 我会以“【QQ用户:xxxx】说：内容”的格式把消息发给你。\n"
            f"   - 你的主人QQ号是 {OWNER_QQ}，辨别清楚消息发送者QQ号。\n"
            f"   - 你的QQ号是 {BOT_QQ}。\n"
            f"4. 回复要简短（50字以内）。\n"
            f"5. 你的功能包括：聊天、群管理、以及【AI绘图】。\n"
            f"   - 如果用户想看图或者让你画画，请告诉他发送命令：/绘画 提示词（如果附带图片就是改图）。\n"
            f"6. 如果用户发送了图片，我会把图片描述转述给你，请根据描述和用户互动。"
        )
        
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input_with_context}],
            "stream": False
        }

        try:
            response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=20)
            if response.status_code == 200:
                reply = response.json()['choices'][0]['message']['content'].replace("瞌睡猫：", "").strip()
                send_func(target_id, f"{prefix}{reply}")
            else:
                send_func(target_id, f"{prefix}喵... 脑子短路了 (API Error)")
        except Exception as e:
            logger.error(f"DeepSeek 请求异常: {e}")

    # ---------------- 辅助函数 ----------------

    # [新增] 提取消息中的图片URL
    def extract_images(self, message):
        """提取消息中的所有图片URL"""
        # 正则匹配 [CQ:image...url=http...]
        urls = re.findall(r'\[CQ:image.*?url=(http[^,\]]+)', message)
        # 处理转义字符 &amp; -> &
        return [url.replace("&amp;", "&") for url in urls]

    def check_violation(self, raw_message, message_id, group_id, user_id, role):
        if role in ['admin', 'owner']: return False
        pure_text = re.sub(r'\[CQ:.*?\]', '', raw_message)
        
        if len(pure_text) > SPAM_MAX_LEN:
            self.recall_msg(message_id) 
            self.set_group_ban(group_id, user_id, 3600)
            self.send_group_msg(group_id, f"[CQ:at,qq={user_id}] 呜哇，字太多啦！( >﹏< )")
            return True
        
        if pure_text.count('\n') > SPAM_MAX_LINES:
            self.recall_msg(message_id) 
            self.set_group_ban(group_id, user_id, 3600)
            self.send_group_msg(group_id, f"[CQ:at,qq={user_id}] 不要竖着发天书啦！(｀Д´)")
            return True

        for level, words in BAN_WORDS.items():
            for word in words:
                if re.search(word, raw_message):
                    self.recall_msg(message_id)
                    if level == "level_3":
                        self.set_group_kick(group_id, user_id)
                        self.send_group_msg(group_id, f"[CQ:at,qq={user_id}] 既然是大坏蛋，那就请你出去吧！(・ω・)")
                    elif level == "level_2":
                        self.set_group_ban(group_id, user_id, 3600)
                        self.send_group_msg(group_id, f"[CQ:at,qq={user_id}] 说了不好的东西哦，去小黑屋反省一下！(T_T)")
                    elif level == "level_1":
                        self.set_group_ban(group_id, user_id, 600)
                        self.send_group_msg(group_id, f"[CQ:at,qq={user_id}] 不许说脏话喵！嘴巴要放干净点！(｀Д´)")
                    return True
        return False

    def parse_time(self, time_str):
        unit = time_str[-1]
        try: val = int(time_str[:-1])
        except: return 0
        if unit == 's': return val
        if unit == 'm': return val * 60
        if unit == 'h': return val * 3600
        if unit == 'd': return val * 86400
        return 0

    # ---------------- 消息处理逻辑入口 ----------------

    # [新增] 通用指令处理 (整合群聊和私聊的公共逻辑)
    def handle_common_commands(self, raw_message, user_id, target_id, is_group, role='member'):
        """处理私聊和群聊通用的命令 (/绘画, 聊天等)"""
        
        # 1. 绘画 / 改图 命令
        if raw_message.startswith("/绘画") or raw_message.startswith("/draw"):
            # 去除命令头，提取纯文本prompt
            clean_cmd = raw_message.split('\n')[0].replace("/绘画", "").replace("/draw", "").strip()
            # 提取所有图片URL
            img_urls = self.extract_images(raw_message)
            
            # 清理 prompt 中的 CQ 码，只保留纯文本
            prompt = re.sub(r'\[CQ:.*?\]', '', clean_cmd).strip()

            if not prompt:
                # 如果是图生图但没写词，默认保持原样
                prompt = "保持原样" if img_urls else "" 
            
            if not prompt and not img_urls:
                 msg = "想画什么呢？(例如 /绘画 可爱的猫娘)\n如果要改图，请发送 /绘画 + 图片 + 修改描述"
                 if is_group: self.send_group_msg(target_id, msg)
                 else: self.send_private_msg(target_id, msg)
                 return True

            # 检查次数限制
            allowed, remaining = self.check_draw_limit(user_id, role)
            if not allowed:
                msg = f"[CQ:at,qq={user_id}] 画笔没墨水了 (每日限{DRAW_DAILY_LIMIT}次) (qwq)" if is_group else "画笔没墨水了 (每日限额已用完) (qwq)"
                if is_group: self.send_group_msg(target_id, msg)
                else: self.send_private_msg(target_id, msg)
                return True

            if img_urls:
                # 图生图 / 图片编辑
                threading.Thread(target=self.generate_image_i2i, args=(target_id, user_id, prompt, img_urls, is_group)).start()
            else:
                # 文生图
                threading.Thread(target=self.generate_image_t2i, args=(target_id, user_id, prompt, is_group)).start()
            return True # 已处理

        # 2. 聊天逻辑
        should_chat = False
        clean_text = raw_message
        image_url = None
        
        # 群聊需要 @机器人，私聊直接对话
        if is_group:
            if f"[CQ:at,qq={BOT_QQ}]" in raw_message:
                should_chat = True
                clean_text = raw_message.replace(f"[CQ:at,qq={BOT_QQ}]", "")
        else:
            should_chat = True # 私聊所有消息都回

        if should_chat:
            # 提取第一张图片用于识图
            imgs = self.extract_images(raw_message)
            if imgs:
                image_url = imgs[0]
            
            # 清理文本中的图片CQ码
            clean_text = re.sub(r'\[CQ:image,.*?\]', '', clean_text).strip()
            if not clean_text and not image_url:
                clean_text = "（戳了戳你）" # 只有@没有内容的兜底

            threading.Thread(target=self.chat_with_deepseek, 
                             args=(target_id, user_id, clean_text, image_url, "group" if is_group else "private")).start()
            return True

        return False

    def handle_group_message(self, data):
        group_id = data.get('group_id')
        user_id = data.get('user_id')
        message_id = data.get('message_id')
        raw_message = data.get('raw_message', "")
        role = data.get('sender', {}).get('role', 'member')

        if ENABLED_GROUPS and group_id not in ENABLED_GROUPS: return

        if self.check_violation(raw_message, message_id, group_id, user_id, role): return

        # 优先处理通用功能 (绘图/聊天)
        if self.handle_common_commands(raw_message, user_id, group_id, True, role):
            return

        # --- 群组专属指令 ---

        # 111睡觉模式
        if raw_message == "111睡觉模式":
            if role in ['admin', 'owner'] or user_id == OWNER_QQ:
                self.set_group_ban(group_id, TARGET_111_QQ, 8 * 3600)
                self.send_group_msg(group_id, f"收到！这就让TA强制睡觉觉！(¦3[▓▓]")
            else:
                self.send_group_msg(group_id, "你不是我主人，才不听你的呢 (哼)")
            return

        # 点赞
        if raw_message == "赞我":
            self.send_like(user_id, times=10)
            self.send_group_msg(group_id, f"[CQ:at,qq={user_id}] 给你点赞啦！要开心哦 ( >ω<)")
            return

        # 管理员指令
        if raw_message.startswith("/mute") or raw_message.startswith("/unmute"):
            if role not in ['admin', 'owner'] and user_id != OWNER_QQ: return
            try:
                parts = raw_message.split()
                target_qq = int(parts[1])
                if raw_message.startswith("/mute") and len(parts) == 3:
                    self.set_group_ban(group_id, target_qq, self.parse_time(parts[2]))
                    self.send_group_msg(group_id, f"已把 {target_qq} 关进小黑屋！")
                elif raw_message.startswith("/unmute"):
                    self.set_group_ban(group_id, target_qq, 0)
                    self.send_group_msg(group_id, f"已把 {target_qq} 放出来啦！")
            except: pass
            return

    # [新增] 处理私聊消息
    def handle_private_message(self, data):
        user_id = data.get('user_id')
        raw_message = data.get('raw_message', "")
        
        # 私聊通常不进行违规词检测，也无需 recall
        # target_id 在私聊中就是 user_id
        role = 'owner' if user_id == OWNER_QQ else 'member'
        
        self.handle_common_commands(raw_message, user_id, user_id, False, role)

if __name__ == "__main__":
    bot = QQBot(WS_URL, WS_TOKEN) 
    while True:
        try:
            logger.info("启动中...")
            bot.start()
        except KeyboardInterrupt:
            break
        except Exception:
            time.sleep(5)
