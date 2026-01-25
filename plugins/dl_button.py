
import logging
import re
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
import asyncio
import aiohttp
import json
import math
import os
import shutil
import time
from datetime import datetime
from plugins.config import Config
from plugins.script import Translation
from plugins.thumbnail import *
from plugins.database.database import db
logging.getLogger("pyrogram").setLevel(logging.WARNING)
from plugins.functions.display_progress import progress_for_pyrogram, humanbytes, TimeFormatter
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from PIL import Image
from pyrogram import enums 

async def send_upload_log(bot, update, file_path, file_type, original_url=None, sent_msg=None):
    """Forward the uploaded file to log channel with full caption - NO SEPARATE LOG MESSAGE"""
    if not hasattr(Config, 'LOG_CHANNEL') or not Config.LOG_CHANNEL:
        return
    
    try:
        user = update.from_user
        
        # Get file info
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
        else:
            file_size = 0
            
        file_name = os.path.basename(file_path)
        
        # Clean file name - remove format number and extension
        clean_file_name = file_name
        # Remove trailing format numbers before extension
        clean_file_name = re.sub(r'_\d+(?=\.\w+$)', '', clean_file_name)
        # Remove extension
        clean_file_name = os.path.splitext(clean_file_name)[0]
        
        # Get duration for audio/video files
        duration = "N/A"
        if file_type in ["AUDIO", "VIDEO", "VIDEO_NOTE"]:
            try:
                if file_type == "AUDIO":
                    dur = await Mdata03(file_path)
                    if dur:
                        duration = f"{dur // 60}:{dur % 60:02d}"
                elif file_type == "VIDEO":
                    width, height, dur = await Mdata01(file_path)
                    if dur:
                        duration = f"{dur // 60}:{dur % 60:02d}"
                elif file_type == "VIDEO_NOTE":
                    width, dur = await Mdata02(file_path)
                    if dur:
                        duration = f"{dur // 60}:{dur % 60:02d}"
            except Exception as e:
                logger.error(f"Error getting duration: {e}")
        
        # Create FULL CAPTION for the forwarded file
        if file_type in ["AUDIO", "VIDEO"]:
            full_caption = f"""{clean_file_name}

👤 **User:** {user.first_name} {user.last_name if user.last_name else ''}
🆔 **ID:** {user.id}
📁 **File Info:**
├ File Type: {file_type}
├ File Size: {humanbytes(file_size)}
└ Duration: {duration}
🔗 **Original URL:** {original_url if original_url else 'Direct Upload'}"""
        else:
            full_caption = f"""{clean_file_name}

👤 **User:** {user.first_name} {user.last_name if user.last_name else ''}
🆔 **ID:** {user.id}
🔗 **Original URL:** {original_url if original_url else 'Direct Upload'}"""
        
        # Forward the uploaded file to log channel WITH FULL CAPTION ONLY
        if sent_msg:
            try:
                # Forward with the full caption
                await sent_msg.copy(
                    chat_id=Config.LOG_CHANNEL,
                    caption=full_caption,
                    parse_mode=enums.ParseMode.MARKDOWN
                )
                logger.info(f"✅ Forwarded {file_type} to log channel with full caption")
            except Exception as e:
                logger.error(f"Failed to forward file to log channel: {e}")
                # Try alternative method if copy fails
                try:
                    if file_type == "AUDIO" and os.path.exists(file_path):
                        dur = await Mdata03(file_path) if hasattr('Mdata03', '__call__') else None
                        await bot.send_audio(
                            chat_id=Config.LOG_CHANNEL,
                            audio=file_path,
                            caption=full_caption,
                            duration=dur if dur else None,
                            parse_mode=enums.ParseMode.MARKDOWN
                        )
                    elif file_type == "VIDEO" and os.path.exists(file_path):
                        width, height, dur = await Mdata01(file_path) if hasattr('Mdata01', '__call__') else (None, None, None)
                        await bot.send_video(
                            chat_id=Config.LOG_CHANNEL,
                            video=file_path,
                            caption=full_caption,
                            duration=dur if dur else None,
                            width=width if width else None,
                            height=height if height else None,
                            supports_streaming=True,
                            parse_mode=enums.ParseMode.MARKDOWN
                        )
                    elif file_type == "DOCUMENT" and os.path.exists(file_path):
                        await bot.send_document(
                            chat_id=Config.LOG_CHANNEL,
                            document=file_path,
                            caption=full_caption,
                            parse_mode=enums.ParseMode.MARKDOWN
                        )
                except Exception as e2:
                    logger.error(f"Alternative forwarding also failed: {e2}")
                
    except Exception as e:
        logger.error(f"Failed to forward file to log channel: {e}")

async def ddl_call_back(bot, update):
    logger.info(update)
    cb_data = update.data
    tg_send_type, youtube_dl_format, youtube_dl_ext = cb_data.split("=")
    thumb_image_path = Config.DOWNLOAD_LOCATION + "/" + str(update.from_user.id) + ".jpg"
    youtube_dl_url = update.message.reply_to_message.text
    custom_file_name = os.path.basename(youtube_dl_url)
    
    if "|" in youtube_dl_url:
        url_parts = youtube_dl_url.split("|")
        if len(url_parts) == 2:
            youtube_dl_url = url_parts[0]
            custom_file_name = url_parts[1]
        else:
            for entity in update.message.reply_to_message.entities:
                if entity.type == "text_link":
                    youtube_dl_url = entity.url
                elif entity.type == "url":
                    o = entity.offset
                    l = entity.length
                    youtube_dl_url = youtube_dl_url[o:o + l]
        if youtube_dl_url is not None:
            youtube_dl_url = youtube_dl_url.strip()
        if custom_file_name is not None:
            custom_file_name = custom_file_name.strip()
        logger.info(youtube_dl_url)
        logger.info(custom_file_name)
    else:
        for entity in update.message.reply_to_message.entities:
            if entity.type == "text_link":
                youtube_dl_url = entity.url
            elif entity.type == "url":
                o = entity.offset
                l = entity.length
                youtube_dl_url = youtube_dl_url[o:o + l]
    
    description = Translation.CUSTOM_CAPTION_UL_FILE
    start = datetime.now()
    
    # ✅ Initial DOWNLOAD message
    await update.message.edit_caption(
        caption=f"**📥 Downloading...**\nFile: `{custom_file_name}`\nProgress: 0%"
    )
    
    tmp_directory_for_each_user = Config.DOWNLOAD_LOCATION + "/" + str(update.from_user.id)
    if not os.path.isdir(tmp_directory_for_each_user):
        os.makedirs(tmp_directory_for_each_user)
    download_directory = tmp_directory_for_each_user + "/" + custom_file_name
    
    # ✅ Download with progress
    async with aiohttp.ClientSession() as session:
        c_time = time.time()
        try:
            await download_coroutine(
                bot,
                session,
                youtube_dl_url,
                download_directory,
                update.message,  # Pass message object instead of chat_id and message_id
                c_time
            )
        except asyncio.TimeoutError:
            await bot.edit_message_text(
                text=Translation.SLOW_URL_DECED,
                chat_id=update.message.chat.id,
                message_id=update.message.id
            )
            return False
    
    if os.path.exists(download_directory):
        end_one = datetime.now()
        
        # ✅ Start UPLOAD
        await update.message.edit_caption(
            caption=f"**📤 Uploading...**\nFile: `{custom_file_name}`\nProgress: 0%"
        )
        
        file_size = Config.TG_MAX_FILE_SIZE + 1
        try:
            file_size = os.stat(download_directory).st_size
        except FileNotFoundError as exc:
            download_directory = os.path.splitext(download_directory)[0] + ".mkv"
            file_size = os.stat(download_directory).st_size
        
        if file_size > Config.TG_MAX_FILE_SIZE:
            await update.message.edit_caption(
                caption=Translation.RCHD_TG_API_LIMIT
            )
        else:
            start_time = time.time()
            sent_msg = None
            file_type_for_log = "VIDEO"
            
            if (await db.get_upload_as_doc(update.from_user.id)) is False:
                thumbnail = await Gthumb01(bot, update)
                sent_msg = await update.message.reply_document(
                    document=download_directory,
                    thumb=thumbnail,
                    caption=description,
                    parse_mode=enums.ParseMode.HTML,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        "Uploading to Telegram...",
                        update.message,
                        start_time
                    )
                )
                file_type_for_log = "DOCUMENT"
            else:
                width, height, duration = await Mdata01(download_directory)
                thumb_image_path = await Gthumb02(bot, update, duration, download_directory)
                sent_msg = await update.message.reply_video(
                    video=download_directory,
                    caption=description,
                    duration=duration,
                    width=width,
                    height=height,
                    supports_streaming=True,
                    parse_mode=enums.ParseMode.HTML,
                    thumb=thumb_image_path,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        "Uploading to Telegram...",
                        update.message,
                        start_time
                    )
                )
            
            if tg_send_type == "audio":
                duration = await Mdata03(download_directory)
                thumbnail = await Gthumb01(bot, update)
                sent_msg = await update.message.reply_audio(
                    audio=download_directory,
                    caption=description,
                    parse_mode=enums.ParseMode.HTML,
                    duration=duration,
                    thumb=thumbnail,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        "Uploading to Telegram...",
                        update.message,
                        start_time
                    )
                )
                file_type_for_log = "AUDIO"
            elif tg_send_type == "vm":
                width, duration = await Mdata02(download_directory)
                thumbnail = await Gthumb02(bot, update, duration, download_directory)
                sent_msg = await update.message.reply_video_note(
                    video_note=download_directory,
                    duration=duration,
                    length=width,
                    thumb=thumbnail,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        "Uploading to Telegram...",
                        update.message,
                        start_time
                    )
                )
                file_type_for_log = "VIDEO_NOTE"
            
            # ✅ Forward to log channel
            await send_upload_log(bot, update, download_directory, file_type_for_log, youtube_dl_url, sent_msg)
            
            end_two = datetime.now()
            try:
                os.remove(download_directory)
                if os.path.exists(thumb_image_path):
                    os.remove(thumb_image_path)
            except:
                pass
            
            time_taken_for_download = (end_one - start).seconds
            time_taken_for_upload = (end_two - end_one).seconds
           #await update.message.edit_caption(
                #caption=Translation.AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS.format(time_taken_for_download, time_taken_for_upload),
                #parse_mode=enums.ParseMode.HTML
            #)
    else:
        await update.message.edit_caption(
            caption=Translation.NO_VOID_FORMAT_FOUND.format("Incorrect Link"),
            parse_mode=enums.ParseMode.HTML
        )

async def download_coroutine(bot, session, url, file_name, message, start):
    """Download coroutine with progress bar"""
    downloaded = 0
    
    try:
        async with session.get(url, timeout=Config.PROCESS_MAX_TIMEOUT) as response:
            total_length = int(response.headers.get("Content-Length", 0))
            content_type = response.headers.get("Content-Type", "")
            
            if "text" in content_type and total_length < 500:
                return await response.release()
            
            with open(file_name, "wb") as f_handle:
                while True:
                    chunk = await response.content.read(Config.CHUNK_SIZE)
                    if not chunk:
                        break
                    f_handle.write(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    diff = now - start
                    
                    # ✅ Update download progress
                    if round(diff % 5.00) == 0 or downloaded == total_length:
                        await progress_for_pyrogram(
                            current=downloaded,
                            total=total_length,
                            ud_type="Downloading from URL",
                            message=message,
                            start=start,
                            progress_type="download"
                        )
            
            return await response.release()
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise