# Room Scheduler - A1-3195197

## Student Information
- Student Number: 3195197
- Module: Cloud Platforms & Applications
- Assignment: 1 of 2

## Application Overview
A web-based room scheduling application built with FastAPI, MongoDB, and Firebase Authentication. Users can add rooms, make bookings, view and manage their bookings, and see room availability.

## Prerequisites
- Python 3.13 installed
- Internet connection (for MongoDB Atlas and Firebase)

## Setup and Run Instructions

### Step 1: Open terminal in project folder
Open VS Code, then open terminal with Ctrl and backtick key

### Step 2: Create virtual environment
Run this command:
    python -m venv env

### Step 3: Activate virtual environment
On Windows PowerShell run:
    .\env\Scripts\activate.ps1

You should see (env) at the start of your terminal line.

### Step 4: Install dependencies
Run this command:
    pip install -r requirements.txt

### Step 5: Run the application
Run this command:
    uvicorn main:app --reload

### Step 6: Open browser and navigate to
    http://127.0.0.1:8000

## Important Notes
- MongoDB Atlas free tier may take 5-10 seconds to wake up on first load
- Please wait and refresh the page if it does not load immediately on first visit
- Firebase authentication is pre-configured for project room-scheduler-31165
- Database name: A1-3195197

## Tech Stack
- Backend: FastAPI (Python)
- Database: MongoDB Atlas
- Authentication: Firebase
- Templates: Jinja2
- Server: Uvicorn

## Features
- Firebase login and logout
- Add and delete rooms
- Book rooms with clash detection
- Edit and delete bookings
- Filter bookings by day
- View room occupancy for next 5 days
- Earliest free time for next 5 days
- Calendar view for next 5 days