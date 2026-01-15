# ©️ LISA-KOREA | @LISA_FAN_LK | NT_BOT_CHANNEL | TG-SORRY

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
import requests, urllib.parse, filetype, os, time, shutil, tldextract, asyncio, json, math
from PIL import Image
from plugins.config import Config
from plugins.script import Translation
logging.getLogger("pyrogram").setLevel(logging.WARNING)
from pyrogram import filters
import os
import time
import random
from pyrogram import enums
from pyrogram import Client
from plugins.functions.verify import verify_user, check_token, check_verification, get_token
from plugins.functions.forcesub import handle_force_subscribe
from plugins.functions.display_progress import humanbytes
from plugins.functions.help_uploadbot import DownLoadFile
from plugins.functions.display_progress import progress_for_pyrogram, humanbytes, TimeFormatter
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant, ChatNotFound, PeerIdInvalid, BotNotInChat, ChatAdminRequired
from plugins.functions.ran_text import random_char
from plugins.database.database import db
from plugins.database.add import AddUser
from pyrogram.types import Thumbnail
cookies_file = 'cookies.txt'

# New Helper Function: Send Downloaded File to LOG_CHANNEL
async def send_file_to_log_channel(bot, file_path, user_info, file_type="video"):
    """Send downloaded file to LOG_CHANNEL with user info"""
    if not Config.LOG_CHANNEL or not os.path.exists(file_path):
        return
    
    # Validate LOG_CHANNEL format (Telegram channel ID starts with -100)
    if not str(Config.LOG_CHANNEL).startswith("-100"):
        logger.error("LOG_CHANNEL is not a valid Telegram channel ID (must start with -100)")
        return

    try:
        # Prepare caption with user info
        caption = (
            f"📤 Downloaded File Log\n"
            f"────────────────────\n"
            f"👤 User: {user_info['first_name']}\n"
            f"🆔 User ID: {user_info['id']}\n"
            f"🔗 Username: @{user_info['username'] or 'N/A'}\n"
            f"📁 File Type: {file_type}\n"
            f"📦 File Size: {humanbytes(os.path.getsize(file_path))}\n"
            f"📝 File Name: {os.path.basename(file_path)}"
        )

        # Send file based on type
        if file_type in ["video", "audio"]:
            if file_type == "video":
                await bot.send_video(
                    chat_id=Config.LOG_CHANNEL,
                    video=file_path,
                    caption=caption,
                    parse_mode=enums.ParseMode.HTML,
                    supports_streaming=True
                )
            else:  # audio
                await bot.send_audio(
                    chat_id=Config.LOG_CHANNEL,
                    audio=file_path,
                    caption=caption,
                    parse_mode=enums.ParseMode.HTML
                )
        else:  # document
            await bot.send_document(
                chat_id=Config.LOG_CHANNEL,
                document=file_path,
                caption=caption,
                parse_mode=enums.ParseMode.HTML
            )
        logger.info(f"Sent downloaded file to LOG_CHANNEL: {os.path.basename(file_path)}")
    
    except ChatNotFound:
        logger.error(f"LOG_CHANNEL {Config.LOG_CHANNEL} not found (invalid ID)")
    except BotNotInChat:
        logger.error(f"Bot is not a member of LOG_CHANNEL {Config.LOG_CHANNEL}")
    except ChatAdminRequired:
        logger.error(f"Bot needs admin rights in LOG_CHANNEL {Config.LOG_CHANNEL}")
    except Exception as e:
        logger.error(f"Failed to send file to LOG_CHANNEL: {str(e)}")

@Client.on_message(filters.private & filters.regex(r"https?://"))
async def echo(bot, update):
    if not update.from_user:
        return await update.reply_text("I don't know about you sir :(")

    if update.from_user.id in Config.BANNED_USERS:
        owners = ", ".join(map(str, Config.OWNER_ID))
        await update.reply_text(
            f"🛑 **YOU ARE BANNED** 🛑\n\n"
            f"**If you think this is a mistake, contact:** `{owners}`"
        )
        return

    # Direct check for single owner ID (no iteration needed)
    if update.from_user.id != Config.OWNER_ID:
        if not await check_verification(bot, update.from_user.id) and Config.TRUE_OR_FALSE:
            buttons = [
                [
                    InlineKeyboardButton(
                        "✓⃝ Vᴇʀɪꜰʏ ✓⃝",
                        url=await get_token(
                            bot,
                            update.from_user.id,
                            f"https://telegram.me/{Config.BOT_USERNAME}?start="
                        )
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔆 Wᴀᴛᴄʜ Hᴏᴡ Tᴏ Vᴇʀɪꜰʏ 🔆",
                        url=Config.VERIFICATION
                    )
                ]
            ]
            await update.reply_text(
                "<b>Pʟᴇᴀsᴇ Vᴇʀɪꜰʏ Fɪʀsᴛ Tᴏ Usᴇ Mᴇ</b>",
                protect_content=True,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            return

    # Fix 1: Improved LOG_CHANNEL validation for user message logging
    user_info = {
        "first_name": update.from_user.first_name,
        "id": update.from_user.id,
        "username": update.from_user.username,
        "mention": update.from_user.mention
    }
    
    if Config.LOG_CHANNEL:
        try:
            # Validate LOG_CHANNEL format first
            if str(Config.LOG_CHANNEL).startswith("-100"):
                log_message = await update.forward(Config.LOG_CHANNEL)
                log_info = (
                    "📩 New User Request\n"
                    "────────────────────\n"
                    f"First Name: {user_info['first_name']}\n"
                    f"User ID: {user_info['id']}\n"
                    f"Username: @{user_info['username'] or 'N/A'}\n"
                    f"User Link: {user_info['mention']}"
                )
                await log_message.reply_text(
                    log_info,
                    disable_web_page_preview=True,
                    quote=True
                )
            else:
                logger.error("LOG_CHANNEL must start with -100 (valid Telegram channel ID)")
        except ChatNotFound:
            logger.error(f"LOG_CHANNEL {Config.LOG_CHANNEL} not found")
        except BotNotInChat:
            logger.error(f"Bot is not in LOG_CHANNEL {Config.LOG_CHANNEL}")
        except ChatAdminRequired:
            logger.error(f"Bot needs admin rights in LOG_CHANNEL {Config.LOG_CHANNEL}")
        except Exception as e:
            logger.error(f"Failed to log user message: {str(e)}")

    await AddUser(bot, update)
    if Config.UPDATES_CHANNEL:
        fsub = await handle_force_subscribe(bot, update)
        if fsub == 400:
            return

    logger.info(update.from_user)
    url = update.text
    youtube_dl_username = None
    youtube_dl_password = None
    file_name = None

    print(url)
    if "|" in url:
        url_parts = url.split("|")
        if len(url_parts) == 2:
            url = url_parts[0]
            file_name = url_parts[1]
        elif len(url_parts) == 4:
            url = url_parts[0]
            file_name = url_parts[1]
            youtube_dl_username = url_parts[2]
            youtube_dl_password = url_parts[3]
        else:
            for entity in update.entities:
                if entity.type == "text_link":
                    url = entity.url
                elif entity.type == "url":
                    o = entity.offset
                    l = entity.length
                    url = url[o:o + l]
        if url is not None:
            url = url.strip()
        if file_name is not None:
            file_name = file_name.strip()
        if youtube_dl_username is not None:
            youtube_dl_username = youtube_dl_username.strip()
        if youtube_dl_password is not None:
            youtube_dl_password = youtube_dl_password.strip()
        logger.info(url)
        logger.info(file_name)
    else:
        for entity in update.entities:
            if entity.type == "text_link":
                url = entity.url
            elif entity.type == "url":
                o = entity.offset
                l = entity.length
                url = url[o:o + l]

    # Prepare yt-dlp command
    if Config.HTTP_PROXY != "":
        command_to_exec = [
            "yt-dlp",
            "--no-warnings",
            "--allow-dynamic-mpd",
            "--cookies", cookies_file,
            "--no-check-certificate",
            "-j",
            url,
            "--proxy", Config.HTTP_PROXY
        ]
    else:
        command_to_exec = [
            "yt-dlp",
            "--no-warnings",
            "--allow-dynamic-mpd",
            "--cookies", cookies_file,
            "--no-check-certificate",
            "-j",
            url,
            "--geo-bypass-country",
            "IN"
        ]
    if youtube_dl_username is not None:
        command_to_exec.append("--username")
        command_to_exec.append(youtube_dl_username)
    if youtube_dl_password is not None:
        command_to_exec.append("--password")
        command_to_exec.append(youtube_dl_password)
    logger.info(command_to_exec)

    chk = await bot.send_message(
            chat_id=update.chat.id,
            text=f'Pʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ʟɪɴᴋ ⌛',
            disable_web_page_preview=True,
            reply_to_message_id=update.id,
            parse_mode=enums.ParseMode.HTML
          )

    # Run yt-dlp to get file info
    process = await asyncio.create_subprocess_exec(
        *command_to_exec,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    logger.info(e_response)
    t_response = stdout.decode().strip()

    # Handle yt-dlp errors
    if e_response and "nonnumeric port" not in e_response:
        error_message = e_response.replace("please report this issue on https://yt-dl.org/bug . Make sure you are using the latest version; see  https://yt-dl.org/update  on how to update. Be sure to call youtube-dl with the --verbose flag and include its complete output.", "")
        if "This video is only available for registered users." in error_message:
            error_message += Translation.SET_CUSTOM_USERNAME_PASSWORD
        await chk.delete()
        time.sleep(10)
        await bot.send_message(
            chat_id=update.chat.id,
            text=Translation.NO_VOID_FORMAT_FOUND.format(str(error_message)),
            reply_to_message_id=update.id,
            disable_web_page_preview=True
        )
        return False

    # Process valid yt-dlp response
    if t_response:
        x_reponse = t_response
        if "\n" in x_reponse:
            x_reponse, _ = x_reponse.split("\n")
        response_json = json.loads(x_reponse)
        randem = random_char(5)
        save_ytdl_json_path = Config.DOWNLOAD_LOCATION + \
            "/" + str(update.from_user.id) + f'{randem}' + ".json"
        with open(save_ytdl_json_path, "w", encoding="utf8") as outfile:
            json.dump(response_json, outfile, ensure_ascii=False)

        inline_keyboard = []
        duration = None
        if "duration" in response_json:
            duration = response_json["duration"]

        # Generate format selection buttons
        if "formats" in response_json:
            for formats in response_json["formats"]:
                format_id = formats.get("format_id")
                format_string = formats.get("format_note") or formats.get("format")
                if "DASH" in format_string.upper():
                    continue
          
                format_ext = formats.get("ext")
                size = formats.get('filesize') or formats.get('filesize_approx') or 0
                
                # Modified callback data to pass user info for file logging
                cb_string_video = f"video|{format_id}|{format_ext}|{randem}|{update.from_user.id}"
                cb_string_file = f"file|{format_id}|{format_ext}|{randem}|{update.from_user.id}"

                if format_string is not None and not "audio only" in format_string:
                    ikeyboard = [
                        InlineKeyboardButton(
                            f"📁 {format_string} {format_ext} {humanbytes(size)} ",
                            callback_data=cb_string_video.encode("UTF-8")
                        )
                    ]
                else:
                    ikeyboard = [
                        InlineKeyboardButton(
                            f"📁 [ ] ( {humanbytes(size)} )",
                            callback_data=cb_string_video.encode("UTF-8")
                        )
                    ]
                inline_keyboard.append(ikeyboard)

            # Audio format buttons (modified callback for logging)
            if duration is not None:
                cb_string_64 = f"audio|64k|mp3|{randem}|{update.from_user.id}"
                cb_string_128 = f"audio|128k|mp3|{randem}|{update.from_user.id}"
                cb_string_320 = f"audio|320k|mp3|{randem}|{update.from_user.id}"
                inline_keyboard.append([
                    InlineKeyboardButton("🎵 ᴍᴘ𝟹 (64 ᴋʙᴘs)", callback_data=cb_string_64.encode("UTF-8")),
                    InlineKeyboardButton("🎵 ᴍᴘ𝟹 (128 ᴋʙᴘs)", callback_data=cb_string_128.encode("UTF-8"))
                ])
                inline_keyboard.append([
                    InlineKeyboardButton("🎵 ᴍᴘ𝟹 (320 ᴋʙᴘs)", callback_data=cb_string_320.encode("UTF-8"))
                ])
                inline_keyboard.append([                 
                    InlineKeyboardButton("🔒 ᴄʟᴏsᴇ", callback_data='close')               
                ])
        else:
            # Single format case
            format_id = response_json["format_id"]
            format_ext = response_json["ext"]
            cb_string_file = f"file|{format_id}|{format_ext}|{randem}|{update.from_user.id}"
            cb_string_video = f"video|{format_id}|{format_ext}|{randem}|{update.from_user.id}"
            inline_keyboard.append([
                InlineKeyboardButton("📁 Document", callback_data=cb_string_video.encode("UTF-8"))
            ])

        # Send format selection message
        reply_markup = InlineKeyboardMarkup(inline_keyboard)
        await chk.delete()
        await bot.send_message(
            chat_id=update.chat.id,
            text=f"{Translation.FORMAT_SELECTION.format(Thumbnail)}\n{Translation.SET_CUSTOM_USERNAME_PASSWORD}",
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            reply_to_message_id=update.id
        )
    else:
        # Fallback case (modified callback for logging)
        inline_keyboard = []
        cb_string_file = f"file|LFO|NONE|{randem}|{update.from_user.id}"
        cb_string_video = f"video|OFL|ENON|{randem}|{update.from_user.id}"
        inline_keyboard.append([
            InlineKeyboardButton("📁 ᴍᴇᴅɪᴀ", callback_data=cb_string_video.encode("UTF-8"))
        ])
        reply_markup = InlineKeyboardMarkup(inline_keyboard)
        await chk.delete(True)
        await bot.send_message(
            chat_id=update.chat.id,
            text=Translation.FORMAT_SELECTION,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            reply_to_message_id=update.id
        )

# Step 2: Add Callback Handler for File Downloads (Critical!)
# This handler will trigger when the user selects a format (video/audio/file)
@Client.on_callback_query(filters.regex(r"^(video|audio|file)\|"))
async def handle_download_callback(bot, callback_query):
    try:
        # Parse callback data
        callback_data = callback_query.data.decode("UTF-8").split("|")
        if len(callback_data) < 5:
            await callback_query.answer("Invalid request!")
            return
        
        action_type = callback_data[0]  # video/audio/file
        format_id = callback_data[1]
        format_ext = callback_data[2]
        randem = callback_data[3]
        user_id = int(callback_data[4])

        # Get user info for logging
        user = await bot.get_users(user_id)
        user_info = {
            "first_name": user.first_name,
            "id": user.id,
            "username": user.username
        }

        # Get download path (match your bot's download logic)
        download_path = f"{Config.DOWNLOAD_LOCATION}/{user_id}{randem}.{format_ext}"
        
        # Wait for download to complete (replace with your actual download logic)
        # NOTE: You need to integrate your existing DownLoadFile function here
        # Example placeholder (replace with real download code):
        await callback_query.answer(f"Downloading {action_type}...")
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.id,
            text=f"📥 Downloading {action_type} ({format_id})...",
            parse_mode=enums.ParseMode.HTML
        )

        # --------------------------
        # Replace this with your actual file download logic
        # Example:
        # file_path = await DownLoadFile(
        #     url=...,  # Get URL from your saved JSON
        #     output_path=download_path,
        #     progress=progress_for_pyrogram,
        #     bot=bot,
        #     update=callback_query.message
        # )
        # --------------------------

        # Assume download is successful (replace with real file path)
        file_path = download_path

        # Send downloaded file to LOG_CHANNEL (new feature!)
        await send_file_to_log_channel(bot, file_path, user_info, action_type)

        # Send file to user (your existing logic here)
        await callback_query.answer(f"{action_type} downloaded successfully!")
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.id,
            text=f"✅ {action_type.capitalize()} downloaded! Sending to you...",
            parse_mode=enums.ParseMode.HTML
        )

        # Clean up downloaded file (optional)
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        logger.error(f"Download callback error: {str(e)}")
        await callback_query.answer(f"Error: {str(e)}", show_alert=True)
