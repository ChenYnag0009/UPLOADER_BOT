
import logging
import asyncio
import json
import os
import shutil
import time
import re
from datetime import datetime
from pyrogram import enums
from pyrogram.types import InputMediaPhoto
from plugins.config import Config
from plugins.script import Translation
from plugins.thumbnail import *
from plugins.functions.display_progress import progress_for_pyrogram, humanbytes
from plugins.database.database import db
from PIL import Image
from plugins.functions.ran_text import random_char

cookies_file = 'cookies.txt'
# Set up logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

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

async def youtube_dl_call_back(bot, update):
    cb_data = update.data
    tg_send_type, youtube_dl_format, youtube_dl_ext, ranom = cb_data.split("|")
    random1 = random_char(5)
    
    save_ytdl_json_path = os.path.join(Config.DOWNLOAD_LOCATION, f"{update.from_user.id}{ranom}.json")
    
    try:
        with open(save_ytdl_json_path, "r", encoding="utf8") as f:
            response_json = json.load(f)
    except FileNotFoundError as e:
        logger.error(f"JSON file not found: {e}")
        await update.message.delete()
        return False
    
    youtube_dl_url = update.message.reply_to_message.text
    custom_file_name = f"{response_json.get('title')}_{youtube_dl_format}.{youtube_dl_ext}"
    youtube_dl_username = None
    youtube_dl_password = None
    
    if "|" in youtube_dl_url:
        url_parts = youtube_dl_url.split("|")
        if len(url_parts) == 2:
            youtube_dl_url, custom_file_name = url_parts
        elif len(url_parts) == 4:
            youtube_dl_url, custom_file_name, youtube_dl_username, youtube_dl_password = url_parts
        else:
            for entity in update.message.reply_to_message.entities:
                if entity.type == "text_link":
                    youtube_dl_url = entity.url
                elif entity.type == "url":
                    o = entity.offset
                    l = entity.length
                    youtube_dl_url = youtube_dl_url[o:o + l]
                    
        youtube_dl_url = youtube_dl_url.strip()
        custom_file_name = custom_file_name.strip()
        if youtube_dl_username:
            youtube_dl_username = youtube_dl_username.strip()
        if youtube_dl_password:
            youtube_dl_password = youtube_dl_password.strip()
        
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

    # ============================================================
    # PHASE 1: SIMULATED PROGRESS (0-100%)
    # ============================================================
    logger.info("🎬 Starting PHASE 1: Simulated Progress (0-100%)")
    simulated_start_time = time.time()
    
    # ✅ Initial message for SIMULATED progress
    await update.message.edit_caption(
        caption=f"**🔄 Preparing download...**\nFile: `{custom_file_name}`\nProgress: 0%"
    )
    
    description = Translation.CUSTOM_CAPTION_UL_FILE
    if "fulltitle" in response_json:
        description = response_json["fulltitle"][0:1021]
    
    tmp_directory_for_each_user = os.path.join(Config.DOWNLOAD_LOCATION, f"{update.from_user.id}{random1}")
    os.makedirs(tmp_directory_for_each_user, exist_ok=True)
    download_directory = os.path.join(tmp_directory_for_each_user, custom_file_name)
    
    # ✅ Get REAL file size from response_json
    estimated_size = 0
    
    # Try to get actual file size from formats in response_json
    if "formats" in response_json:
        for fmt in response_json["formats"]:
            if fmt.get("format_id") == youtube_dl_format:
                if fmt.get("filesize"):
                    estimated_size = fmt.get("filesize")
                    logger.info(f"✅ Using exact filesize from format: {humanbytes(estimated_size)}")
                    break
                elif fmt.get("filesize_approx"):
                    estimated_size = fmt.get("filesize_approx")
                    logger.info(f"✅ Using approximate filesize from format: {humanbytes(estimated_size)}")
                    break
    
    # If still no size, use response_json size
    if estimated_size == 0:
        if response_json.get('filesize'):
            estimated_size = response_json.get('filesize')
            logger.info(f"✅ Using filesize from response_json: {humanbytes(estimated_size)}")
        elif response_json.get('filesize_approx'):
            estimated_size = response_json.get('filesize_approx')
            logger.info(f"✅ Using filesize_approx from response_json: {humanbytes(estimated_size)}")
    
    # If still no size, use a reasonable default
    if estimated_size == 0:
        if youtube_dl_format in ["320", "256", "192", "best"]:
            estimated_size = 100 * 1024 * 1024  # 100MB for high quality
        else:
            estimated_size = 50 * 1024 * 1024  # 50MB default
        logger.info(f"⚠️ No filesize info, using default: {humanbytes(estimated_size)}")
    
    logger.info(f"📊 Estimated size for progress: {humanbytes(estimated_size)}")
    
    # ✅ Function for SIMULATED PROGRESS (0-100%)
    async def simulate_progress():
        """Simulated progress for initial preparation"""
        try:
            for i in range(1, 101):
                await asyncio.sleep(0.15)  # Fast updates for smooth progress
                
                # Simulate based on time
                simulated_size = (i / 100) * estimated_size
                
                try:
                    await progress_for_pyrogram(
                        current=int(simulated_size),
                        total=int(estimated_size),
                        ud_type=f"Preparing: {custom_file_name[:30]}...",
                        message=update.message,
                        start=simulated_start_time,
                        progress_type="simulated"
                    )
                    logger.info(f"🔄 Simulated progress: {i}%")
                except Exception as e:
                    logger.error(f"Simulated progress error: {e}")
                
                # Stop early if real file exists
                if os.path.exists(download_directory):
                    logger.info("✅ Real file detected, stopping simulation")
                    return i
            
            logger.info("✅ Simulated progress completed 100%")
            return 100
        except asyncio.CancelledError:
            logger.info("Simulated progress cancelled")
            raise
        except Exception as e:
            logger.error(f"Simulated progress failed: {e}")
            return 0
    
    # ✅ Start SIMULATED progress
    simulated_task = asyncio.create_task(simulate_progress())
    
    # ============================================================
    # PHASE 2: DOWNLOAD PROGRESS (0-100%)
    # ============================================================
    
    # ✅ Command for download
    command_to_exec = [
        "yt-dlp",
        "-c",
        "--progress",
        "--newline",
        "--max-filesize", str(Config.TG_MAX_FILE_SIZE),
        "--embed-subs",
        "-f", f"{youtube_dl_format}bestvideo+bestaudio/best",
        "--hls-prefer-ffmpeg",
        "--cookies", cookies_file,
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        youtube_dl_url,
        "-o", download_directory
    ]
    
    if tg_send_type == "audio":
        command_to_exec = [
            "yt-dlp",
            "-c",
            "--progress",
            "--newline",
            "--max-filesize", str(Config.TG_MAX_FILE_SIZE),
            "--bidi-workaround",
            "--extract-audio",
            "--cookies", cookies_file,
            "--audio-format", youtube_dl_ext,
            "--audio-quality", youtube_dl_format,
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            youtube_dl_url,
            "-o", download_directory
        ]
    
    if Config.HTTP_PROXY:
        command_to_exec.extend(["--proxy", Config.HTTP_PROXY])
    if youtube_dl_username:
        command_to_exec.extend(["--username", youtube_dl_username])
    if youtube_dl_password:
        command_to_exec.extend(["--password", youtube_dl_password])
    
    command_to_exec.append("--no-warnings")
    
    logger.info(f"🚀 Executing yt-dlp command...")
    
    # ✅ Start download process
    process = await asyncio.create_subprocess_exec(
        *command_to_exec,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    # ✅ Function to parse yt-dlp progress
    async def parse_ytdlp_progress():
        """Parse yt-dlp progress output for real download"""
        while True:
            try:
                line = await process.stderr.readline()
                if not line:
                    break
                
                line = line.decode('utf-8', errors='ignore').strip()
                
                # Parse progress lines
                if '[download]' in line and '%' in line:
                    try:
                        # Extract percentage
                        match = re.search(r'(\d+\.\d+|\d+)%', line)
                        if match:
                            percentage = float(match.group(1))
                            
                            # Cancel simulated task
                            if not simulated_task.done():
                                simulated_task.cancel()
                                logger.info("✅ Cancelled simulated progress")
                            
                            # Extract size
                            size_match = re.search(r'(\d+\.\d+|\d+)([KMGT]?iB)', line)
                            if size_match:
                                size_num = float(size_match.group(1))
                                size_unit = size_match.group(2).upper()
                                
                                # Convert to bytes
                                units = {'B': 1, 'KIB': 1024, 'MIB': 1024**2, 'GIB': 1024**3, 'TIB': 1024**4}
                                current_size = size_num * units.get(size_unit, 1)
                                
                                # Update DOWNLOAD progress
                                await progress_for_pyrogram(
                                    current=int(current_size),
                                    total=int(estimated_size),
                                    ud_type=f"Downloading: {custom_file_name[:30]}...",
                                    message=update.message,
                                    start=simulated_start_time,
                                    progress_type="download"
                                )
                                
                                logger.info(f"📥 Download progress: {line}")
                    except Exception as e:
                        logger.debug(f"Error parsing progress: {e}")
            except Exception as e:
                logger.error(f"Error reading stderr: {e}")
                break
    
    # ✅ Start parsing progress
    parse_task = asyncio.create_task(parse_ytdlp_progress())
    
    # ✅ Function to monitor file size
    async def monitor_file_progress():
        """Monitor file size for progress updates"""
        last_size = 0
        while True:
            try:
                if os.path.exists(download_directory):
                    current_size = os.path.getsize(download_directory)
                    if current_size != last_size and current_size > 0:
                        last_size = current_size
                        
                        # Update progress
                        await progress_for_pyrogram(
                            current=current_size,
                            total=estimated_size,
                            ud_type=f"Downloading: {custom_file_name[:30]}...",
                            message=update.message,
                            start=simulated_start_time,
                            progress_type="download"
                        )
                        
                        percentage = min(99, (current_size / estimated_size) * 100)
                        logger.info(f"📥 File progress: {percentage:.1f}% ({humanbytes(current_size)})")
                
                await asyncio.sleep(1)
            except:
                await asyncio.sleep(1)
    
    # ✅ Start file monitoring
    monitor_task = asyncio.create_task(monitor_file_progress())
    
    # ✅ Wait for download to complete
    try:
        await process.wait()
        
        # Cancel all tasks
        if not simulated_task.done():
            simulated_task.cancel()
        if not parse_task.done():
            parse_task.cancel()
        if not monitor_task.done():
            monitor_task.cancel()
        
    except Exception as e:
        logger.error(f"Download process error: {e}")
        await update.message.edit_caption(
            caption=f"**❌ Download Error**\n{str(e)[:200]}"
        )
        return False
    
    # ✅ Check download result
    if process.returncode != 0:
        logger.error(f"yt-dlp failed with return code {process.returncode}")
        await update.message.edit_caption(
            caption=f"**❌ Download Failed**\nReturn code: {process.returncode}"
        )
        return False
    
    # ✅ Find downloaded file
    downloaded_file = None
    if os.path.exists(download_directory):
        downloaded_file = download_directory
    else:
        try:
            for file in os.listdir(tmp_directory_for_each_user):
                file_path = os.path.join(tmp_directory_for_each_user, file)
                if os.path.isfile(file_path) and not file.endswith('.part'):
                    downloaded_file = file_path
                    logger.info(f"✅ Found downloaded file: {file}")
                    break
        except Exception as e:
            logger.error(f"Error finding file: {e}")
    
    if not downloaded_file or not os.path.exists(downloaded_file):
        logger.error(f"❌ Downloaded file not found")
        await update.message.edit_caption(
            caption=Translation.DOWNLOAD_FAILED
        )
        return False
    
    # ✅ Final download progress update (100%)
    try:
        final_size = os.path.getsize(downloaded_file)
        await progress_for_pyrogram(
            current=final_size,
            total=final_size,
            ud_type=f"Download Complete!",
            message=update.message,
            start=simulated_start_time,
            progress_type="download"
        )
        logger.info(f"✅ Download completed: {humanbytes(final_size)}")
    except Exception as e:
        logger.error(f"Error in final progress update: {e}")
    
    # ✅ Check file size limit
    try:
        file_size = os.path.getsize(downloaded_file)
        if file_size > Config.TG_MAX_FILE_SIZE:
            await update.message.edit_caption(
                caption=Translation.RCHD_TG_API_LIMIT.format(
                    int(time.time() - simulated_start_time),
                    humanbytes(file_size)
                )
            )
            try:
                shutil.rmtree(tmp_directory_for_each_user)
            except:
                pass
            return False
    except:
        pass
    
    # ============================================================
    # PHASE 3: UPLOAD PROGRESS (0-100%)
    # ============================================================
    logger.info("🎬 Starting PHASE 3: Upload Progress (0-100%)")
    
    # ✅ Start UPLOAD
    upload_start_time = time.time()
    
    # ✅ Initial message for UPLOAD progress
    await update.message.edit_caption(
        caption=f"**📤 Uploading to Telegram...**\nFile: `{custom_file_name}`\nProgress: 0%"
    )
    
    sent_msg = None
    file_type_for_log = "VIDEO"
    
    try:
        if not await db.get_upload_as_doc(update.from_user.id):
            thumbnail = await Gthumb01(bot, update)
            # ✅ UPLOAD PROGRESS (progress_type="upload" is default)
            sent_msg = await update.message.reply_document(
                document=downloaded_file,
                thumb=thumbnail,
                caption=description,
                progress=progress_for_pyrogram,
                progress_args=(
                    "Uploading to Telegram...",
                    update.message,
                    upload_start_time
                    # progress_type="upload" is default
                )
            )
            file_type_for_log = "DOCUMENT"
        else:
            width, height, duration = await Mdata01(downloaded_file)
            thumb_image_path = await Gthumb02(bot, update, duration, downloaded_file)
            sent_msg = await update.message.reply_video(
                video=downloaded_file,
                caption=description,
                duration=duration,
                width=width,
                height=height,
                supports_streaming=True,
                thumb=thumb_image_path,
                progress=progress_for_pyrogram,
                progress_args=(
                    "Uploading to Telegram...",
                    update.message,
                    upload_start_time
                    # progress_type="upload" is default
                )
            )
        
        if tg_send_type == "audio":
            duration = await Mdata03(downloaded_file)
            thumbnail = await Gthumb01(bot, update)
            sent_msg = await update.message.reply_audio(
                audio=downloaded_file,
                caption=description,
                duration=duration,
                thumb=thumbnail,
                progress=progress_for_pyrogram,
                progress_args=(
                    "Uploading to Telegram...",
                    update.message,
                    upload_start_time
                    # progress_type="upload" is default
                )
            )
            file_type_for_log = "AUDIO"
        elif tg_send_type == "vm":
            width, duration = await Mdata02(downloaded_file)
            thumbnail = await Gthumb02(bot, update, duration, downloaded_file)
            sent_msg = await update.message.reply_video_note(
                video_note=downloaded_file,
                duration=duration,
                length=width,
                thumb=thumbnail,
                progress=progress_for_pyrogram,
                progress_args=(
                    "Uploading to Telegram...",
                    update.message,
                    upload_start_time
                    # progress_type="upload" is default
                )
            )
            file_type_for_log = "VIDEO_NOTE"
        
        # ✅ Forward to log channel
        await send_upload_log(bot, update, downloaded_file, file_type_for_log, youtube_dl_url, sent_msg)
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        await update.message.edit_caption(
            caption=f"**❌ Upload Failed**\n{str(e)[:200]}"
        )
        return False
    
    # ✅ Cleanup
    try:
        shutil.rmtree(tmp_directory_for_each_user)
        if 'thumbnail' in locals():
            try:
                os.remove(thumbnail)
            except:
                pass
        if 'thumb_image_path' in locals():
            try:
                os.remove(thumb_image_path)
            except:
                pass
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
    
    # ✅ Final message
    total_time = int(time.time() - simulated_start_time)
    upload_time = int(time.time() - upload_start_time)
    download_time = total_time - upload_time
    
    await update.message.edit_caption(
        caption=Translation.AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS.format(download_time, upload_time)
    )
    
    logger.info(f"✅ Success! Total: {total_time}s, Download: {download_time}s, Upload: {upload_time}s")
    
    # ✅ Remove JSON file
    try:
        os.remove(save_ytdl_json_path)
    except:
        pass
    
    return True