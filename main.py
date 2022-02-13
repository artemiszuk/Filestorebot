import os
import logging
import asyncio
import subprocess
from utils import str_to_b64, b64_to_str, retrieve
from pyrogram import Client, filters, errors, idle, errors
from pyrogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
bot_token = os.environ.get("BOT_TOKEN")
#p = subprocess.Popen(["python3", "-m", "http.server"])

app = Client(":memory:", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOGGER = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


class Var(object):
    AUTH_USERS = os.environ.get("AUTH_USERS").split()
    log_c = int(os.environ.get("LOG_CHANNEL"))
    doing_batch = dict()
    batch_list = dict()

class Messages:
    startm = "**📌MAIN MENU**\n\nHi ! This is File Share Bot \n\n__Click Help for how to use__"
    helpm = "**📌HELP MENU**\n\nTo Share Files Seperately just send them here directly. \n\nTo Share as a Batch send /batch, then send multiple files, after you are done, use /getlink to get the link of the Batch You Created"


@app.on_callback_query()
async def button(client, cmd: CallbackQuery):
    cb_data = cmd.data
    if "help" in cb_data:
        await cmd.message.edit(
            Messages.helpm,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Back ◀", callback_data="start")]]
            ),
        )
    elif "start" in cb_data:
        await cmd.message.edit(
            Messages.startm,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Help ❓", callback_data="help"),
                        InlineKeyboardButton("Close ❌", callback_data="close"),
                    ]
                ]
            ),
        )
    elif "close" in cb_data:
        await cmd.message.delete()
        await cmd.message.reply_to_message.delete()

class CustomFilters:
    auth_users = filters.create(
        lambda _, __, message: str(message.from_user.id) in Var.AUTH_USERS
    )


@app.on_message(filters.command(["start"]) & filters.private)
async def start(client, message):
    if "_" not in message.text and str(message.from_user.id) in Var.AUTH_USERS:
        await message.reply(
            Messages.startm,
            reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("Help ❓", callback_data="help"),
                            InlineKeyboardButton("Close ❌", callback_data="close")
                        ]
                    ]
                ),
            quote=True
        )
    elif "_" in message.text and "batch" in message.text:
        encoded_string = message.text.split("_")[-1]
        print("Batch")
        msg_id = int(b64_to_str(encoded_string))
        msg = await app.get_messages(Var.log_c, msg_id)
        msg_list = msg.text.split()
        print(msg_list)
        for i in msg_list:
            to_send = await app.get_messages(Var.log_c,int(i))
            sent_to_user = await to_send.copy(message.from_user.id)
            await asyncio.sleep(0.3)
        await msg.reply(
            f" Batch Retrieval Requested By : {message.from_user.mention()}"
        )
        share_link = await retrieve(app, Var.log_c, encoded_string, "batch")

        await message.reply(
            f"Here is the Share Link for this Batch \n\n{share_link}", quote=True
        )

    elif "_" in message.text:
        encoded_string = message.text.split("_")[-1]
        msg_id = int(b64_to_str(encoded_string))

        msg_to_send = await app.get_messages(Var.log_c, msg_id)
        type = msg_to_send.media
        await msg_to_send.reply(
            f"Retrieval Requested By : {message.from_user.mention()}"
        )

        sent = await msg_to_send.copy(message.from_user.id)
        share_link = await retrieve(app, Var.log_c, encoded_string, type)

        await sent.reply(
            f"Here is the Share Link for this {type}\n\n{share_link}", quote=True
        )

@app.on_message(filters.command(["getlink"]) & filters.private & CustomFilters.auth_users)
async def return_link(client,message):
    user_id = message.from_user.id
    if (user_id not in Var.doing_batch or Var.doing_batch[user_id] == False):
        return await message.reply(
            "Can Only be used after starting batch Creation!\nRead Help For more"
        )
    if (len(Var.batch_list[user_id]) == 0):
        return await message.reply(
            "Creating Batch Cancelled"
        )
        Var.doing_batch[user_id] = False
        Var.batch_list[user_id] = ""
    elif Var.doing_batch[user_id]:
        sent = await app.send_message(Var.log_c,Var.batch_list[user_id])
        type = "batch"
        await sent.reply(f"Share {type} Requested by {message.from_user.mention()}")
        encode_string = str_to_b64(str(sent.message_id))
        share_link = await retrieve(app, Var.log_c, encode_string, type)
        print(share_link)
        await message.reply(
            f"Here is the Share Link for this {type}\n\n{share_link}", quote=True
        )
        Var.doing_batch[user_id] = False
        Var.batch_list[user_id] = ""
        

@app.on_message(filters.command(["batch"]) & filters.private & CustomFilters.auth_users)
async def batch_handler(client, message):
    user_id = message.from_user.id
    Var.doing_batch[user_id] = True
    Var.batch_list[user_id] = ""
    await message.reply("Start Sending Files Now \nSend /getlink after you are done\n\nDo Not send large amount of files in bulk or bot may crash!")

@app.on_message(
    (
        filters.photo
        | filters.audio
        | filters.video
        | filters.document
        | filters.animation
    )
    & CustomFilters.auth_users
    & filters.private
)
async def forwarder(client, message):
    user_id = message.from_user.id
    type = message.media
    if user_id in Var.doing_batch and Var.doing_batch[user_id]:
        sent = await message.copy(Var.log_c)
        Var.batch_list[user_id] += str(sent.message_id) + " "
        print(Var.batch_list[user_id])
        return
    print(type)
    sent = await message.copy(Var.log_c)
    await sent.reply(f"Share {type} Requested by {message.from_user.mention()}")
    encode_string = str_to_b64(str(sent.message_id))
    share_link = await retrieve(app, Var.log_c, encode_string, type)
    print(share_link)
    await message.reply(
        f"Here is the Share Link for this {type}\n\n{share_link}", quote=True
    )


print("Starting Bot..")
app.run()
