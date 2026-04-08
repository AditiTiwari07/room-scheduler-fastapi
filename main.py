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
from datetime import datetime, timedelta

# Connect to MongoDB
uri = "mongodb+srv://aditiuser:Shubh123@cluster0.6opbt4j.mongodb.net/room_scheduler?retryWrites=true&w=majority"
client = MongoClient(
    uri,
    server_api=ServerApi('1'),
    serverSelectionTimeoutMS=30000,
    connectTimeoutMS=30000,
    socketTimeoutMS=30000
)

# Ping to confirm connection
try:
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(e)

# Define the app
app = FastAPI()


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
    # validate firebase token 
    if not id_token:
        return None
    user_token = None
    try:
        user_token = google.oauth2.id_token.verify_firebase_token(
            id_token, firebase_request_adapter)
    except ValueError as err:
        print(str(err))
    return user_token


def getOrCreateDay(room_id, room_name, date_str):
    # get existing day document 
    day = day_collection.find_one({
        'room_name': room_name,
        'date': date_str
    })
    if not day:
        # create new day document
        day_dict = {
            'room_id': room_id,
            'room_name': room_name,
            'date': date_str,
            'booking_list': []
        }
        result = day_collection.insert_one(day_dict)
        # link day to room
        room_collection.update_one(
            {'_id': room_id},
            {'$push': {'day_list': result.inserted_id}}
        )
        day = day_collection.find_one({'_id': result.inserted_id})
    return day


@app.get('/', response_class=HTMLResponse)
async def root(request: Request):
    
    id_token = request.cookies.get('token')
    error_message = request.query_params.get('error', '')
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
    # add a new room to the database
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    form = await request.form()
    room_name = form['room_name']

    # check if room already exists
    existing_room = room_collection.find_one({'name': room_name})
    if existing_room:
        return RedirectResponse('/?error=Room+already+exists', status_code=status.HTTP_302_FOUND)

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

    # validate end time is after start time
    if end_time <= start_time:
        return RedirectResponse('/?error=End+time+must+be+after+start+time', status_code=status.HTTP_302_FOUND)

    # get the room
    room = room_collection.find_one({'name': room_name})
    if not room:
        return RedirectResponse('/?error=Room+not+found', status_code=status.HTTP_302_FOUND)

    # get or create day document
    day = getOrCreateDay(room['_id'], room_name, date)

    # check for clashing bookings on this day
    for booking_id in day['booking_list']:
        existing = booking_collection.find_one({'_id': booking_id})
        if existing:
            existing_start = existing['start_time']
            existing_end = existing['end_time']
            if not (end_time <= existing_start or start_time >= existing_end):
                return RedirectResponse('/?error=Room+already+booked+for+this+time', status_code=status.HTTP_302_FOUND)

    # create booking document
    booking_result = booking_collection.insert_one({
        'room_name': room_name,
        'room_id': room['_id'],
        'day_id': day['_id'],
        'date': date,
        'start_time': start_time,
        'end_time': end_time,
        'user_email': user_token['email']
    })

    # link booking to day
    day_collection.update_one(
        {'_id': day['_id']},
        {'$push': {'booking_list': booking_result.inserted_id}}
    )

    return RedirectResponse('/', status_code=status.HTTP_302_FOUND)


@app.post('/delete-booking', response_class=RedirectResponse)
async def deleteBooking(request: Request):
    # delete a booking 
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
        # remove booking from day's booking list
        day_collection.update_one(
            {'_id': booking['day_id']},
            {'$pull': {'booking_list': booking['_id']}}
        )
        # delete the booking
        booking_collection.delete_one({'_id': ObjectId(booking_id)})

    return RedirectResponse('/', status_code=status.HTTP_302_FOUND)


@app.get('/edit-booking/{booking_id}', response_class=HTMLResponse)
async def editBooking(request: Request, booking_id: str):
    
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

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
    # update a booking with new date and time
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    form = await request.form()
    date = form['date']
    start_time = form['start_time']
    end_time = form['end_time']

    # validate end time is after start time
    if end_time <= start_time:
        return RedirectResponse('/?error=End+time+must+be+after+start+time', status_code=status.HTTP_302_FOUND)

    # get current booking
    booking = booking_collection.find_one({'_id': ObjectId(booking_id)})
    room_name = booking['room_name']
    room = room_collection.find_one({'name': room_name})

    # get or create day for new date
    day = getOrCreateDay(room['_id'], room_name, date)

    # check for clashing bookings excluding current booking
    for bid in day['booking_list']:
        if bid == ObjectId(booking_id):
            continue
        existing = booking_collection.find_one({'_id': bid})
        if existing:
            existing_start = existing['start_time']
            existing_end = existing['end_time']
            if not (end_time <= existing_start or start_time >= existing_end):
                return RedirectResponse('/?error=Room+already+booked+for+this+time', status_code=status.HTTP_302_FOUND)

    # remove booking from old day
    day_collection.update_one(
        {'_id': booking['day_id']},
        {'$pull': {'booking_list': ObjectId(booking_id)}}
    )

    # add booking to new day
    day_collection.update_one(
        {'_id': day['_id']},
        {'$push': {'booking_list': ObjectId(booking_id)}}
    )

    # update the booking
    booking_collection.update_one(
        {'_id': ObjectId(booking_id)},
        {'$set': {
            'date': date,
            'day_id': day['_id'],
            'start_time': start_time,
            'end_time': end_time
        }}
    )

    return RedirectResponse('/', status_code=status.HTTP_302_FOUND)


@app.post('/delete-room', response_class=RedirectResponse)
async def deleteRoom(request: Request):
    # delete a room 
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    form = await request.form()
    room_name = form['room_name']

    # check if room was created by this user
    room = room_collection.find_one({
        'name': room_name,
        'created_by': user_token['email']
    })

    if not room:
        return RedirectResponse('/?error=You+can+only+delete+rooms+you+created', status_code=status.HTTP_302_FOUND)

    # check if room has any bookings
    existing_bookings = booking_collection.find_one({'room_name': room_name})
    if existing_bookings:
        return RedirectResponse('/?error=Cannot+delete+room+with+existing+bookings', status_code=status.HTTP_302_FOUND)

    # delete all day documents for this room
    day_collection.delete_many({'room_id': room['_id']})

    # delete the room
    room_collection.delete_one({'name': room_name})

    return RedirectResponse('/', status_code=status.HTTP_302_FOUND)


@app.post('/filter-bookings', response_class=HTMLResponse)
async def filterBookings(request: Request):
   
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    form = await request.form()
    date = form['date']

    rooms = []
    for room in room_collection.find():
        rooms.append(room)

    bookings = []
    for booking in booking_collection.find({'user_email': user_token['email']}):
        bookings.append(booking)

    
    filtered_bookings = []
    for booking in booking_collection.find({'date': date}):
        filtered_bookings.append(booking)

    filtered_bookings.sort(key=lambda x: x['start_time'])

    return templates.TemplateResponse('index.html', {
        'request': request,
        'user_token': user_token,
        'error_message': '',
        'rooms': rooms,
        'bookings': bookings,
        'filtered_bookings': filtered_bookings
    })


@app.get('/room/{room_name}', response_class=HTMLResponse)
async def viewRoom(request: Request, room_name: str):
    
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    
    bookings = []
    for booking in booking_collection.find({'room_name': room_name}):
        bookings.append(booking)
    bookings.sort(key=lambda x: (x['date'], x['start_time']))

    
    my_bookings = []
    for booking in booking_collection.find({
        'room_name': room_name,
        'user_email': user_token['email']
    }):
        my_bookings.append(booking)
    my_bookings.sort(key=lambda x: (x['date'], x['start_time']))

    
    today = datetime.now().date()
    occupancy = []
    earliest_free = []
    calendar_data = []

    for i in range(5):
        day = today + timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')

        total_minutes = 540
        booked_minutes = 0

        day_bookings = list(booking_collection.find({
            'room_name': room_name,
            'date': day_str
        }))
        day_bookings.sort(key=lambda x: x['start_time'])

        for b in day_bookings:
            start_parts = b['start_time'].split(':')
            end_parts = b['end_time'].split(':')
            start_mins = int(start_parts[0]) * 60 + int(start_parts[1])
            end_mins = int(end_parts[0]) * 60 + int(end_parts[1])
            start_mins = max(start_mins, 540)
            end_mins = min(end_mins, 1080)
            if end_mins > start_mins:
                booked_minutes += end_mins - start_mins

        percentage = round((booked_minutes / total_minutes) * 100, 1)
        occupancy.append({'date': day_str, 'percentage': percentage})

        # find earliest free time
        free_from = 540
        for b in day_bookings:
            start_parts = b['start_time'].split(':')
            end_parts = b['end_time'].split(':')
            start_mins = int(start_parts[0]) * 60 + int(start_parts[1])
            end_mins = int(end_parts[0]) * 60 + int(end_parts[1])
            if start_mins <= free_from:
                free_from = max(free_from, end_mins)

        if free_from < 1080:
            free_hour = free_from // 60
            free_min = free_from % 60
            earliest_free.append({
                'date': day_str,
                'time': f'{free_hour:02d}:{free_min:02d}'
            })
        else:
            earliest_free.append({
                'date': day_str,
                'time': 'No free time available'
            })

        # build calendar slots for day
        slots = []
        for b in day_bookings:
            start_parts = b['start_time'].split(':')
            end_parts = b['end_time'].split(':')
            start_mins = int(start_parts[0]) * 60 + int(start_parts[1])
            end_mins = int(end_parts[0]) * 60 + int(end_parts[1])
            top = start_mins - 540
            height = end_mins - start_mins
            slots.append({
                'start': b['start_time'],
                'end': b['end_time'],
                'top': max(top, 0),
                'height': max(height, 10)
            })

        calendar_data.append({
            'date': day_str,
            'slots': slots
        })

    return templates.TemplateResponse('room.html', {
        'request': request,
        'user_token': user_token,
        'room_name': room_name,
        'bookings': bookings,
        'my_bookings': my_bookings,
        'occupancy': occupancy,
        'earliest_free': earliest_free,
        'calendar_data': calendar_data
    })
@app.post('/my-room-bookings', response_class=HTMLResponse)
async def myRoomBookings(request: Request):
    # show all bookings the current user 
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    form = await request.form()
    room_name = form['room_name']

    # get all rooms
    rooms = []
    for room in room_collection.find():
        rooms.append(room)

    # get all bookings for current user
    bookings = []
    for booking in booking_collection.find({'user_email': user_token['email']}):
        bookings.append(booking)

    # get bookings for this specific room by current user
    room_bookings = []
    for booking in booking_collection.find({
        'room_name': room_name,
        'user_email': user_token['email']
    }):
        room_bookings.append(booking)

    room_bookings.sort(key=lambda x: (x['date'], x['start_time']))

    return templates.TemplateResponse('index.html', {
        'request': request,
        'user_token': user_token,
        'error_message': '',
        'rooms': rooms,
        'bookings': bookings,
        'room_bookings': room_bookings
    })