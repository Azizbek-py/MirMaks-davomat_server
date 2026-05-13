# Davomat API

FastAPI server for attendance processing.

## Features
- Attendance validation
- Telegram initData verification
- GPS location checking
- Photo storage
- Telegram channel notifications

## Setup
1. Copy `.env` file from root directory
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `uvicorn server:app --host 0.0.0.0 --port 8000`

## Endpoints
- `GET /api/health` - Health check
- `POST /api/validate` - Validate initData
- `POST /api/attendance` - Process attendance

## Deployment
Deploy to:
- Heroku
- Railway
- DigitalOcean App Platform
- AWS/GCP/Azure