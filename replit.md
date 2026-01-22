# ClickCounter

## Overview
A Portuguese-language button click counter web application built with Flask. Users can click any of 4 buttons, and the app tracks clicks with a daily sequential counter stored in Replit DB.

## Project Structure
- `main.py` - Flask backend with API endpoints for click tracking
- `templates/index.html` - Main HTML template
- `static/app.js` - Frontend JavaScript for handling button clicks
- `static/styles.css` - Styling

## Features
- 4 clickable buttons (Botão 1-4)
- Daily click counter that resets each day
- Click history stored in Replit DB
- Timezone-aware timestamps (configurable via TIMEZONE env var)

## API Endpoints
- `GET /` - Main page
- `GET /api/status` - Get current counter status
- `GET /api/clicks/today` - Get today's click history
- `POST /api/click` - Record a button click

## Running the App
The app runs on port 5000 with Flask's development server.

## Environment Variables
- `TIMEZONE` or `TZ` - Set timezone (default: Europe/Lisbon)
- `PORT` - Server port (default: 5000)
