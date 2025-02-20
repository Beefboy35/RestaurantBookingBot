from typing import List, TypeVar, Generic, Type
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy import update as sqlalchemy_update, delete as sqlalchemy_delete, func
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.DAO.database import Base

T = TypeVar("T", bound=Base)


class BaseDAO(Generic[T]):
    model: Type[T] = None

    def __init__(self, session: AsyncSession):
        self._session = session
        if self.model is None:
            raise ValueError("Model must be specified in the child class")

    async def find_one_or_none_by_id(self, data_id: int):
        try:
            query = select(self.model).filter_by(id=data_id)
            result = await self._session.execute(query)
            record = result.scalar_one_or_none()
            log_message = f"Record {self.model.__name__} with ID {data_id} {'successfully found' if record else 'not found'}."
            logger.info(log_message)
            return record
        except SQLAlchemyError as e:
            logger.error(f"Error while searching for the record with ID {data_id}: {e}")
            raise

    async def find_one_or_none(self, filters: BaseModel):
        filter_dict = filters.model_dump(exclude_unset=True)
        logger.info(f"Search for a single entry {self.model.__name__} by filters {filter_dict}")
        try:
            stmt = select(self.model).filter_by(**filter_dict)
            result = await self._session.execute(stmt)
            entry = result.scalar_one_or_none()
            log_message = f"Entry {"found" if entry else "not found"} by filters {filter_dict}"
            logger.info(log_message)
            return entry
        except SQLAlchemyError as e:
            logger.error(f"Error searching for entry by filters {filter_dict}: {e}")
            raise
    async def add(self, values: BaseModel):
        values_dict = values.model_dump(exclude_unset=True)
        logger.info(f"Adding multiple entries {self.model.__name__}. Quantity: {len(values_dict)}")
        try:
            new_instance = self.model(**values_dict)
            self._session.add(new_instance)
            logger.info(f"Entry {self.model.__name__} successfully added")
            await self._session.flush()
            return new_instance
        except SQLAlchemyError as e:
            logger.error(f"Error adding the record: {e}")
            await self._session.rollback()
            raise

    async def add_many(self, instance: List[BaseModel]):
        values_list = [item.model_dump(exclude_unset=True) for item in instance]
        logger.info(f"Adding multiple entries {self.model.__name__}. Quantity: {len(values_list)}")
        try:
            new_instances = [self.model(**inst) for inst in values_list]
            self._session.add_all(new_instances)
            logger.info(f"{len(new_instances)} entries successfully added")
            await self._session.flush()
            return new_instances
        except SQLAlchemyError as e:
            logger.error(f"Error adding multiple entries: {e}")
            await self._session.rollback()
            raise


    async def find_all(self, filters: BaseModel | None = None):
        filter_dict = filters.model_dump(exclude_unset=True) if filters else {}
        logger.info(f"Searching for all entries {self.model.__name__} by filters: {filter_dict}")
        try:
            stmt = select(self.model).filter_by(**filter_dict)
            result = await self._session.execute(stmt)
            records = result.scalars().all()
            logger.info(f"{len(records)} entries found")
            return records
        except SQLAlchemyError as e:
            logger.error(f"Error fetching all entries by filters: {e}")
            raise

    async def update(self, filters: BaseModel, values: BaseModel):
        filter_dict = filters.model_dump(exclude_unset=True)
        values_dict = values.model_dump(exclude_unset=True)
        logger.info(
            f"Updating entries {self.model.__name__} by filter: {filter_dict} with parameters: {values_dict}")
        try:
            query = (
                sqlalchemy_update(self.model)
                .where(*[getattr(self.model, k) == v for k, v in filter_dict.items()])
                .values(**values_dict)
                .execution_options(synchronize_session="fetch")
            )
            result = await self._session.execute(query)
            logger.info(f"{result.rowcount} entries updated.")
            await self._session.flush()
            return result.rowcount
        except SQLAlchemyError as e:
            logger.error(f"Error updating the entry: {e}")
            raise

    async def delete(self, filters: BaseModel):
        filter_dict = filters.model_dump(exclude_unset=True)
        logger.info(f"Удаление записей {self.model.__name__} по фильтру: {filter_dict}")
        if not filter_dict:
            logger.error("Нужен хотя бы один фильтр для удаления.")
            raise ValueError("Нужен хотя бы один фильтр для удаления.")
        try:
            query = sqlalchemy_delete(self.model).filter_by(**filter_dict)
            result = await self._session.execute(query)
            logger.info(f"Удалено {result.rowcount} записей.")
            await self._session.flush()
            return result.rowcount
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при удалении записей: {e}")
            raise

    async def count(self, filters: BaseModel | None = None):
        filter_dict = filters.model_dump(exclude_unset=True) if filters else {}
        logger.info(f"Counting the number of entries {self.model.__name__} by filter: {filter_dict}")
        try:
            stmt = select(func.count()).select_from(self.model).filter_by(**filter_dict)
            result = await self._session.execute(stmt)
            res = result.scalar()
            logger.info(f"{res} entries found")
            return res
        except SQLAlchemyError as e:
            logger.error(f"Error counting entries: {e}")
            raise
