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

# 阿里云绘图 API 配置
DASHSCOPE_API_KEY = "sk-xxxxx"
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

# 绘图限制
DRAW_DAILY_LIMIT = 5

# 启用的群组
ENABLED_GROUPS = [923820685] 

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
SPAM_MAX_LINES = 5   

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
        """消息分发中心"""
        try:
            data = json.loads(message)
            if "echo" in data: return
            
            # 1. 处理群消息 (聊天、指令)
            if data.get('post_type') == 'message' and data.get('message_type') == 'group':
                self.handle_group_message(data)
            
            # 2. 处理通知事件 (戳一戳、进群) <--- 新增
            elif data.get('post_type') == 'notice':
                self.handle_notice(data)

        except Exception as e:
            logger.error(f"处理消息异常: {e}")

    # ---------------- API 封装 ----------------

    def send_ws(self, action, params):
        payload = {"action": action, "params": params, "echo": str(int(time.time()))}
        try:
            self.ws.send(json.dumps(payload))
        except Exception as e:
            logger.error(f"发送 WebSocket 数据失败: {e}")

    def send_group_msg(self, group_id, message):
        self.send_ws("send_group_msg", {"group_id": group_id, "message": message})

    def set_group_ban(self, group_id, user_id, duration):
        self.send_ws("set_group_ban", {"group_id": group_id, "user_id": user_id, "duration": duration})

    def set_group_kick(self, group_id, user_id, reject_add_request=False):
        self.send_ws("set_group_kick", {"group_id": group_id, "user_id": user_id, "reject_add_request": reject_add_request})

    def send_like(self, user_id, times=10):
        self.send_ws("send_like", {"user_id": user_id, "times": times})
    
    def recall_msg(self, message_id):
        if message_id:
            self.send_ws("delete_msg", {"message_id": message_id})

    # ---------------- 新增：通知处理 (戳一戳/进群) ----------------

    def handle_notice(self, data):
        """处理通知事件"""
        notice_type = data.get('notice_type')
        sub_type = data.get('sub_type')
        group_id = data.get('group_id')
        user_id = data.get('user_id')

        # 过滤未启用的群
        if group_id not in ENABLED_GROUPS: return

        # === 1. 戳一戳检测 ===
        # notice_type: notify, sub_type: poke
        if notice_type == 'notify' and sub_type == 'poke':
            target_id = data.get('target_id')
            # 只有当被戳的是机器人(BOT_QQ)时才反应
            if target_id == BOT_QQ:
                logger.info(f"被戳了 - 群:{group_id} 用户:{user_id}")
                # 随机回复库
                replies = [
                    f"[CQ:at,qq={user_id}] 呜哇... 谁在戳我呀？( >﹏< )",
                    f"[CQ:at,qq={user_id}] 哼，不理你 (扭头)",
                    f"[CQ:at,qq={user_id}] 别戳啦，毛都要被你戳掉啦！qwq",
                    f"[CQ:at,qq={user_id}] ( >ω<)ﾉ"
                ]
                self.send_group_msg(group_id, random.choice(replies))

        # === 2. 进群欢迎 ===
        # notice_type: group_increase
        elif notice_type == 'group_increase':
            logger.info(f"新人进群 - 群:{group_id} 用户:{user_id}")
            welcome_msg = f"欢迎新人 [CQ:at,qq={user_id}] 加入本群喵！ ( >ω<)ﾉ"
            self.send_group_msg(group_id, welcome_msg)

    # ---------------- AI 绘图功能 ----------------

    def check_draw_limit(self, user_id, role):
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

    def generate_image(self, group_id, user_id, prompt):
        logger.info(f"绘图请求 - 群:{group_id} 用户:{user_id} 提示词:{prompt}")
        self.send_group_msg(group_id, f"[CQ:at,qq={user_id}] 正在努力画图喵，稍等一下哦 ( >ω<) ...")

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DASHSCOPE_API_KEY}"}
        payload = {
            "model": "qwen-image",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ]
            },
            "parameters": {
                "negative_prompt": "低分辨率，低画质，肢体畸形，手指畸形，画面过饱和，蜡像感，人脸无细节，过度光滑，画面具有AI感。构图混乱。文字模糊，扭曲，过于写实。",
                "prompt_extend": False,
                "watermark": False,
                "size": "1664*928"
            }
        }

        try:
            response = requests.post(DASHSCOPE_URL, headers=headers, json=payload, timeout=90)
            if response.status_code == 200:
                res_json = response.json()
                try:
                    image_url = res_json['output']['choices'][0]['message']['content'][0]['image']
                    self.send_group_msg(group_id, f"[CQ:at,qq={user_id}]\n画好啦！快夸我快夸我(≧∀≦)ゞ \n[CQ:image,file={image_url}]")
                    self.add_draw_count(user_id)
                    logger.info(f"绘图成功: {image_url}")
                except:
                    msg = res_json.get('message', '未知错误')
                    self.send_group_msg(group_id, f"[CQ:at,qq={user_id}] 呜呜... 画笔断掉了 (生成失败：{msg}) qwq")
            else:
                self.send_group_msg(group_id, f"[CQ:at,qq={user_id}] 连接绘画服务器失败惹 (Status: {response.status_code})")
        except Exception as e:
            logger.error(f"绘图请求异常: {e}")
            self.send_group_msg(group_id, f"[CQ:at,qq={user_id}] 绘画发生内部错误，脑子稍微有点乱...")

    # ---------------- AI 聊天功能 ----------------

    def chat_with_deepseek(self, group_id, user_id, content):
        logger.info(f"AI聊天请求 - 群:{group_id} 用户:{user_id}")
        system_prompt = (
            f"你现在的设定如下：\n"
            f"1. 你的名字叫瞌睡猫，是一只可爱的猫娘，说话要带颜文字 ( >ω<), awa, qwq等。\n"
            f"2. 你现在正处于一个QQ群中聊天（群号：{group_id}）。\n"
            f"3. 我会以“【QQ用户:xxxx】说：内容”的格式把消息发给你。\n"
            f"   - 你的主人QQ号是 {OWNER_QQ}，辨别清楚消息发送者QQ号。\n"
            f"   - 你的QQ号是 {BOT_QQ}。\n"
            f"4. 回复要简短（50字以内）。\n"
        )
        user_input_with_context = f"【QQ用户:{user_id}】说：{content}"
        
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input_with_context}],
            "stream": False
        }

        try:
            response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=15)
            if response.status_code == 200:
                reply = response.json()['choices'][0]['message']['content'].replace("瞌睡猫：", "").strip()
                self.send_group_msg(group_id, f"[CQ:at,qq={user_id}] {reply}")
            else:
                self.send_group_msg(group_id, "喵... 脑子短路了 (API Error)")
        except Exception as e:
            logger.error(f"DeepSeek 请求异常: {e}")

    # ---------------- 违规检测 (含撤回) ----------------

    def check_violation(self, raw_message, message_id, group_id, user_id, role):
        if role in ['admin', 'owner']: return False
        
        pure_text = re.sub(r'\[CQ:.*?\]', '', raw_message)
        
        if len(pure_text) > SPAM_MAX_LEN:
            self.recall_msg(message_id) 
            self.set_group_ban(group_id, user_id, 3600)
            self.send_group_msg(group_id, f"[CQ:at,qq={user_id}] 呜哇，字太多啦！眼睛要看花了好过分！( >﹏< )")
            return True
        
        if pure_text.count('\n') > SPAM_MAX_LINES:
            self.recall_msg(message_id) 
            self.set_group_ban(group_id, user_id, 3600)
            self.send_group_msg(group_id, f"[CQ:at,qq={user_id}] 不要竖着发天书啦，屏幕要被撑破了！(｀Д´)")
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

    def handle_group_message(self, data):
        group_id = data.get('group_id')
        user_id = data.get('user_id')
        message_id = data.get('message_id')
        raw_message = data.get('raw_message', "")
        role = data.get('sender', {}).get('role', 'member')

        if ENABLED_GROUPS and group_id not in ENABLED_GROUPS: return

        if self.check_violation(raw_message, message_id, group_id, user_id, role): return

        # 绘画命令
        if raw_message.startswith("/绘画") or raw_message.startswith("/draw"):
            prompt = raw_message.replace("/绘画", "").replace("/draw", "").strip()
            if not prompt:
                self.send_group_msg(group_id, "想画什么呢？要告诉我描述哦 (例如 /绘画 可爱的猫娘)")
                return
            allowed, remaining = self.check_draw_limit(user_id, role)
            if not allowed:
                self.send_group_msg(group_id, f"[CQ:at,qq={user_id}] 呜... 画笔没墨水了，明天再来找我画画吧 (每日限{DRAW_DAILY_LIMIT}次) (qwq)")
                return
            threading.Thread(target=self.generate_image, args=(group_id, user_id, prompt)).start()
            return

        # 111睡觉模式
        if raw_message == "111睡觉模式":
            if role in ['admin', 'owner'] or user_id == OWNER_QQ:
                self.set_group_ban(group_id, TARGET_111_QQ, 8 * 3600)
                self.send_group_msg(group_id, f"收到！这就让TA强制睡觉觉！(禁言8小时) (¦3[▓▓]")
            else:
                self.send_group_msg(group_id, "你不是我主人，才不听你的呢 (哼)")
            return

        # 点赞
        if raw_message == "赞我":
            self.send_like(user_id, times=10)
            self.send_group_msg(group_id, f"[CQ:at,qq={user_id}] 给你点赞啦！要开心哦 ( >ω<)")
            return

        # 管理员指令
        if raw_message.startswith("/mute") or raw_message.startswith("/unmute") or raw_message.startswith("/status"):
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

        # AI 聊天
        if f"[CQ:at,qq={BOT_QQ}]" in raw_message:
            clean_content = raw_message.replace(f"[CQ:at,qq={BOT_QQ}]", "").strip() or "你好"
            threading.Thread(target=self.chat_with_deepseek, args=(group_id, user_id, clean_content)).start()

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
