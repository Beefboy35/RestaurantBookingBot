from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from app.DAO.database import async_session_maker


class BaseDatabaseMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        async with async_session_maker() as session:
            self.set_session(data, session)
            try:
                result = await handler(event, data)
                await self.after_handler(session)
                return result
            except Exception as e:
                await session.rollback()
                raise e
            finally:
                await session.close()

    def set_session(self, data: Dict[str, Any], session) -> None:
        """Method for setting a session in the data dictionary."""
        raise NotImplementedError("Этот метод должен быть реализован в подклассах.")

    async def after_handler(self, session) -> None:
        """Method for additional actions after the handler is called (e.g, commit)."""
        pass


class DatabaseMiddlewareWithoutCommit(BaseDatabaseMiddleware):
    def set_session(self, data: Dict[str, Any], session) -> None:
        data['session_without_commit'] = session


class DatabaseMiddlewareWithCommit(BaseDatabaseMiddleware):
    def set_session(self, data: Dict[str, Any], session) -> None:
        data['session_with_commit'] = session

    async def after_handler(self, session) -> None:
        await session.commit()