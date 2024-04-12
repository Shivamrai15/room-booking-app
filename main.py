from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.auth
import google.oauth2.id_token
from google.auth.transport import requests
from google.cloud import firestore
import starlette.status as status
from datetime import datetime

app = FastAPI()

firestore_db = firestore.Client()
firebase_request_adapter = requests.Request()

app.mount('/static', StaticFiles(directory='static'), name='static' )
templets = Jinja2Templates(directory='templates')


@app.get("/", response_class=HTMLResponse)
async def root( request : Request ) :

    id_token = request.cookies.get("token")
    error_message = "No error here"
    user_token = None
    user = None

    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return templets.TemplateResponse('main.html', { 'request' : request, 'user_token' : None , 'error_message' : error_message, 'user_info': None })
    
    user = getUser(user_token)
    rooms, error_message = getRoomsByEmail(user_token["email"])
    return templets.TemplateResponse('main.html', { 'request' : request, 'user_token' : user_token , 'error_message' : error_message, 'user_info': user.get(), "rooms" : rooms })



def getUser(user_token) :
    user = firestore_db.collection('users').document(user_token['user_id'])
    if not user.get().exists:
        user_data = {
            'name' : 'No name yet',
            'age' : 0
        }
        firestore_db.collection('users').document(user_token['user_id']).set(user_data)
    return user


def validateFirebaseToken(id_token):
    if not id_token:
        return None
    
    user_token = None
    try:
        user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
    except ValueError as err:
        print(str(err))
    
    return  user_token

def getRoomsByEmail( email: str ):
    error_message = ""
    rooms = []
    try : 
        ref = firestore_db.collection('rooms').where("createdBy", "==", email)
        snapshot = ref.get()
        for room in snapshot:
            rooms.append(
                {
                    "id" : room.id,
                    "createdAt" : room.create_time,
                    "name" : room.get("name"),
                    "number" : room.get("number")

                }
            )
    except :
        error_message = "Internal server error"
    return rooms, error_message
# -------------------------------------------------------------------------------------------------#


@app.get("/login", response_class=HTMLResponse)
async def login(request : Request):
    id_token =  request.cookies.get("token")

    user_token = validateFirebaseToken(id_token)
    if not user_token:
       return templets.TemplateResponse('login.html', { 'request' : request }) 
    return RedirectResponse('/')
# -------------------------------------------------------------------------------------------------#



@app.get("/create-room", response_class=HTMLResponse )
async def createRoom(request : Request):
    id_token =  request.cookies.get("token")

    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/')
    return templets.TemplateResponse('room.html', { 'request' : request, 'error' : None })
# -------------------------------------------------------------------------------------------------#


@app.post("/create-room", response_class=HTMLResponse)
async def postCreateRoom(request : Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/')

    form = await request.form()

    if (not form['room']) or (not form['room-number']):
        return templets.TemplateResponse('room.html', { 'request' : request, 'error' : "Room name and room number required" })

    room_data = {
        "name" : form["room"],
        "number" : int(form["room-number"]),
        "createdBy" : user_token["email"],
    }
    room = firestore_db.collection('rooms').document().set(room_data)
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    
# -------------------------------------------------------------------------------------------------#


@app.delete("/delete-room/{roomId}")
async def deleteRoom( request : Request, roomId: str ):
    id_token =  request.cookies.get("token")

    user_token = validateFirebaseToken(id_token)
    if not user_token:
        raise HTTPException(status_code=400, detail="User not alllowed to delete the room")
    
    room = firestore_db.collection("rooms").document(roomId)
    
    if ( user_token["email"] != room.get().to_dict().get("createdBy")) :
        raise HTTPException(status_code=400, detail="User not alllowed to delete the room")
    
    room.delete()
    return JSONResponse({ "success" : True }, status_code=200)
    

# -------------------------------------------------------------------------------------------------#


@app.get("/book-room", response_class=HTMLResponse)
async def bookRoom(request: Request):
    id_token =  request.cookies.get("token")

    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/')
    return templets.TemplateResponse('book.html', { 'request' : request, 'error' : None })


# -------------------------------------------------------------------------------------------------#
@app.get("/available-rooms/{date}", response_class=JSONResponse)
async def checkRoomAvailability(request: Request, date:str):
    id_token =  request.cookies.get("token")

    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/')
    
    booked_roomIds = []
    formatted_date = datetime.strptime(date, "%Y-%m-%d").timestamp()
    bookings = firestore_db.collection('bookings').where("booking_date", "==", formatted_date).get()
    for booked_rooms in bookings:
        booked_roomIds.append(booked_rooms.get("roomId"))
    
    available_rooms = []
    all_rooms = firestore_db.collection("rooms").get()

    for room_doc in all_rooms:
        room_data = room_doc.to_dict()
        room_id = room_doc.id
        if room_id not in booked_roomIds:
            available_rooms.append({"id": room_id, "name": f"{room_data.get('name')} {room_data.get('number')}"})

    return JSONResponse(available_rooms, status_code=200)



@app.post("/book-room", response_class=HTMLResponse)
async def bookRoom(request: Request):
    id_token =  request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/')
    
    form = await request.form()
    booking_data = {
        "booked_by" : user_token["email"],
        "booking_date" : datetime.strptime(form["booking-date"], "%Y-%m-%d").timestamp(),
        "roomId" : form["select-room"]
    }

    firestore_db.collection("bookings").document().set(booking_data)
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
