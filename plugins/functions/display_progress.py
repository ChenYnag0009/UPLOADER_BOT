import math
import time
import logging
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from plugins.script import Translation
from pyrogram import enums

# បង្កើត logger
logger = logging.getLogger(__name__)

async def progress_for_pyrogram(current, total, ud_type, message, start, progress_type="upload"):
    now = time.time()
    diff = now - start
    
    # ✅ ការពារការចែកដោយសូន្យ
    if diff <= 0:
        return
    
    # ✅ Set different update intervals for different progress types
    if progress_type == "download":
        update_interval = 2.0  # Update every 2 seconds for download
    elif progress_type == "simulated":
        update_interval = 0.5  # Update every 0.5 seconds for simulated (faster)
    else:  # upload
        update_interval = 5.0  # Update every 5 seconds for upload
    
    if round(diff % update_interval) == 0 or current == total:
        percentage = current * 100 / total if total > 0 else 0
        speed = current / diff if diff > 0 else 0
        
        # ✅ LOG តម្លៃសម្រាប់ debug
        logger.debug(f"[PROGRESS_{progress_type.upper()}] "
                    f"Current: {current}, Total: {total}, "
                    f"Percentage: {percentage:.2f}%, "
                    f"Speed: {speed:.2f} B/s, "
                    f"Time elapsed: {diff:.2f}s")
        
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time_str = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time_str = TimeFormatter(milliseconds=estimated_total_time)

        # ✅ Create progress bar with better visualization
        filled_blocks = math.floor(percentage / 10)
        empty_blocks = 10 - filled_blocks
        
        progress = "┏━━━━✦[{0}{1}]✦━━━━".format(
            ''.join(["▣" for i in range(filled_blocks)]),
            ''.join(["▢" for i in range(empty_blocks)])
        )

        # ✅ កំណត់ស្ថានភាពផ្សេងគ្នាសម្រាប់ប្រភេទផ្សេងគ្នា
        if progress_type == "download":
            status_text = "**📥 Downloading from YouTube...**\n"
            log_prefix = "📥 DOWNLOAD"
        elif progress_type == "simulated":
            status_text = "**🔄 Preparing download...**\n"
            log_prefix = "🔄 SIMULATED"
        else:  # upload
            status_text = "**📤 Uploading to Telegram...**\n"
            log_prefix = "📤 UPLOAD"
        
        # ✅ LOG ព័ត៌មានសំខាន់ៗ
        logger.info(f"{log_prefix} PROGRESS: {percentage:.1f}% | "
                   f"{humanbytes(current)}/{humanbytes(total)} | "
                   f"Speed: {humanbytes(speed)}/s")

        # ✅ Use the format from Translation
        progress_text = progress + Translation.PROGRESS.format(
            round(percentage, 2),
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time_str if estimated_total_time_str != '' else "0 s"
        )
        
        # ✅ Combine status text and progress
        full_text = status_text + Translation.PROGRES.format(ud_type, progress_text)
        
        try:
            await message.edit(
                text=full_text,
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton('⛔ Cancel', callback_data=f"cancel_download+{message.id}")
                        ]
                    ]
                )
            )
            logger.debug(f"✅ Successfully updated {progress_type} progress to {percentage:.1f}%")
        except Exception as e:
            # Handle specific errors
            if "MESSAGE_NOT_MODIFIED" in str(e):
                logger.debug(f"Message not modified for {progress_type} at {percentage:.1f}%")
            else:
                logger.error(f"Failed to edit message for {progress_type}: {e}")
            pass

def humanbytes(size):
    if not size:
        return "0 B"
    power = 2 ** 10
    n = 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    result = ""
    if days > 0:
        result += f"{days}d "
    if hours > 0:
        result += f"{hours}h "
    if minutes > 0:
        result += f"{minutes}m "
    if seconds > 0:
        result += f"{seconds}s "
    if milliseconds > 0 and not result:
        result += f"{milliseconds}ms"
    
    return result.strip() or "0s"