from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.oauth2.id_token
from google.auth.transport import requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
import starlette.status as status
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB
uri = os.getenv("MONGO_URI")
client = MongoClient(uri, server_api=ServerApi('1'))

# Ping to confirm connection
try:
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(e)

# Define the app
app = FastAPI()

# Open database and collections
db = client['A1-3195197']
room_collection = db['rooms']
day_collection = db['days']
booking_collection = db['bookings']

# Firebase request adapter
firebase_request_adapter = requests.Request()

# Static files and templates
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')


def validateFirebaseToken(id_token):
    if not id_token:
        return None
    user_token = None
    try:
        user_token = google.oauth2.id_token.verify_firebase_token(
            id_token, firebase_request_adapter)
    except ValueError as err:
        print(str(err))
    return user_token


@app.get('/', response_class=HTMLResponse)
async def root(request: Request):
    id_token = request.cookies.get('token')
    error_message = 'No error here'
    user_token = None

    user_token = validateFirebaseToken(id_token)

    # get all rooms
    rooms = []
    for room in room_collection.find():
        rooms.append(room)

    # get all bookings for current user
    bookings = []
    if user_token:
        for booking in booking_collection.find({'user_email': user_token['email']}):
            bookings.append(booking)

    return templates.TemplateResponse('index.html', {
        'request': request,
        'user_token': user_token,
        'error_message': error_message,
        'rooms': rooms,
        'bookings': bookings
    })


@app.post('/add-room', response_class=RedirectResponse)
async def addRoom(request: Request):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    form = await request.form()
    room_name = form['room_name']

    # check if room already exists
    existing_room = room_collection.find_one({'name': room_name})
    if existing_room:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    # add room to database
    room_collection.insert_one({
        'name': room_name,
        'created_by': user_token['email'],
        'day_list': []
    })

    return RedirectResponse('/', status_code=status.HTTP_302_FOUND)


@app.post('/add-booking', response_class=RedirectResponse)
async def addBooking(request: Request):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    form = await request.form()
    room_name = form['room_name']
    date = form['date']
    start_time = form['start_time']
    end_time = form['end_time']

    # check for clashing bookings
    existing_bookings = booking_collection.find({
        'room_name': room_name,
        'date': date
    })

    for existing in existing_bookings:
        existing_start = existing['start_time']
        existing_end = existing['end_time']
        if not (end_time <= existing_start or start_time >= existing_end):
            return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    # add booking to database
    booking_collection.insert_one({
        'room_name': room_name,
        'date': date,
        'start_time': start_time,
        'end_time': end_time,
        'user_email': user_token['email']
    })

    return RedirectResponse('/', status_code=status.HTTP_302_FOUND)


@app.post('/delete-booking', response_class=RedirectResponse)
async def deleteBooking(request: Request):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    form = await request.form()
    booking_id = form['booking_id']

    # only delete if this booking belongs to the current user
    booking = booking_collection.find_one({
        '_id': ObjectId(booking_id),
        'user_email': user_token['email']
    })

    if booking:
        booking_collection.delete_one({'_id': ObjectId(booking_id)})

    return RedirectResponse('/', status_code=status.HTTP_302_FOUND)


@app.get('/edit-booking/{booking_id}', response_class=HTMLResponse)
async def editBooking(request: Request, booking_id: str):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    # get the booking
    booking = booking_collection.find_one({
        '_id': ObjectId(booking_id),
        'user_email': user_token['email']
    })

    if not booking:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse('edit_booking.html', {
        'request': request,
        'user_token': user_token,
        'booking': booking
    })


@app.post('/edit-booking/{booking_id}', response_class=RedirectResponse)
async def editBookingPost(request: Request, booking_id: str):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    form = await request.form()
    date = form['date']
    start_time = form['start_time']
    end_time = form['end_time']

    # get current booking to know the room name
    booking = booking_collection.find_one({'_id': ObjectId(booking_id)})
    room_name = booking['room_name']

    # check for clashing bookings excluding current booking
    existing_bookings = booking_collection.find({
        'room_name': room_name,
        'date': date,
        '_id': {'$ne': ObjectId(booking_id)}
    })

    for existing in existing_bookings:
        existing_start = existing['start_time']
        existing_end = existing['end_time']
        if not (end_time <= existing_start or start_time >= existing_end):
            return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    # update the booking
    booking_collection.update_one(
        {'_id': ObjectId(booking_id)},
        {'$set': {
            'date': date,
            'start_time': start_time,
            'end_time': end_time
        }}
    )

    return RedirectResponse('/', status_code=status.HTTP_302_FOUND)
