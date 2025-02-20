from datetime import date, datetime, tzinfo
from typing import Dict
from loguru import logger
from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from app.DAO.base import BaseDAO
from app.DAO.models import User, Table, Booking, TimeSlot


class UserDAO(BaseDAO[User]):
    model = User

class TimeSlotUserDAO(BaseDAO[TimeSlot]):
    model = TimeSlot


class TableDAO(BaseDAO[Table]):
    model = Table


class BookingDAO(BaseDAO[Booking]):
    model = Booking
    async def check_available_bookings(self, table_id: int, booking_date: date, time_slot_id: int):
        '''Check for available reservations at the specified date and time slot'''
        try:
            stmt = select(self.model).filter_by(table_id=table_id, date=booking_date, time_slot_id=time_slot_id)
            result = await self._session.execute(stmt)
            if not result.scalars().all():
                return True
            for booking in result.scalars().all():
                if booking.status == "booked":
                    return False
                continue
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error checking reservation availability: {e}")


    async def get_available_time_slots(self, table_id: int, booking_date: date):
        """
        Acquiring all free time slots for the table on the specified date
        """
        try:
            booking_stmt = select(self.model).filter_by(table_id=table_id, date=booking_date)
            booking_result = await self._session.execute(booking_stmt)
            #create a set of occupied tables
            booked_slots = {booking.time_slot_id for booking in booking_result.scalars().all() if booking.status == "booked"}
            #acquiring all free slots, excluding occupied ones
            free_slots_stmt = select(TimeSlot).filter(~TimeSlot.id.in_(booked_slots))
            free_slots_result = await self._session.execute(free_slots_stmt)
            return free_slots_result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error acquiring available time slots for the date {e}")

    async def get_bookings_with_details(self, user_id: int):
        """
        Acquire the list of all user's reservations with details
        :params user_id:  user's ID
        :return: A list of the Booking objects with uploaded data about table and time information
        """
        try:
            stmt = select(self.model).options(
                joinedload(self.model.table),
                joinedload(self.model.time_slot)
            ).filter_by(user_id=user_id)
            result = await self._session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error acquiring reservations with details: {e}")
            return []

    async def complete_past_bookings(self):
        """
        Update the booking status to 'completed'
        if  the date and time of the booking have already passed
        """
        try:
            now = datetime.now()
            sub_stmt = select(TimeSlot.start_time).where(TimeSlot.id == self.model.time_slot_id).scalar_subquery()
            stmt = select(Booking.id).where(
                Booking.date > now.date(),
                            self.model.status == "booked"
            ).union_all(
                select(Booking.id).where(self.model.date == now.date(),
                                         sub_stmt > now.time(),
                                         self.model.status == "booked"
                                         )
            )
            result = await self._session.execute(stmt)
            reservation_ids_to_update = result.scalars().all()
            if reservation_ids_to_update:
                #form statement to update booking status
                update_stmt = (update(Booking)
                               .where(Booking.id.in_(reservation_ids_to_update))
                               .values(status="completed")
                               )
                #Executing an update query
                await self._session.execute(update_stmt)

                #Commit the change
                await self._session.commit()
                logger.info(f"Status for {len(reservation_ids_to_update)} reservations changed to 'completed'")
            else:
                logger.info("No reservations to update status")
        except SQLAlchemyError as e:
            logger.error(f"Error updating reservations' status to 'completed': {e}")

    async def cancel_reservation(self, book_id: int):
        try:
            stmt = (update(self.model)
                    .filter_by(id=book_id)
                    .values(status="canceled")
                    .execution_options(synchronize_session="fetch")
            )
            result = await self._session.execute(stmt)
            await self._session.flush()
            return result.rowcount
        except SQLAlchemyError as e:
            logger.error(f"Error canceling the booking with id {book_id}: {e}")
            await self._session.rollback()
            raise

    async def delete_booking(self, book_id: int):
        try:
            stmt = delete(self.model).filter_by(id=book_id)
            result = await self._session.execute(stmt)
            logger.info(f"{result.rowcount} records are deleted")
            await self._session.flush()
            return result.rowcount
        except SQLAlchemyError as e:
            logger.info(f"Error deleting records: {e}")
            await self._session.rollback()
            raise

    async def entries_count(self) -> Dict[str, int]:
        """
        Counting the number of entries by status ('booked', 'completed', 'canceled')
        """
        try:
            entries_count = {}
            states = ["booked", "completed", "canceled"]
            for st in states:
                stmt = select(func.count(self.model.id)).where(self.model.status == st)
                result = await self._session.execute(stmt)
                count = result.scalar()
                entries_count[st] = count
                logger.info(f"{count} entries with status {st} found")
            total_stmt = select(func.count(self.model.id))
            total_res = await self._session.execute(total_stmt)
            total_count = total_res.scalar()
            entries_count["total"] = total_count
            logger.info(f"{total_count} entries found in total")
            return entries_count
        except SQLAlchemyError as e:
            logger.error(f"Error counting entries by status: {e}")
            raise


