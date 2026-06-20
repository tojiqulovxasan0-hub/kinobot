from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
import database as db


class UserRegisterMiddleware(BaseMiddleware):
    """Har bir xabar/callback kelganda foydalanuvchini ro'yxatdan o'tkazadi"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None

        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user and not user.is_bot:
            await db.add_user(
                user_id=user.id,
                username=user.username or "",
                full_name=user.full_name or ""
            )
            await db.update_daily_visit(user.id)

        return await handler(event, data)
