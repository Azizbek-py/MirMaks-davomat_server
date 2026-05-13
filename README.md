# Davomat Server

FastAPI backend server for the Davomat attendance system.

## Features
- REST API for attendance processing
- Telegram WebApp data validation
- File upload handling (photos)
- Database operations with TinyDB
- CORS support for WebApp integration

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and configure
3. Run: `uvicorn API.server:app --reload`

## API Endpoints
- `POST /api/attendance` - Submit attendance with photo and location
- `GET /api/employees` - Get employee list
- `POST /api/employees` - Add new employee
- `PUT /api/employees/{id}` - Update employee
- `DELETE /api/employees/{id}` - Delete employee

## Environment Variables
- `BOT_TOKEN` - Telegram bot token
- `OFFICE_LAT` - Office latitude
- `OFFICE_LON` - Office longitude
- `SECRET_KEY` - Telegram WebApp secret

## Deployment
Deploy to:
- Heroku
- Railway
- DigitalOcean App Platform
- Any VPS with Python support

## Project Structure
- `API/` - FastAPI application
- `utils/` - Utility functions and config
- `db/` - Database files
- `uploads/` - Uploaded photos
- `.env` - Environment configuration