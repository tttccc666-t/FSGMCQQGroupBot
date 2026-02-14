# QQ Bot based on the NapCatQQ Framework

English | [中文](README.md)

The bot framework currently used by the **FSGMC Community Group**.  
A group chat bot built on **Python** and the **OneBot 11 (NapCatQQ)** protocol.  
It integrates **DeepSeek Large Model conversations**, **Alibaba Cloud Tongyi Wanxiang AI drawing**, and **automated group management** functions.  
It features a cute "Catgirl" persona, supporting "Poke" interactions and new member welcomes.  
![MIT License](https://img.shields.io/badge/License-MIT_License-blue "MIT License")

## ✨ Features

### 🧠 AI Intelligent Interaction
- **Smart Chat**: Accesses the DeepSeek V3 model with a distinct "Catgirl" persona. Supports context-aware conversations (triggered when @mentioned).
- **AI Drawing**: Accesses the Alibaba Cloud `qwen-image-max` model for high-quality text-to-image generation.
  - Command: `/绘画 prompt` or `/draw prompt`.
  - Limits: 5 times per day for normal users; unlimited for Administrators/Owner.
- **Fun Interactions**:
  - **Poke**: Double-click the bot's avatar to trigger random cute voice messages or actions.
  - **Group Welcome**: Automatically sends a welcome message when new members join.
  - **Like Feedback**: Send "赞我" (Like me), and the bot will like you back 10 times.

### 🛡️ Group Management System
- **Profanity Filter**:
  - Level 1 (Minor): Mute for 10 minutes.
  - Level 2 (Ads): Mute for 1 hour.
  - Level 3 (Severe): Kick from the group immediately.
  - **Auto Recall**: When a violation is detected, the message is recalled first, followed by punishment.
- **Anti-Spam Mechanism**:
  - Message exceeds 300 characters -> Recall + Mute for 1 hour.
  - Message exceeds 10 lines -> Recall + Mute for 1 hour.
  - *Smart Recognition: Automatically filters [CQ Codes] (e.g., stickers) to prevent false positives.*
- **Admin Commands**:
  - `/mute QQ_ID Time(s/m/h)`: Mute a specific user.
  - `/unmute QQ_ID`: Unmute a user.
  - `111睡觉模式` (111 Sleep Mode): One-click mute for a specific target for 8 hours (Forced Sleep).

## 🛠️ Environment Dependencies

1. **Python 3.8+**
2. **NapCatQQ** (or other OneBot 11 implementations), with a configured **Websocket Server**.
3. **API Keys**:
   - DeepSeek API Key (for Chat)
   - Alibaba Cloud DashScope API Key (for Drawing)

## 📦 Installation & Configuration

### 1. Install Dependencies

```bash
pip install websocket-client requests
```

### 2. Configure `main.py`

Open `main.py` and modify the **Configuration Area** at the top according to your actual setup:

```python
# NapCat Connection Config
WS_URL = "ws://127.0.0.1:2354"  # Keep default if running locally; enter Server IP if running on cloud
WS_TOKEN = "YourToken"          # The Token set in NapCat configuration

# Identity Config
BOT_QQ = 12345678      # The Bot's QQ number
OWNER_QQ = 88888888    # The Owner's QQ number (Highest Permission)
TARGET_111_QQ = 0      # The specific target QQ for "111 Sleep Mode"

# API Key Config
DEEPSEEK_API_KEY = "sk-xxxxxxxx"
DASHSCOPE_API_KEY = "sk-xxxxxxxx" # Alibaba Cloud Key

# Enabled Groups (Bot will only respond in groups listed here)
ENABLED_GROUPS = [123456789, 987654321]
```

### 3. Start the Bot

Ensure NapCatQQ is logged in and running, then execute in the terminal:

```bash
python main.py
```

If you see the log output `WebSocket 连接成功` (WebSocket Connected Successfully), the startup is complete.

## 🎮 Command Manual

### 👥 Normal User Commands

| Command/Action | Description | Example |
| :--- | :--- | :--- |
| **@Bot Content** | Chat with the AI Catgirl | `@SleepyCat Hello there` |
| **/draw Prompt** | AI Image Generation (Limit 5/day) | `/draw a cat eating fish` |
| **赞我** | Ask the bot to like you | `赞我` |
| **Double-click Avatar** | Trigger Poke interaction | (Action) |
| **(Join Group)** | Trigger Welcome Message | (Action) |

### 👮‍♂️ Admin/Owner Commands

| Command | Description | Example |
| :--- | :--- | :--- |
| **/mute** | Mute a user | `/mute 123456 10m` (Mute for 10 mins) |
| **/unmute** | Unmute a user | `/unmute 123456` |
| **111睡觉模式** | Force mute target user for 8 hours | `111睡觉模式` |
| **/draw** | AI Image Generation (Unlimited) | `/draw Cyberpunk City` |

## ⚠️ FAQ

**Q: Error `[WinError 10060]` Connection Timeout during startup?**
A: Please check `WS_URL`. If the script and NapCat are on the same computer, use `ws://127.0.0.1:2354`. If they are not on the same computer, ensure the server firewall allows port 2354 and NapCat is listening on `0.0.0.0`.

## 📝 Disclaimer

This project is for learning and technical research purposes only. Do not use it to send spam, harass others, or engage in any illegal activities. Any costs incurred by using API services (DeepSeek/Alibaba Cloud) are borne by the user.
