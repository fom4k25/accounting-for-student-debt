from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List
import uvicorn
from datetime import datetime
import webbrowser
import threading

from database import SessionLocal, engine, Base
import models
import schemas  # Импортируем схемы напрямую
from crud import crud

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Система учета задолженностей студентов",
    description="API для управления задолженностями студентов и расписанием",
    version="1.0.0"
)

# Настройка шаблонов и статики
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Веб-интерфейс (главная страница)
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request, db: Session = Depends(get_db)):
    students = crud.get_students(db)
    # Возвращаем все задолженности
    debts = crud.get_debts(db)
    schedules = crud.get_schedules(db)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "students": students,
            "debts": debts,
            "schedules": schedules
        }
    )

@app.get("/search-student", response_class=HTMLResponse)
def search_student(request: Request, student_id: str, db: Session = Depends(get_db)):
    # Получаем студента по номеру студенческого билета
    student = db.query(models.Student).filter(models.Student.student_id == student_id).first()
    
    if student:
        # Получаем только активные задолженности студента
        student_debts = db.query(models.Debt).filter(
            models.Debt.student_id == student.id,
            models.Debt.status == "активна"
        ).all()
        
        search_result = {
            "name": student.name,
            "debts_count": len(student_debts),
            "debts": student_debts
        }
    else:
        search_result = None
    
    # Получаем все данные для отображения на главной странице
    students = crud.get_students(db)
    debts = crud.get_debts(db)  # Возвращаем все задолженности
    schedules = crud.get_schedules(db)
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "students": students,
            "debts": debts,
            "schedules": schedules,
            "search_result": search_result
        }
    )

# Обработка форм (добавление через веб)
@app.post("/students/", response_class=HTMLResponse)
def add_student(request: Request, name: str = Form(...), faculty: str = Form(...), group: str = Form(...), student_id: str = Form(...), db: Session = Depends(get_db)):
    student = schemas.StudentCreate(name=name, faculty=faculty, group=group, student_id=student_id)
    crud.create_student(db, student)
    return read_root(request, db)

@app.post("/debts/", response_class=HTMLResponse)
def add_debt(request: Request, student_id: int = Form(...), subject: str = Form(...), db: Session = Depends(get_db)):
    debt = schemas.DebtCreate(student_id=student_id, subject=subject, status="активна")
    result = crud.create_debt(db, debt)
    if not result:
        # Если студент не найден, возвращаем на главную страницу с сообщением об ошибке
        return RedirectResponse(url="/?error=student_not_found", status_code=303)
    return read_root(request, db)

@app.post("/schedule/", response_class=HTMLResponse)
def add_schedule(request: Request, debt_id: int = Form(...), group: str = Form(...), teacher: str = Form(...), due_date: str = Form(...), db: Session = Depends(get_db)):
    schedule = schemas.ScheduleCreate(debt_id=debt_id, group=group, teacher=teacher, date=datetime.strptime(due_date, '%Y-%m-%dT%H:%M'))
    result = crud.create_schedule(db, schedule)
    if not result:
        # Если задолженность не найдена или не активна, возвращаем на главную страницу с сообщением об ошибке
        return RedirectResponse(url="/?error=debt_not_found_or_inactive", status_code=303)
    return read_root(request, db)

# --- API ENDPOINTS ---
@app.post("/api/students/", response_model=schemas.Student)
def create_student(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    return crud.create_student(db=db, student=student)

@app.get("/api/students/", response_model=List[schemas.Student])
def read_students(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_students(db, skip=skip, limit=limit)

@app.get("/api/students/{student_id}", response_model=schemas.Student)
def read_student(student_id: int, db: Session = Depends(get_db)):
    db_student = crud.get_student(db, student_id=student_id)
    if db_student is None:
        raise HTTPException(status_code=404, detail="Студент не найден")
    return db_student

@app.get("/api/students/search/{student_id}", response_model=schemas.StudentWithDebts)
def search_student_by_id(student_id: str, db: Session = Depends(get_db)):
    # Получаем студента по номеру студенческого билета
    student = db.query(models.Student).filter(models.Student.student_id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Студент не найден")
    
    # Получаем все задолженности студента
    student_debts = db.query(models.Debt).filter(models.Debt.student_id == student.id).all()
    
    return {
        "id": student.id,
        "name": student.name,
        "faculty": student.faculty,
        "group": student.group,
        "student_id": student.student_id,
        "created_at": student.created_at,
        "debts": student_debts,
        "debts_count": len(student_debts)
    }

@app.put("/api/students/{student_id}", response_model=schemas.Student)
def update_student(student_id: int, student: schemas.StudentCreate, db: Session = Depends(get_db)):
    db_student = crud.update_student(db, student_id, student)
    if db_student is None:
        raise HTTPException(status_code=404, detail="Студент не найден")
    return db_student

@app.delete("/api/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    result = crud.delete_student(db, student_id)
    if not result:
        raise HTTPException(status_code=404, detail="Студент не найден")
    return {"ok": True}

@app.post("/api/debts/", response_model=schemas.Debt)
def create_debt(debt: schemas.DebtCreate, db: Session = Depends(get_db)):
    return crud.create_debt(db=db, debt=debt)

@app.get("/api/debts/", response_model=List[schemas.Debt])
def read_debts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_debts(db, skip=skip, limit=limit)

@app.get("/api/debts/student/{student_id}", response_model=List[schemas.Debt])
def read_student_debts(student_id: int, db: Session = Depends(get_db)):
    return crud.get_student_debts(db, student_id=student_id)

@app.post("/api/debts/pay/{debt_id}", response_model=schemas.Debt)
def pay_debt(debt_id: int, db: Session = Depends(get_db)):
    debt = crud.pay_debt(db, debt_id)
    if not debt:
        raise HTTPException(status_code=404, detail="Задолженность не найдена")
    return debt

@app.post("/api/schedule/", response_model=schemas.Schedule)
def create_schedule(schedule: schemas.ScheduleCreate, db: Session = Depends(get_db)):
    return crud.create_schedule(db=db, schedule=schedule)

@app.get("/api/schedule/", response_model=List[schemas.Schedule])
def read_schedule(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_schedules(db, skip=skip, limit=limit)

@app.put("/api/schedule/{schedule_id}", response_model=schemas.Schedule)
def update_schedule(schedule_id: int, schedule: schemas.ScheduleCreate, db: Session = Depends(get_db)):
    db_schedule = crud.update_schedule(db, schedule_id, schedule)
    if db_schedule is None:
        raise HTTPException(status_code=404, detail="Запись в расписании не найдена")
    return db_schedule

@app.delete("/api/schedule/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    result = crud.delete_schedule(db, schedule_id)
    if not result:
        raise HTTPException(status_code=404, detail="Запись в расписании не найдена")
    return {"ok": True}

@app.post("/students/update/{student_id}", response_class=HTMLResponse)
def update_student_form(request: Request, student_id: int, name: str = Form(...), faculty: str = Form(...), group: str = Form(...), student_id_value: str = Form(...), db: Session = Depends(get_db)):
    student = schemas.StudentCreate(name=name, faculty=faculty, group=group, student_id=student_id_value)
    crud.update_student(db, student_id, student)
    return RedirectResponse(url="/", status_code=303)

@app.post("/students/delete/{student_id}", response_class=HTMLResponse)
def delete_student_form(request: Request, student_id: int, db: Session = Depends(get_db)):
    crud.delete_student(db, student_id)
    return RedirectResponse(url="/", status_code=303)

@app.post("/debts/update/{debt_id}", response_class=HTMLResponse)
def update_debt_form(request: Request, debt_id: int, student_id: int = Form(...), subject: str = Form(...), status: str = Form(...), db: Session = Depends(get_db)):
    debt = schemas.DebtCreate(student_id=student_id, subject=subject, status=status)
    crud.update_debt(db, debt_id, debt)
    return RedirectResponse(url="/", status_code=303)

@app.post("/debts/delete/{debt_id}", response_class=HTMLResponse)
def delete_debt_form(request: Request, debt_id: int, db: Session = Depends(get_db)):
    crud.delete_debt(db, debt_id)
    return RedirectResponse(url="/", status_code=303)

@app.post("/schedule/update/{schedule_id}", response_class=HTMLResponse)
def update_schedule_form(request: Request, schedule_id: int, debt_id: int = Form(...), group: str = Form(...), teacher: str = Form(...), date: str = Form(...), db: Session = Depends(get_db)):
    schedule = schemas.ScheduleCreate(debt_id=debt_id, group=group, teacher=teacher, date=datetime.strptime(date, '%Y-%m-%dT%H:%M'))
    crud.update_schedule(db, schedule_id, schedule)
    return RedirectResponse(url="/", status_code=303)

@app.post("/schedule/delete/{schedule_id}", response_class=HTMLResponse)
def delete_schedule_form(request: Request, schedule_id: int, db: Session = Depends(get_db)):
    crud.delete_schedule(db, schedule_id)
    return RedirectResponse(url="/", status_code=303)

@app.get("/student/{student_id}", response_class=HTMLResponse)
def student_detail(request: Request, student_id: int, db: Session = Depends(get_db)):
    student = crud.get_student(db, student_id)
    if not student:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("student_detail.html", {"request": request, "student": student})

@app.post("/student/{student_id}/update", response_class=HTMLResponse)
def update_student_page(request: Request, student_id: int, name: str = Form(...), faculty: str = Form(...), group: str = Form(...), student_id_value: str = Form(...), db: Session = Depends(get_db)):
    student = schemas.StudentCreate(name=name, faculty=faculty, group=group, student_id=student_id_value)
    crud.update_student(db, student_id, student)
    return RedirectResponse(url=f"/student/{student_id}", status_code=303)

@app.post("/student/{student_id}/delete", response_class=HTMLResponse)
def delete_student_page(request: Request, student_id: int, db: Session = Depends(get_db)):
    crud.delete_student(db, student_id)
    return RedirectResponse(url="/", status_code=303)

@app.get("/debt/{debt_id}", response_class=HTMLResponse)
def debt_detail(request: Request, debt_id: int, db: Session = Depends(get_db)):
    debt = db.query(models.Debt).filter(models.Debt.id == debt_id).first()
    students = crud.get_students(db)
    if not debt:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("debt_detail.html", {
        "request": request,
        "debt": debt,
        "students": students
    })

@app.post("/debt/{debt_id}/update", response_class=HTMLResponse)
def update_debt_page(request: Request, debt_id: int, student_id: int = Form(...), subject: str = Form(...), status: str = Form(...), db: Session = Depends(get_db)):
    debt = schemas.DebtCreate(student_id=student_id, subject=subject, status=status)
    crud.update_debt(db, debt_id, debt)
    return RedirectResponse(url=f"/debt/{debt_id}", status_code=303)

@app.post("/debt/{debt_id}/delete", response_class=HTMLResponse)
def delete_debt_page(request: Request, debt_id: int, db: Session = Depends(get_db)):
    crud.delete_debt(db, debt_id)
    return RedirectResponse(url="/", status_code=303)

@app.get("/schedule/{schedule_id}", response_class=HTMLResponse)
def schedule_detail(request: Request, schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    debts = crud.get_debts(db)
    if not schedule:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("schedule_detail.html", {
        "request": request,
        "schedule": schedule,
        "debts": debts
    })

@app.post("/schedule/{schedule_id}/update", response_class=HTMLResponse)
def update_schedule_page(request: Request, schedule_id: int, debt_id: int = Form(...), group: str = Form(...), teacher: str = Form(...), date: str = Form(...), db: Session = Depends(get_db)):
    schedule = schemas.ScheduleCreate(debt_id=debt_id, group=group, teacher=teacher, date=datetime.strptime(date, '%Y-%m-%dT%H:%M'))
    crud.update_schedule(db, schedule_id, schedule)
    return RedirectResponse(url="/", status_code=303)

@app.post("/schedule/{schedule_id}/delete", response_class=HTMLResponse)
def delete_schedule_page(request: Request, schedule_id: int, db: Session = Depends(get_db)):
    crud.delete_schedule(db, schedule_id)
    return RedirectResponse(url="/", status_code=303)

@app.post("/debts/pay/{debt_id}", response_class=HTMLResponse)
def pay_debt_from_schedule(request: Request, debt_id: int, db: Session = Depends(get_db)):
    debt = crud.pay_debt(db, debt_id)
    return RedirectResponse(url="/", status_code=303)

# --- Запуск ---
if __name__ == "__main__":
    def run():
        print("\nВеб-интерфейс: http://127.0.0.1:8000\nAPI документация: http://127.0.0.1:8000/docs\n")
        webbrowser.open("http://127.0.0.1:8000")
        uvicorn.run(app, host="127.0.0.1", port=8000)
    run()
