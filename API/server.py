from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
import json
from datetime import datetime
from typing import Optional
import hashlib
import hmac
import sys

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.config import BOT_TOKEN, OFFICE_LAT, OFFICE_LON
from utils.db import employees_table, attendance_table
from utils.telegram_utils import validate_init_data

app = FastAPI(title="Davomat API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your WebApp domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploads (only for /uploads/ path)
app.mount("/uploads", StaticFiles(directory="../uploads"), name="uploads")

@app.get("/")
async def root():
    return {"message": "Davomat API is running"}

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
    capture_time: int = None
):
    try:
        # Validate Telegram init data
        if not validate_init_data(init_data):
            raise HTTPException(status_code=401, detail="Invalid Telegram data")

        # Check if employee exists
        employee = employees_table.get(doc_id=telegram_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not registered")

        # Validate location (within 100m of office)
        from math import radians, sin, cos, sqrt, atan2

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371  # Earth's radius in km
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            return R * c * 1000  # Convert to meters

        distance = haversine(latitude, longitude, OFFICE_LAT, OFFICE_LON)
        if distance > 100:  # 100 meters tolerance
            raise HTTPException(status_code=400, detail="Location too far from office")

        # Convert base64 to image
        import base64
        from PIL import Image
        import io

        # Remove data URL prefix if present
        if selfie_data.startswith('data:image/'):
            selfie_data = selfie_data.split(',')[1]

        image_data = base64.b64decode(selfie_data)
        image = Image.open(io.BytesIO(image_data))

        # Save photo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{telegram_id}_{timestamp}_{type}.jpg"
        filepath = os.path.join("..", "uploads", filename)

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        image.save(filepath, "JPEG")

        # Save attendance record
        attendance_record = {
            "employee_id": telegram_id,
            "employee_name": employee['fullname'],
            "type": type,
            "timestamp": datetime.now().isoformat(),
            "latitude": latitude,
            "longitude": longitude,
            "photo_path": filepath,
            "status": "completed"
        }

        attendance_table.insert(attendance_record)

        return JSONResponse(
            content={
                "success": True,
                "message": f"{type.capitalize()} recorded successfully",
                "data": attendance_record
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/employees")
async def get_employees():
    try:
        employees = employees_table.all()
        return {"employees": employees}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/employees")
async def add_employee(employee_data: dict):
    try:
        # Validate required fields
        required_fields = ['telegram_id', 'fullname', 'position']
        for field in required_fields:
            if field not in employee_data:
                raise HTTPException(status_code=400, detail=f"Missing field: {field}")

        # Check if employee already exists
        existing = employees_table.get(doc_id=employee_data['telegram_id'])
        if existing:
            raise HTTPException(status_code=400, detail="Employee already exists")

        employee = {
            "telegram_id": employee_data['telegram_id'],
            "fullname": employee_data['fullname'],
            "position": employee_data['position'],
            "active": employee_data.get('active', True),
            "created_at": datetime.now().isoformat()
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
        employee = employees_table.get(doc_id=employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")

        # Update fields
        for key, value in employee_data.items():
            if key in ['fullname', 'position', 'active']:
                employee[key] = value

        employee['updated_at'] = datetime.now().isoformat()
        employees_table.update(employee, doc_ids=[employee_id])

        return {"success": True, "employee": employee}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/employees/{employee_id}")
async def delete_employee(employee_id: int):
    try:
        employee = employees_table.get(doc_id=employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")

        employees_table.remove(doc_ids=[employee_id])
        return {"success": True, "message": "Employee deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)