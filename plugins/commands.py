import os, re, json, base64, logging, random, asyncio
from Script import script
from database.users_chats_db import db
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.ia_filterdb import Media, get_file_details, unpack_new_file_id
from info import CHANNELS, ADMINS, AUTH_CHANNEL, LOG_CHANNEL, PICS, BATCH_FILE_CAPTION, CUSTOM_FILE_CAPTION, PROTECT_CONTENT, START_MESSAGE, FORCE_SUB_TEXT, SUPPORT_CHAT
from utils import get_settings, get_size, is_subscribed, save_group_settings, temp
from database.connections_mdb import active_connection

logger = logging.getLogger(__name__)
BATCH_FILES = {}

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        buttons = [[           
            InlineKeyboardButton('📢 Updates 📢', url=f'https://t.me/{SUPPORT_CHAT}')
            ],[ 
            InlineKeyboardButton('ℹ️ Help ℹ️', url=f"https://t.me/{temp.U_NAME}?start=help")
        ]]
        await message.reply(START_MESSAGE.format(user=message.from_user.mention if message.from_user else message.chat.title, bot=client.mention), reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)                    
        await asyncio.sleep(2) 
        if not await db.get_chat(message.chat.id):
            total = await client.get_chat_members_count(message.chat.id)
            await client.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(a=message.chat.title, b=message.chat.id, c=message.chat.username, d=total, f=client.mention, e="Unknown"))       
            await db.add_chat(message.chat.id, message.chat.title, message.chat.username)
        return 
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention, message.from_user.username, temp.U_NAME))
    if len(message.command) != 2:
        buttons = [[
            InlineKeyboardButton("➕️ Add Me To Your Chat ➕", url=f"http://t.me/{temp.U_NAME}?startgroup=true")
            ],[ 
            InlineKeyboardButton("Search 🔎", switch_inline_query_current_chat=''), 
            InlineKeyboardButton("Channel 🔈", url="https://t.me/mkn_bots_updates")
            ],[      
            InlineKeyboardButton("Help 🕸️", callback_data="help"),
            InlineKeyboardButton("About ✨", callback_data="about")
        ]]
        await message.reply_photo(photo=random.choice(PICS), caption=START_MESSAGE.format(user=message.from_user.mention, bot=client.mention), reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        return
        
    if AUTH_CHANNEL and not await is_subscribed(client, message):
        try:
            invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL))
        except ChatAdminRequired:
            logger.error("MAKE SURE BOT IS ADMIN IN FORCESUB CHANNEL")
            return
        btn = [[InlineKeyboardButton("Join My Channel ✨", url=invite_link.invite_link)]]
        if message.command[1] != "subscribe":
            try:
                kk, file_id = message.command[1].split("_", 1)
                pre = 'checksubp' if kk == 'filep' else 'checksub' 
                btn.append([InlineKeyboardButton("⟳ Try Again", callback_data=f"{pre}#{file_id}")])
            except (IndexError, ValueError):
                btn.append([InlineKeyboardButton("⟳ Try Again", url=f"https://t.me/{temp.U_NAME}?start={message.command[1]}")])
                
        try:
            return await client.send_message(chat_id=message.from_user.id, text=FORCE_SUB_TEXT, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.DEFAULT)
        except Exception as e:
            print(f"Force Sub Text Error\n{e}")
            return await client.send_message(chat_id=message.from_user.id, text=script.FORCE_SUB_TEXT, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.DEFAULT)
        
    if len(message.command) == 2 and message.command[1] in ["subscribe", "error", "okay", "help"]:
        buttons = [[
            InlineKeyboardButton("➕️ Add Me To Your Chat ➕", url=f"http://t.me/{temp.U_NAME}?startgroup=true")
            ],[ 
            InlineKeyboardButton("Search 🔎", switch_inline_query_current_chat=''), 
            InlineKeyboardButton("Channel 🔈", url="https://t.me/mkn_bots_updates")
            ],[      
            InlineKeyboardButton("Help 🕸️", callback_data="help"),
            InlineKeyboardButton("About ✨", callback_data="about")
        ]]
        await message.reply_photo(photo=random.choice(PICS), caption=START_MESSAGE.format(user=message.from_user.mention, bot=client.mention), reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
        return
        
    data = message.command[1]
    try:
        pre, file_id = data.split('_', 1)
    except:
        file_id = data
        pre = ""
        
    if data.split("-", 1)[0] == "BATCH":
        sts = await message.reply("PLEASE WAIT......")
        file_id = data.split("-", 1)[1]
        msgs = BATCH_FILES.get(file_id)
        if not msgs:
            file = await client.download_media(file_id)
            try: 
                with open(file) as file_data:
                    msgs=json.loads(file_data.read())
            except:
                await sts.edit("FAILED")
                return await client.send_message(LOG_CHANNEL, "UNABLE TO OPEN FILE.")
            os.remove(file)
            BATCH_FILES[file_id] = msgs
        for msg in msgs:
            title = msg.get("title")
            size=get_size(int(msg.get("size", 0)))
            f_caption=msg.get("caption", "")
            if BATCH_FILE_CAPTION:
                try:
                    f_caption=BATCH_FILE_CAPTION.format(mention=message.from_user.mention, file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                except Exception as e:
                    logger.exception(e)
                    f_caption=f_caption
            if f_caption is None:
                f_caption = f"{title}"
            try:
                await client.send_cached_media(chat_id=message.from_user.id, file_id=msg.get("file_id"), caption=f_caption, protect_content=msg.get('protect', False))
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await client.send_cached_media(chat_id=message.from_user.id, file_id=msg.get("file_id"), caption=f_caption, protect_content=msg.get('protect', False))
            except Exception as e:
                logger.warning(e, exc_info=True)
                continue
            await asyncio.sleep(1) 
        return await sts.delete()
        
    elif data.split("-", 1)[0] == "DSTORE":
        sts = await message.reply("PLEASE WAIT....")
        b_string = data.split("-", 1)[1]
        decoded = (base64.urlsafe_b64decode(b_string + "=" * (-len(b_string) % 4))).decode("ascii")
        try:
            f_msg_id, l_msg_id, f_chat_id, protect = decoded.split("_", 3)
        except:
            f_msg_id, l_msg_id, f_chat_id = decoded.split("_", 2)
            protect = "/pbatch" if PROTECT_CONTENT else "batch"
        diff = int(l_msg_id) - int(f_msg_id)
        async for msg in client.iter_messages(int(f_chat_id), int(l_msg_id), int(f_msg_id)):
            if msg.media:
                media = getattr(msg, msg.media)
                if BATCH_FILE_CAPTION:
                    try:
                        f_caption=BATCH_FILE_CAPTION.format(mention=message.from_user.mention, file_name=getattr(media, 'file_name', ''), file_size=getattr(media, 'file_size', ''), file_caption=getattr(msg, 'caption', ''))
                    except Exception as e:
                        logger.exception(e)
                        f_caption = getattr(msg, 'caption', '')
                else:
                    media = getattr(msg, msg.media)
                    file_name = getattr(media, 'file_name', '')
                    f_caption = getattr(msg, 'caption', file_name)
                try:
                    await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False)
                except Exception as e:
                    logger.exception(e)
                    continue
            elif msg.empty:
                continue
            else:
                try:
                    await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except Exception as e:
                    logger.exception(e)
                    continue
        return await sts.delete()


@Client.on_message(filters.command("help"))
async def help(client, message):
    buttons = [
        [InlineKeyboardButton("➕️ Add Me To Your Chat ➕", url=f"http://t.me/{temp.U_NAME}?startgroup=true")],
        [InlineKeyboardButton("Search 🔎", switch_inline_query_current_chat=''), InlineKeyboardButton("Channel 🔈", url="https://t.me/mkn_bots_updates")],
        [InlineKeyboardButton("Help 🕸️", callback_data="help"), InlineKeyboardButton("About ✨", callback_data="about")]
    ]
    await message.reply_photo(photo=random.choice(PICS), caption="How can I assist you today?", reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.HTML)
