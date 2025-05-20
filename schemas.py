from pydantic import BaseModel
from datetime import datetime

class DebtBase(BaseModel):
    subject: str
    student_id: int
    status: str = "активна"

class DebtCreate(DebtBase):
    pass

class Debt(DebtBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class StudentBase(BaseModel):
    name: str
    faculty: str
    group: str
    student_id: str

class StudentCreate(StudentBase):
    pass

class Student(StudentBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ScheduleBase(BaseModel):
    debt_id: int
    group: str
    teacher: str
    date: datetime

class ScheduleCreate(ScheduleBase):
    pass

class Schedule(ScheduleBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class StudentWithDebts(Student):
    debts: list[Debt]
    debts_count: int

    class Config:
        from_attributes = True 