from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.oauth2.id_token
from google.auth.transport import requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import starlette.status as status
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB
uri = os.getenv("MONGO_URI")
client = MongoClient(uri, server_api=ServerApi('1'))

# confirm connection
try:
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(e)

# Define the app
app = FastAPI()

# Open db and collections
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

    return templates.TemplateResponse('index.html', {
        'request': request,
        'user_token': user_token,
        'error_message': error_message,
        'rooms': rooms
    })


@app.post('/add-room', response_class=RedirectResponse)
async def addRoom(request: Request):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    form = await request.form()
    room_name = form['room_name']

    # check if room exists
    existing_room = room_collection.find_one({'name': room_name})
    if existing_room:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    # add room to db
    room_collection.insert_one({
        'name': room_name,
        'created_by': user_token['email'],
        'day_list': []
    })

    return RedirectResponse('/', status_code=status.HTTP_302_FOUND)