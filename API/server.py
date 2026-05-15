from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from tinydb import Query
import os
import base64
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.config import (
    BOT_TOKEN, OFFICE_LAT, OFFICE_LON,
    OFFICE_RADIUS, UPLOADS_DIR
)
from utils.db import employees_table, attendance_table
from utils.telegram_utils import validate_init_data

app = FastAPI(title="Davomat API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(UPLOADS_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2) -> float:
    """Ikki nuqta orasidagi masofa (metrda)"""
    R = 6371000  # metr
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def find_employee(telegram_id: int):
    """TinyDB dan telegram_id bo'yicha xodim topish"""
    Employee = Query()
    return employees_table.get(Employee.telegram_id == telegram_id)


# ─── ROOT ─────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "Davomat API is running"}


# ─── ATTENDANCE ───────────────────────────────────────────────────────────────
@app.post("/api/attendance")
async def submit_attendance(
    telegram_id: int,
    type: str,
    latitude: float,
    longitude: float,
    accuracy: float,
    selfie_data: str,
    init_data: str,
    device_info: str = None,
    platform: str = None,
    capture_time: int = None,
):
    try:
        # 1. Telegram init_data tekshirish
        #    init_data bo'sh bo'lsa (test/brauzerdan) — o'tkazib yuboramiz
        if init_data:
            try:
                validate_init_data(init_data, BOT_TOKEN)
            except ValueError:
                raise HTTPException(status_code=401, detail="Telegram ma'lumotlari noto'g'ri")

        # 2. Xodimni topish (Query bilan, doc_id emas)
        employee = find_employee(telegram_id)
        if not employee:
            raise HTTPException(
                status_code=404,
                detail=f"Xodim topilmadi (telegram_id={telegram_id}). Avval botda ro'yxatdan o'ting."
            )

        # 3. Lokatsiya tekshirish
        #    OFFICE_LAT/LON = 0 bo'lsa (sozlanmagan) — tekshirishni o'tkazib yuboramiz
        if OFFICE_LAT != 0 and OFFICE_LON != 0:
            distance = haversine(latitude, longitude, OFFICE_LAT, OFFICE_LON)
            if distance > OFFICE_RADIUS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ofisdan uzoqdasiz ({int(distance)}m). Ruxsat etilgan masofa: {int(OFFICE_RADIUS)}m"
                )

        # 4. Rasmni saqlash
        #    data:image/... prefix bo'lsa olib tashlaymiz
        clean_b64 = selfie_data.split(",")[1] if "," in selfie_data else selfie_data

        try:
            image_bytes = base64.b64decode(clean_b64)
        except Exception:
            raise HTTPException(status_code=400, detail="Rasm ma'lumoti noto'g'ri (base64 xato)")

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{telegram_id}_{timestamp_str}_{type}.jpg"
        filepath = os.path.join(UPLOADS_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(image_bytes)

        # 5. Davomatni bazaga yozish
        record = {
            "employee_id":   telegram_id,
            "employee_name": employee.get("fullname", ""),
            "type":          type,
            "timestamp":     datetime.now().isoformat(),
            "latitude":      latitude,
            "longitude":     longitude,
            "accuracy":      accuracy,
            "photo_path":    filepath,
            "device_info":   device_info,
            "platform":      platform,
            "status":        "completed",
        }
        attendance_table.insert(record)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"{'Kirish' if type == 'KIRISH' else 'Chiqish'} muvaffaqiyatli qayd etildi ✓",
                "data": {k: v for k, v in record.items() if k != "photo_path"},
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        # Aniq xato xabarini Render logs da ko'rish uchun
        print(f"[ATTENDANCE ERROR] {type(e).__name__}: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Server xatosi: {str(e)}")


# ─── EMPLOYEES ────────────────────────────────────────────────────────────────
@app.get("/api/employees")
async def get_employees():
    try:
        return {"employees": employees_table.all()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/employees")
async def add_employee(employee_data: dict):
    try:
        for field in ["telegram_id", "fullname", "position"]:
            if field not in employee_data:
                raise HTTPException(status_code=400, detail=f"Maydon yetishmayapti: {field}")

        tid = int(employee_data["telegram_id"])
        if find_employee(tid):
            raise HTTPException(status_code=400, detail="Xodim allaqachon mavjud")

        employee = {
            "telegram_id": tid,
            "fullname":    employee_data["fullname"],
            "position":    employee_data["position"],
            "active":      employee_data.get("active", True),
            "created_at":  datetime.now().isoformat(),
        }
        employees_table.insert(employee)
        return {"success": True, "employee": employee}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/employees/{employee_id}")
async def update_employee(employee_id: int, employee_data: dict):
    try:
        Employee = Query()
        employee = employees_table.get(Employee.telegram_id == employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Xodim topilmadi")

        for key in ["fullname", "position", "active"]:
            if key in employee_data:
                employee[key] = employee_data[key]
        employee["updated_at"] = datetime.now().isoformat()

        employees_table.update(employee, Employee.telegram_id == employee_id)
        return {"success": True, "employee": employee}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/employees/{employee_id}")
async def delete_employee(employee_id: int):
    try:
        Employee = Query()
        employee = employees_table.get(Employee.telegram_id == employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Xodim topilmadi")

        employees_table.remove(Employee.telegram_id == employee_id)
        return {"success": True, "message": "Xodim o'chirildi"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    from utils.config import HOST, PORT
    uvicorn.run(app, host=HOST, port=PORT, reload=True)
