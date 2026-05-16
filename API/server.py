from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from tinydb import Query
import os
import base64
import httpx
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
from typing import Optional
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.config import (
    BOT_TOKEN, CHANNEL_ID,
    OFFICE_LAT, OFFICE_LON,
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


# ─── SCHEMAS ──────────────────────────────────────────────────────────────────
class AttendanceRequest(BaseModel):
    telegram_id:  int
    type:         str
    latitude:     float
    longitude:    float
    accuracy:     float
    selfie_data:  str
    init_data:    str           = ""
    timestamp:    Optional[str] = None
    device_info:  Optional[str] = None
    platform:     Optional[str] = None
    capture_time: Optional[int] = None


class EmployeeRequest(BaseModel):
    telegram_id: int
    fullname:    str
    position:    str
    active:      bool = True


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def find_employee(telegram_id: int):
    Employee = Query()
    return employees_table.get(Employee.telegram_id == telegram_id)


# ─── TELEGRAM KANALGA RASM YUBORISH ──────────────────────────────────────────
async def send_to_channel(
    image_bytes: bytes,
    employee_name: str,
    position: str,
    telegram_id: int,
    att_type: str,
    latitude: float,
    longitude: float,
    accuracy: float,
):
    """Rasmni caption bilan Telegram kanalga yuboradi"""

    now = datetime.now()
    sana = now.strftime("%d.%m.%Y")
    vaqt = now.strftime("%H:%M:%S")

    emoji  = "🟢" if att_type == "KIRISH" else "🔴"
    label  = "KIRISH" if att_type == "KIRISH" else "CHIQISH"
    maps   = f"https://maps.google.com/?q={latitude},{longitude}"

    caption = (
        f"{emoji} <b>{label}</b>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Ism:</b> {employee_name}\n"
        f"💼 <b>Lavozim:</b> {position}\n"
        f"🆔 <b>ID:</b> <code>{telegram_id}</code>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"📅 <b>Sana:</b> {sana}\n"
        f"🕐 <b>Vaqt:</b> {vaqt}\n"
        f"📍 <b>Joylashuv:</b> <a href='{maps}'>Xaritada ko'rish</a>\n"
        f"🎯 <b>Aniqlik:</b> ±{int(accuracy)}m"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            url,
            data={
                "chat_id":    str(CHANNEL_ID),
                "caption":    caption,
                "parse_mode": "HTML",
            },
            files={
                "photo": ("selfie.jpg", image_bytes, "image/jpeg")
            }
        )

    if response.status_code != 200:
        print(f"[TELEGRAM ERROR] {response.status_code}: {response.text}", flush=True)
    else:
        print(f"[TELEGRAM] Kanal ga yuborildi: {employee_name} {label}", flush=True)


# ─── ROOT ─────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "Davomat API is running"}


# ─── ATTENDANCE ───────────────────────────────────────────────────────────────
@app.post("/api/attendance")
async def submit_attendance(req: AttendanceRequest):
    try:
        # 1. Telegram init_data tekshirish
        if req.init_data:
            try:
                validate_init_data(req.init_data, BOT_TOKEN)
            except ValueError:
                raise HTTPException(status_code=401, detail="Telegram ma'lumotlari noto'g'ri")

        # 2. Xodimni topish
        employee = find_employee(req.telegram_id)
        if not employee:
            raise HTTPException(
                status_code=404,
                detail=f"Xodim topilmadi (ID: {req.telegram_id}). Botda ro'yxatdan o'ting."
            )

        # 3. Lokatsiya tekshirish
        if OFFICE_LAT != 0 and OFFICE_LON != 0:
            distance = haversine(req.latitude, req.longitude, OFFICE_LAT, OFFICE_LON)
            if distance > OFFICE_RADIUS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ofisdan uzoqdasiz ({int(distance)}m). Ruxsat: {int(OFFICE_RADIUS)}m"
                )

        # 4. Base64 → bytes
        clean_b64 = req.selfie_data.split(",")[1] if "," in req.selfie_data else req.selfie_data
        try:
            image_bytes = base64.b64decode(clean_b64)
        except Exception:
            raise HTTPException(status_code=400, detail="Rasm ma'lumoti noto'g'ri")

        # 5. Rasmni diskka saqlash
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{req.telegram_id}_{ts}_{req.type}.jpg"
        filepath = os.path.join(UPLOADS_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)

        # 6. Bazaga yozish
        record = {
            "employee_id":   req.telegram_id,
            "employee_name": employee.get("fullname", ""),
            "position":      employee.get("position", ""),
            "type":          req.type,
            "timestamp":     datetime.now().isoformat(),
            "latitude":      req.latitude,
            "longitude":     req.longitude,
            "accuracy":      req.accuracy,
            "photo_path":    filepath,
            "status":        "completed",
        }
        attendance_table.insert(record)

        # 7. Telegram kanalga yuborish
        await send_to_channel(
            image_bytes   = image_bytes,
            employee_name = employee.get("fullname", "Noma'lum"),
            position      = employee.get("position", ""),
            telegram_id   = req.telegram_id,
            att_type      = req.type,
            latitude      = req.latitude,
            longitude     = req.longitude,
            accuracy      = req.accuracy,
        )

        label = "Kirish" if req.type == "KIRISH" else "Chiqish"
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"{label} muvaffaqiyatli qayd etildi ✓",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
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
async def add_employee(req: EmployeeRequest):
    try:
        if find_employee(req.telegram_id):
            raise HTTPException(status_code=400, detail="Xodim allaqachon mavjud")

        employee = {
            "telegram_id": req.telegram_id,
            "fullname":    req.fullname,
            "position":    req.position,
            "active":      req.active,
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
    uvicorn.run(app, host=HOST, port=PORT)
