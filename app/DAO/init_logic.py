import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.DAO.dao import TableDAO, TimeSlotUserDAO
from app.DAO.database import async_session_maker
from pydantic import BaseModel


class TableBase(BaseModel):
    capacity: int
    description: str


class TimeSlotBase(BaseModel):
    start_time: str
    end_time: str


async def add_tables_to_db(session: AsyncSession):
    with open(settings.TABLES_JSON, "r", encoding='utf-8') as file:
        tables_data = json.load(file)
    await TableDAO(session).add_many([TableBase(**table) for table in tables_data])

async def add_time_slots_to_db(session: AsyncSession):
    with open(settings.SLOTS_JSON, 'r', encoding='utf-8') as file:
        tables_data = json.load(file)
    await TimeSlotUserDAO(session).add_many([TimeSlotBase(**table) for table in tables_data])


async def init_db():
    async with async_session_maker() as session:
        await add_tables_to_db(session)
        await add_time_slots_to_db(session)
        await session.commit()