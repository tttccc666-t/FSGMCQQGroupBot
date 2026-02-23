# QQ Bot based on the NapCatQQ Framework

English | [中文](README.md)

The bot framework currently used by the **FSGMC Community Group**.  
A group chat bot built on **Python** and the **OneBot 11 (NapCatQQ)** protocol.  
It integrates **DeepSeek Large Model conversations**, **Alibaba Cloud AI Drawing/Editing**, and **Qwen-VL Visual Recognition** functions.  
It features a cute "Catgirl" persona, supporting "Poke" interactions, new member welcomes, **Private Chat**, and **Image Understanding**.  
![MIT License](https://img.shields.io/badge/License-MIT_License-blue "MIT License")

## ✨ Features

### 🧠 AI Intelligent Interaction (Multimodal)
- **Smart Chat**: Accesses the DeepSeek V3 model with a distinct "Catgirl" persona. 
  - **Group Mode**: Responds when @mentioned, aware of group context.
  - **Private Mode (New)**: Supports 1-on-1 private chat without @mentioning.
- **👀 Visual Recognition**: Accesses the Alibaba Cloud `qwen-vl-plus` model.
  - **Image Understanding**: Send an image and @mention the bot (or directly in DM), and it will understand the content of the image and reply.
- **🎨 AI Drawing & Editing (New)**: 
  - **Text-to-Image**: Accesses `qwen-image`. Command: `/draw prompt`.
  - **Image-to-Image/Editing**: Accesses `wan2.5-i2i-preview`.
    - Command: Send `/draw prompt` **with 1-3 images attached**.
    - Function: Edits the original image or blends multiple images based on the prompt.
  - Limits: 5 times per day for normal users; unlimited for Administrators/Owner.
- **Fun Interactions**:
  - **Poke**: Double-click the bot's avatar to trigger random cute voice messages or actions.
  - **Group Welcome**: Automatically sends a welcome message when new members join.
  - **Friend Request**: **Automatically accepts** friend requests and sends a greeting.
  - **Like Feedback**: Send "赞我" (Like me), and the bot will like you back 10 times.

### 🛡️ Group Management System
- **Profanity Filter**:
  - Level 1 (Minor): Mute for 10 minutes.
  - Level 2 (Ads): Mute for 1 hour.
  - Level 3 (Severe): Kick from the group immediately.
  - **Auto Recall**: When a violation is detected, the message is recalled first, followed by punishment.
- **Anti-Spam Mechanism**:
  - Message exceeds 1000 characters -> Recall + Mute for 1 hour.
  - Message exceeds 15 lines -> Recall + Mute for 1 hour.
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
   - Alibaba Cloud DashScope API Key (for **Drawing**, **Editing**, and **Vision**)

## 📦 Installation & Configuration

### 1. Install Dependencies

```bash
pip install websocket-client requests
```

### 2. Configure Script

Open your script and modify the **Configuration Area** at the top:

```python
# NapCat Connection Config
WS_URL = "ws://127.0.0.1:2354"  # Keep default if running locally; enter Server IP if running on cloud
WS_TOKEN = "YourToken"          # The Token set in NapCat configuration

# Identity Config
BOT_QQ = 12345678      # The Bot's QQ number
OWNER_QQ = 88888888    # The Owner's QQ number (Highest Permission)

# API Key Config
DEEPSEEK_API_KEY = "sk-xxxxxxxx"
DASHSCOPE_API_KEY = "sk-xxxxxxxx" # Alibaba Cloud Key (Must enable DashScope service)

# Enabled Groups (Private chats are enabled by default)
ENABLED_GROUPS = [123456789, 987654321]
```

### 3. Start the Bot

Ensure NapCatQQ is logged in and running, then execute in the terminal:

```bash
python main.py
```

If you see the log output `WebSocket 连接成功` (WebSocket Connected Successfully), the startup is complete.

## 🎮 Command Manual

### 👥 Common Commands (Group/Private)

| Command/Action | Description | Example |
| :--- | :--- | :--- |
| **@Bot Content** | Chat with AI Catgirl (No @ needed in DM) | `@SleepyCat Hello` |
| **@Bot [Image]** | **Image Understanding** | `@SleepyCat [Image] Look at this` |
| **/draw Prompt** | **Text-to-Image** (Limit 5/day) | `/draw a cat eating fish` |
| **/draw [Image] Prompt** | **Image-to-Image/Edit** (Attach image) | `/draw [Image] make it cyberpunk style` |
| **赞我** | Ask the bot to like you | `赞我` |
| **Double-click Avatar** | Trigger Poke interaction | (Action) |
| **(Add Friend)** | Auto-accept friend request | (Action) |

### 👮‍♂️ Admin/Owner Commands

| Command | Description | Example |
| :--- | :--- | :--- |
| **/mute** | Mute a user | `/mute 123456 10m` (Mute for 10 mins) |
| **/unmute** | Unmute a user | `/unmute 123456` |
| **111睡觉模式** | Force mute target user for 8 hours | `111睡觉模式` |
| **/draw** | AI Image Generation (Unlimited) | `/draw Cyberpunk City` |

## ⚠️ FAQ

**Q: Image-to-Image generation failed?**
A: I2I uses the Alibaba Cloud `wan2.5-i2i-preview` model via asynchronous calls. The bot automatically polls for results. If it fails, check your API Key permissions or if the image content violates policies. Up to 3 images are supported.

**Q: No response or error when sending images?**  
A:  
1. Ensure the image URL provided by NapCat is accessible from the internet.
2. Check your Alibaba Cloud DashScope balance.

## 📝 Disclaimer

This project is for learning and technical research purposes only. Do not use it to send spam, harass others, or engage in any illegal activities. Any costs incurred by using API services (DeepSeek/Alibaba Cloud) are borne by the user.
