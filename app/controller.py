# -*- coding: utf-8 -*-
# @Time    : 2023/11/18 上午12:18
# @Author  : sudoskys
# @File    : controller.py
# @Software: PyCharm
import asyncio
import time
from io import BytesIO

import shortuuid
from loguru import logger
from pydantic import ValidationError
from telebot import types
from telebot import util, formatting
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage

from .command import DrawCommand
from .core import NovelAiInference, ServerError, NaiResult
from .schema import BotSetting, AwsSetting
from .utils import parse_command

StepCache = StateMemoryStorage()

from asgiref.sync import sync_to_async


@sync_to_async
def upload_to_aws(
        file_bytes: BytesIO,
        message_date: int,
        params: NaiResult.RequestParams
):
    import boto3
    from botocore.exceptions import ClientError
    s3_client = boto3.client('s3',
                             aws_access_key_id=AwsSetting.aws_access_key_id,
                             aws_secret_access_key=AwsSetting.aws_secret_access_key
                             )
    try:
        file_uid = shortuuid.uuid()[:2]
        today = time.strftime('%Y-%m-%d', time.localtime(time.time()))
        s3_client.upload_fileobj(
            file_bytes,
            AwsSetting.aws_bucket_name,
            f"telegram/{today}/nai_tg_{file_uid}_{message_date}.webp"
        )
        # 上传请求参数
        s3_client.put_object(
            Body=params.model_dump_json(),
            Bucket=AwsSetting.aws_bucket_name,
            Key=f"telegram/{today}/nai_tg_{file_uid}_{message_date}.json"
        )
    except ClientError as e:
        logger.exception(f"🍺 Upload to S3 error: {e}")
        return None
    else:
        logger.info(f"🍺 Upload to S3 --file_uid {file_uid}")
        return True


class BotRunner(object):
    def __init__(self):
        self.bot = AsyncTeleBot(BotSetting.token, state_storage=StepCache)

    def run(self):
        logger.info("Bot Start")
        bot = self.bot
        if BotSetting.proxy_address:
            from telebot import asyncio_helper
            asyncio_helper.proxy = BotSetting.proxy_address
            logger.info("Proxy tunnels are being used!")

        @bot.message_handler(commands='help', chat_types=['private', 'supergroup', 'group'])
        async def listen_help_command(message: types.Message):
            _message = await bot.reply_to(
                message,
                text=formatting.format_text(
                    formatting.mbold("🥕 Help"),
                    formatting.mitalic("draw [prompt] [-neg negative_prompt] [-s seed] [-st steps] "
                                       "[-cfg cfg_rescale] [-sam sampler] [-wi width] [-he height]"
                                       ),
                    formatting.mbold("🥕 /draw"),
                    formatting.mitalic("Draw something and generate text. Can be used in a group chat."),
                    formatting.mitalic(
                        "If using the bot within a group, it will use the parameters from the last generation.")
                ),
                parse_mode="MarkdownV2"
            )

        @bot.message_handler(
            commands='draw',
            content_types=["text"],
            chat_types=['group', 'supergroup', 'private']
        )
        async def listen_draw_command(message: types.Message):
            """
            群组命令，draw something
            :param message:
            :return:
            """
            message_text = message.text if message.text else message.caption
            # 参数内容
            head, body = parse_command(message_text)
            if not body:
                return await bot.reply_to(
                    message,
                    "🥕 Input something to draw\n"
                    + DrawCommand.get_help(),
                )
            if body.find(" -") != -1:
                # 将 - 之前的内容用括号包裹
                flag = body[body.find(" -"):]
                body = body[:body.find(" -")]
                body = f"'{body}'{flag}"
                message_text = f"/draw {body}"
            parsed = DrawCommand.parse(message_text)
            if not parsed.matched:
                return await bot.reply_to(
                    message,
                    parsed.error_info
                )
            logger.info(
                f"🍺 Group {message.from_user.id}:{message.chat.id} "
                f"--message:{message.id} --time:{int(time.time())}"
            )
            try:
                infer = NovelAiInference(**parsed.all_matched_args)
                result = await infer()
            except ValidationError as e:
                logger.error(e)
                return await bot.reply_to(message, f"🥕 Invalid parameters...")
            except ServerError as e:
                logger.exception(e)
                return await bot.reply_to(message, e.msg)
            except Exception as e:
                logger.exception(e)
                return await bot.reply_to(message, f"🥕 Error happened...")
            if result.files:
                for file in result.files:
                    await bot.send_document(
                        chat_id=message.chat.id,
                        document=file,
                        caption=parsed.query("prompt"),
                        reply_to_message_id=message.message_id
                    )
                    if AwsSetting.available:
                        await upload_to_aws(
                            file_bytes=BytesIO(file[1]),
                            message_date=message.date,
                            params=infer.parameters
                        )
                return None
            else:
                return await bot.reply_to(
                    message,
                    "🥕 No result"
                )

        async def main():
            await asyncio.gather(
                bot.polling(non_stop=True, allowed_updates=util.update_types, skip_pending=True)
            )

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
