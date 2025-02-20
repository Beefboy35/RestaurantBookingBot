from pydantic import BaseModel
from datetime import date

class SCapacity(BaseModel):
    capacity: int


class SNewBooking(BaseModel):
    user_id: int
    table_id: int
    time_slot_id: int
    date: date
    status: str