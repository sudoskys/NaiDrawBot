# -*- coding: utf-8 -*-
# @Time    : 2023/11/18 上午12:18
# @Author  : sudoskys
# @File    : __init__.py.py
# @Software: PyCharm
import asyncio
import re
import time

from loguru import logger
from telebot import types
from telebot import util, formatting
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
from telebot.formatting import escape_markdown
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

StepCache = StateMemoryStorage()


class StateReceiver(object):
    @staticmethod
    async def negative_prompt(bot: AsyncTeleBot, message: types.Message):
        logger.debug(f"{message.from_user.id}:Negative Prompt Received")
        await bot.delete_state(message.from_user.id, message.chat.id)
        _state = StateResign(uid=message.from_user.id, chat_id=message.chat.id)
        _parent = await _state.get_state()
        if _parent:
            _sketch = Sketch().parse_obj(_parent.sketch)
            # 截取负面回复为 1000 字符
            _sketch.negative_prompt = message.text[:1000]
        else:
            return None
        _message, _keyboard = await _sketch.start_keyboard()
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=_parent.origin_id,
            reply_markup=None
        )
        await bot.send_message(
            message.chat.id,
            text=_message,
            reply_markup=_keyboard,
            parse_mode="MarkdownV2"
        )
        await _state.finish()
        return None

    @staticmethod
    async def init_image_file(bot: AsyncTeleBot, message: types.Message):
        logger.debug(f"{message.from_user.id}:Init Image File Received")
        await bot.delete_state(message.from_user.id, message.chat.id)
        _state = StateResign(uid=message.from_user.id, chat_id=message.chat.id)
        _parent = await _state.get_state()
        if _parent:
            _file_id, _file = await parse_photo(bot, message)
            _sketch = Sketch().parse_obj(_parent.sketch)
            _sketch.init_image_file = _file_id
        else:
            return None
        _message, _keyboard = await _sketch.start_keyboard()
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=_parent.origin_id,
            reply_markup=None
        )
        await bot.send_message(
            message.chat.id,
            text=_message,
            reply_markup=_keyboard,
            parse_mode="MarkdownV2",
            reply_to_message_id=message.message_id
        )
        await _state.finish()
        return None

    @staticmethod
    async def seed(bot: AsyncTeleBot, message: types.Message):
        def extract_numbers(text):
            numbers = re.findall(r'\d+', text)
            if numbers:
                return int(''.join(numbers))
            else:
                return None

        logger.debug(f"{message.from_user.id}:Seed Received")
        # wait
        _state = StateResign(uid=message.from_user.id, chat_id=message.chat.id)
        _parent = await _state.get_state()
        if not _parent:
            return None
        _sketch = Sketch().parse_obj(_parent.sketch)
        _seed = extract_numbers(message.text)
        if not _seed:
            return await bot.send_message(
                message.chat.id,
                text="Wrong Seed, Please Input Again",
                parse_mode="MarkdownV2"
            )
        _sketch.seed = _seed
        await bot.delete_state(message.from_user.id, message.chat.id)
        await _state.finish()
        _message, _keyboard = await _sketch.start_keyboard()
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=_parent.origin_id,
            reply_markup=None
        )
        await bot.send_message(
            message.chat.id,
            text=_message,
            reply_markup=_keyboard,
            parse_mode="MarkdownV2"
        )
        return None

    @staticmethod
    async def prompt(bot: AsyncTeleBot, message: types.Message):
        logger.debug(f"{message.from_user.id}:Prompt Received")
        # wait
        _state = StateResign(uid=message.from_user.id, chat_id=message.chat.id)
        _parent = await _state.get_state()
        if not _parent:
            return None
        _sketch = Sketch().parse_obj(_parent.sketch)
        if not message.text:
            return await bot.send_message(
                message.chat.id,
                text="NO, You should write something",
                parse_mode="MarkdownV2"
            )
        _sketch.prompt = message.text
        await bot.delete_state(message.from_user.id, message.chat.id)
        await _state.finish()
        _message, _keyboard = await _sketch.start_keyboard()
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=_parent.origin_id,
            reply_markup=None
        )
        await bot.send_message(
            message.chat.id,
            text=_message,
            reply_markup=_keyboard,
            parse_mode="MarkdownV2"
        )
        return None


class BotRunner(object):
    def __init__(self):
        pass

    def _bot_create(self):
        return AsyncTeleBot(TelegramBot.token, state_storage=StepCache)

    def run(self):
        logger.info("Bot Start")
        bot = self._bot_create()
        if TelegramBot.proxy:
            from telebot import asyncio_helper
            asyncio_helper.proxy = TelegramBot.proxy
            logger.info("Proxy tunnels are being used!")

        @bot.message_handler(commands='help', chat_types=['private', 'supergroup', 'group'])
        async def listen_help_command(message: types.Message):
            _message = await bot.reply_to(
                message,
                text=formatting.format_text(
                    formatting.mbold("🥕 Help"),
                    formatting.mitalic("Here are some commands you can use:"),
                    formatting.mbold("🥕 /help"),
                    formatting.mitalic("Displays this help message."),
                    formatting.mbold("🥕 /start"),
                    formatting.mitalic("Starts the bot."),
                    formatting.mbold("🥕 /bind"),
                    formatting.mitalic("Link your email address to earn credits."),
                    formatting.mbold("🥕 /draw"),
                    formatting.mitalic("Draw something and generate text. Can be used in a group chat."),
                    formatting.mbold("🥕 /gift"),
                    formatting.mitalic("Gift credits to another user."),
                    formatting.mbold("🥕 /stats"),
                    formatting.mitalic("Displays your stats."),
                    formatting.mbold("🥕 /check_in"),
                    formatting.mitalic("Check in to earn credits."),
                    formatting.mbold("🥕 /clear"),
                    formatting.mitalic("Clear the sketch cache."),
                    formatting.mbold("🧀 Using the bot"),
                    formatting.munderline("Send text or images to the bot."),
                    formatting.mitalic("You can also use the bot in any group chat."),
                    formatting.mitalic(
                        "If using the bot within a group, it will use the parameters from the last generation.")
                ),
                parse_mode="MarkdownV2"
            )

        @bot.message_handler(
            content_types=["photo"],
            chat_types=['group', 'supergroup']
        )
        async def listen_photo_with_draw(message: types.Message):
            """
            群组命令，转发消息
            :param message:
            :return:
            """
            if message.caption:
                if message.caption.startswith('/draw '):
                    return await listen_draw_command(message)

        @bot.message_handler(
            commands='draw',
            content_types=["text"],
            chat_types=['group', 'supergroup']
        )
        async def listen_draw_command(message: types.Message):
            """
            群组命令，draw something
            :param message:
            :return:
            """
            message_text = message.text if message.text else message.caption
            # 参数内容
            _, _share = parse_command(message_text)
            if not _share:
                return None  # 不响应
            logger.info(
                f"🍺 Group Draw {message.from_user.id}:{message.chat.id} --message:{message.id} --time:{int(time.time())}"
            )
            # 暂时没有对单图片的处理方法，所以把这条逻辑移到后面了。
            file_unique_id, file = await parse_photo(bot, message)
            _sketch_cache = await LastCache.read_data(message.from_user.id)
            if _sketch_cache:
                _sketch = Sketch(**_sketch_cache)
                _sketch.__dict__.update({"prompt": _share})
                if file_unique_id:
                    _sketch.__dict__.update({"init_image_file": file_unique_id})
                else:
                    _sketch.__dict__.update({"init_image_file": None})
            else:
                _sketch = Sketch(prompt=_share, init_image_file=file_unique_id)

            _action_key = await ShareCreate().create(
                {
                    "action": "generate",
                    "regen_seed": True,
                    "data": SketchAction().sketch_export(sketch=_sketch)
                }
            )
            try:
                _message = await _sketch.sub_keyboard(key=_action_key, message=Message.from_telegram(message))
            except Exception as e:
                logger.exception(e)
                return await bot.reply_to(message, f"🥕 Error happened...")
            if _message.photo:
                return await bot.send_document(
                    chat_id=message.chat.id,
                    reply_to_message_id=message.id,
                    document=_message.photo[0],
                    caption=_message.message,
                    # reply_markup=_message.keyboard, # 禁止导致混乱的键盘
                    parse_mode="MarkdownV2"
                )
            else:
                return await bot.reply_to(
                    message,
                    _message.message,
                    reply_markup=await open_new_chat(),
                    parse_mode="MarkdownV2"
                )

        @bot.message_handler(commands='about', chat_types=['private'])
        async def handle_private_msg(message):
            await bot.reply_to(message,
                               escape_markdown("""
                                       基于 https://github.com/TelechaBot/BaseBot MVC 框架支持快速开发
                                       """),
                               parse_mode='MarkdownV2')

        @bot.message_handler(commands='check_in', chat_types=['private', 'supergroup', 'group'])
        async def handle_check_in(message):
            from_user = await UserSystem.read(message.from_user.id)
            if from_user.open_id_app.uid:
                try:
                    _return_message = await OPEN_ID_APP.check_in(from_user.open_id_app.uid)
                    _message = _return_message.message
                    if _return_message.status == 200:
                        _message += f"\n✨ Credits +40"
                    _message += f"\n💫 {remaining_hours_until_tomorrow()} hours until the next check-in"
                except AuthError as e:
                    _message = f"Error: {e}"
                except Exception as e:
                    logger.error(e)
                    _message = "Error: Unknown"
                return await bot.reply_to(message,
                                          formatting.format_text(
                                              formatting.mbold(_message),
                                          ),
                                          parse_mode='MarkdownV2')
            else:
                return await bot.reply_to(message,
                                          formatting.format_text(
                                              formatting.mbold("Please bind your email first"),
                                          ),
                                          reply_markup=await open_new_chat(),
                                          parse_mode='MarkdownV2')

        @bot.message_handler(commands='stats', chat_types=['private', 'supergroup', 'group'])
        async def handle_stats(message):
            _error = ""
            from_user = await UserSystem.read(message.from_user.id)
            _message = [
                formatting.munderline("📝 Stats"),
                formatting.mbold(f"🍦 UserID: {from_user.uid}"),
                formatting.mbold(f"🍰 BindID: {from_user.open_id_app.uid}"),
                formatting.mbold(f"💫 Create At: {from_user.creart_time}"),
            ]
            _credit = [formatting.mbold(f"🍪 Gift Credits Remain: {from_user.gift}")]
            if from_user.open_id_app.uid:
                try:
                    _user_details = await OPEN_ID_APP.get_user_credit(from_user.open_id_app.uid)
                    _remain_bound = _user_details.user_credit
                except AuthError:
                    _remain_bound = 0
                    _error = "*Bound Credits Remain Auth Error,So its 0 temporarily"
                except Exception as e:
                    _remain_bound = 0
                    _error = "*Bound Credits Remain Error,So its 0 temporarily"
                    logger.error(e)
                _credit.extend([formatting.mbold(f"🍭 Bound Credits Remain: {_remain_bound}"),
                                formatting.mbold(f"🌟 Total Credits: {round(from_user.gift + _remain_bound, 2)}")])

            _message.extend(_credit)
            if not message.chat.type == "private":
                return await bot.reply_to(message,
                                          text=formatting.format_text(*_credit),
                                          reply_markup=await open_new_chat(),
                                          parse_mode='MarkdownV2'
                                          )
            _message.extend(
                [formatting.mbold("\n🌊Help"),
                 formatting.mitalic(
                     "The available points are the sum of the gifted points and the bound points, which can be increased by checking in on the bound platform. The gifting function will transfer points from the bound platform to the recipient's gift points."
                 ),
                 escape_markdown(_error)]
            )
            return await bot.reply_to(message,
                                      text=formatting.format_text(*_message),
                                      parse_mode='MarkdownV2')

        # 私聊事件处理
        @bot.message_handler(commands='start', chat_types=['private'])
        async def start_command_handler(message: types.Message):
            # 分享参数内容
            _, _share = parse_command(message.text)
            if not _share:
                logger.debug(f"WelCome {message.from_user.id}")
                # Welcome Message
                await bot.send_photo(message.chat.id,
                                     photo="https://pbs.twimg.com/profile_banners/1425515835741786120/1630416858/1080x360",
                                     caption=formatting.format_text(
                                         formatting.mbold(f"Hello {message.from_user.first_name}."),
                                         formatting.mbold("👋 Here's a generative AI hosting platform for you."),
                                         formatting.mbold(
                                             "\nJust post your prompt (which can be accompanied by a picture) and you're good to go. 👇"),
                                         formatting.mbold("\nWant to get to the point?"),
                                         formatting.mitalic(
                                             "If you sign in with your email address, you can earn points every day."),
                                         formatting.munderline("\nCheck /help for more information."),
                                         separator="\n"),
                                     reply_markup=await bind_keyboard(),
                                     parse_mode="MarkdownV2"
                                     )
            else:
                if not await pass_user(message.from_user.id):
                    return await bot.reply_to(message, "🥕 For some reason....You are not allowed to use this bot?")
                # 校验数据,调用面板
                logger.debug(f"{message.from_user.id}:Share {_share}")
                _message = await Sketch.sub_keyboard(key=_share, message=Message.from_telegram(message))
                await bot.send_message(chat_id=message.chat.id, text=_message.message,
                                       reply_markup=_message.keyboard,
                                       parse_mode="MarkdownV2")

        async def bind_keyboard():
            return InlineKeyboardMarkup(
                keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔗 Bind Email",
                            url=await OPEN_ID_APP.login()
                        )
                    ]
                ]
            )

        async def open_new_chat():
            return InlineKeyboardMarkup(
                keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🍪 PM Me",
                            url=TelegramBot.link
                        )
                    ]
                ]
            )

        @bot.message_handler(commands='bind', chat_types=['private', 'group', 'supergroup'])
        async def bind_command_handler(message: types.Message):
            # 分享参数内容
            _, _token = parse_command(message.text)
            if not message.chat.type == "private":
                return await bot.reply_to(message,
                                          text="🧊 Please Send This Command In Private And Not Share your Token Here",
                                          reply_markup=await open_new_chat(),
                                          )
            if not _token:
                return await bot.reply_to(message,
                                          text="🧊 Please Generate A Token First",
                                          reply_markup=await bind_keyboard(),
                                          )
            the_user = await UserSystem.read(message.from_user.id)
            if await BindCache.read_data(message.from_user.id):
                return await bot.reply_to(message, "Baby! You are too fast!")
            await SinkConfigCache.set_data(message.from_user.id, _token, timeout=10)
            # 校验数据,更新用户数据库
            try:
                _user_profile = await OPEN_ID_APP.verify_token(_token)
            except AuthError as e:
                return await bot.reply_to(message, f"🧊 Binding Failed,Token Verification Failed {e}")
            except Exception as e:
                return await bot.reply_to(message, "🧊 Binding Failed,Token Verification Failed")
            else:
                the_user.open_id_app.uid = _user_profile.id
                the_user.open_id_app.role = _user_profile.role
                the_user.open_id_app.email = _user_profile.email
                the_user.open_id_app.token = _token
                await UserSystem.save(the_user)
                await bot.reply_to(message,
                                   formatting.format_text(formatting.mbold(f"🍺 Binding Success,{_user_profile.id}."),
                                                          formatting.munderline(
                                                              f"If you are a new user, please check your email for active your account."),
                                                          separator="\n"),
                                   parse_mode="MarkdownV2"
                                   )

        @bot.message_handler(commands='clear', chat_types=['private', 'group', 'supergroup'])
        async def handle_clear(message: types.Message):
            _sketch_cache = await LastCache.set_data(message.from_user.id, {})
            return await bot.reply_to(message, "🧀 Clear Success")

        @bot.message_handler(content_types=['text', 'photo', 'sticker'], chat_types=['private'])
        async def handle_banner(message: types.Message):
            if not await pass_user(message.from_user.id):
                return await bot.reply_to(message, "🥣 For some reason....You are not allowed to use this bot.")
            # 获取用户输入
            _prompt = message.text if message.text else message.caption
            # 如果配置了 Blip ，则启用 Blip
            # 但是没有 Blip
            _state = await bot.get_state(user_id=message.from_user.id, chat_id=message.chat.id)
            logger.debug(f"{message.from_user.id}:State Result {_state}")
            if _state:
                try:
                    _func = getattr(StateReceiver, _state)
                    await _func(bot, message)
                except Exception as e:
                    logger.exception(e)
                finally:
                    await bot.delete_state(user_id=message.from_user.id, chat_id=message.chat.id)
                    return None

            if not _prompt:
                return

            # 暂时没有对单图片的处理方法，所以把这条逻辑移到后面了。
            file_unique_id, file = await parse_photo(bot, message)
            # 创建
            logger.info(f"🍺 Draw Order Create {message.from_user.id}:{message.chat.id} --prompt:{_prompt[:50]}")
            try:
                await generate_sketch(message, prompt=_prompt, init_image_file_id=file_unique_id)
            except Exception as e:
                logger.exception(e)

        async def generate_sketch(message: types.Message, prompt: str, init_image_file_id: str = None):
            # 创建
            _sketch_cache = await LastCache.read_data(message.from_user.id)
            if _sketch_cache:
                _sketch = Sketch(**_sketch_cache)
                _sketch.__dict__.update({"prompt": prompt})
                # 指定驱动器
                _sketch.__dict__.update({"driver_name": "HOLA_AI"})
                if init_image_file_id:
                    _sketch.__dict__.update({"init_image_file": init_image_file_id})
            else:
                _sketch = Sketch(init_image_file=init_image_file_id, prompt=prompt)

            _message, _keyboard = await _sketch.start_keyboard()
            await bot.send_message(
                message.chat.id,
                text=_message,
                reply_markup=_keyboard,
                parse_mode="MarkdownV2"
            )

        @bot.callback_query_handler(func=None, model_setting_config=root_keyboard.filter())
        async def keyboard_action_handler(call: types.CallbackQuery):
            callback_data: dict = root_keyboard.parse(callback_data=call.data)
            if not await pass_user(call.from_user.id):
                return await bot.answer_callback_query(call.id, text="You are not allowed to use this bot.")
            try:
                _message = await Sketch.sub_keyboard(
                    key=callback_data.get("data"),
                    message=Message.from_telegram(call)
                )
                if _message.resolve:
                    await bot.answer_callback_query(call.id)
                    logger.debug(_message.message)
                    await bot.send_message(
                        call.message.chat.id,
                        text=_message.message,
                        reply_markup=_message.keyboard,
                        parse_mode="MarkdownV2"
                    )
                    _message = await Sketch.sub_keyboard(
                        key=_message.resolve,
                        message=Message.from_telegram(call)
                    )
            except Exception as e:
                logger.exception(e)
                return
            logger.debug(_message.message)
            await bot.answer_callback_query(call.id)
            if _message.state and _message.raw:
                logger.debug(f"{call.from_user.id}:Resign State {call.message.id} {call.message.chat.id}")
                logger.debug(_message.state)
                await StateResign(uid=call.from_user.id, chat_id=call.message.chat.id).resign(
                    state=StateResign.StateData(
                        origin_id=call.message.id,
                        sketch=_message.raw,
                        call_func_name=_message.state,
                    )
                )
                await bot.set_state(
                    user_id=call.from_user.id,
                    chat_id=call.message.chat.id,
                    state=_message.state
                )
            if _message.finish_state:
                await StateResign(uid=call.from_user.id, chat_id=call.message.chat.id).finish()
                await bot.delete_state(user_id=call.from_user.id, chat_id=call.message.chat.id)
                logger.debug(f"Finish State:{call.from_user.id} {call.message.chat.id}")
            if _message.edit:
                if _message.warn:
                    # 警告通知点
                    await __warn(_message.warn)
                await bot.edit_message_text(
                    text=_message.message,
                    chat_id=call.message.chat.id,
                    message_id=call.message.id,
                    reply_markup=_message.keyboard,
                    parse_mode="MarkdownV2"
                )
            else:
                if _message.photo:
                    await bot.send_document(
                        chat_id=call.message.chat.id,
                        document=_message.photo[0],
                        caption=_message.message,
                        reply_markup=_message.keyboard,
                        parse_mode="MarkdownV2"
                    )
                else:
                    await bot.send_message(
                        chat_id=call.message.chat.id,
                        text=_message.message,
                        reply_markup=_message.keyboard,
                        parse_mode="MarkdownV2",
                    )

        async def pass_user(uid: int):
            # 预先初始化用户对象
            the_user = await UserSystem.read(uid)
            if not the_user.public_access:
                return None
            else:
                return True

        # 是否是管理员
        async def is_admin(message: types.Message):
            _got = await bot.get_chat_member(message.chat.id, message.from_user.id)
            return _got.status in ['administrator', 'creator']

        async def __warn(info):
            if not TelegramBot.warn_channel:
                logger.error(f"#Warn {info}")
            try:
                await bot.send_message(
                    chat_id=TelegramBot.warn_channel,
                    text=info
                )
            except Exception as e:
                logger.error(e)

        @bot.message_handler(
            commands='gift',
            content_types=['text'],
            chat_types=['group', 'supergroup']
        )
        async def listen_gift_command(message: types.Message):
            """
            gift something to someone
            :param message:
            :return:
            """
            # 分享参数内容
            _, _share = parse_command(message.text)
            if not _share:
                return await bot.reply_to(message, text=formatting.mbold(f"🥕 Well,who you want to gift?"),
                                          parse_mode="MarkdownV2"
                                          )
            if not message.reply_to_message:
                return await bot.reply_to(message, text=formatting.mbold(f"🥕 Please reply to a user you want to gift."),
                                          parse_mode="MarkdownV2"
                                          )
            if message.reply_to_message.from_user.is_bot:
                return await bot.reply_to(message, f"🥕 Well, you cant gift to a bot....")
            _from_user = message.from_user
            _to_user = message.reply_to_message.from_user
            try:
                _gift = int(str(_share).strip())
            except Exception:
                return await bot.reply_to(message, f"🥕 Please input a number...")
            if _gift <= 0:
                return await bot.reply_to(
                    message,
                    text=formatting.format_text(
                        formatting.mbold(
                            f"🔖 {_from_user.full_name} want to gift {_to_user.full_name} {_gift} gift credits."),
                        formatting.munderline("but you cant do this...")),
                    parse_mode="MarkdownV2"
                )
            from_user = await UserSystem.read(message.from_user.id)
            to_user = await UserSystem.read(message.reply_to_message.from_user.id)
            if not from_user.open_id_app.uid:
                return await bot.reply_to(message, f"🥕 Baby,Please bind your email first...",
                                          reply_markup=await open_new_chat())
            try:
                await OPEN_ID_APP.charge_user(
                    user_id=from_user.open_id_app.uid,
                    credit=_gift
                )
            except AuthError as e:
                return await bot.reply_to(
                    message,
                    text=f"🔖 {_from_user.full_name} tried to give {_to_user.full_name} {_gift} points, but failed, because {e}... may you havent bind your email? "
                )
            except Exception as e:
                logger.error(f"Gift Failed:{e}")
                return await bot.reply_to(
                    message,
                    text=f"🔖 {_from_user.full_name} tried to give {_to_user.full_name} {_gift} points, but failed, because server system boom!"
                )
            else:
                logger.info(f"Gift Success:{_from_user.id} -> {_to_user.id} {_gift}")
                to_user.gift += _gift
                await UserSystem.save(to_user)
                if _to_user.is_premium:
                    _reply = formatting.format_text(
                        formatting.mbold(
                            f"🔖 {_from_user.full_name} gift {_to_user.full_name}(premium.ver) {_gift} gift credits!"),
                    )
                else:
                    _reply = formatting.format_text(
                        formatting.mbold(
                            f"🔖 {_from_user.full_name} gift {_to_user.full_name} {_gift} gift credits!"),
                        formatting.mbold(f"@{_to_user.username}" if _to_user.username else f""),
                    )
                return await bot.reply_to(
                    message,
                    text=_reply,
                    parse_mode="MarkdownV2"
                )

        from telebot import asyncio_filters
        bot.add_custom_filter(asyncio_filters.IsAdminFilter(bot))
        bot.add_custom_filter(asyncio_filters.ChatFilter())
        bot.add_custom_filter(asyncio_filters.StateFilter(bot))
        bind_filters(bot)

        async def main():
            await asyncio.gather(
                bot.polling(non_stop=True, allowed_updates=util.update_types, skip_pending=True)
            )

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
