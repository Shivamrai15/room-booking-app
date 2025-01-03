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

    user_token = validateFirebaseToken(id_token)

    rooms, error_message = await getRooms()

    if not user_token:
        return templets.TemplateResponse('main.html', { 'request' : request, 'user_token' : None , 'error_message' : error_message, 'user_info': None, "rooms" : rooms })
    
    bookings, error_message = await getBookingsByEmail(user_token["email"])
    roomId = request.query_params.get('roomId')
    if roomId :
        specific_bookings = await getBookingsOfSpecificRoom(user_token["email"], roomId)
        print(specific_bookings)
        return templets.TemplateResponse('main.html', { 'request' : request, 'user_token' : user_token , 'error_message' : error_message, "rooms" : rooms, "bookings" : bookings, "specific_bookings": specific_bookings })

    return templets.TemplateResponse('main.html', { 'request' : request, 'user_token' : user_token , 'error_message' : error_message, "rooms" : rooms, "bookings" : bookings , "specific_bookings" : None })



def validateFirebaseToken(id_token):
    if not id_token:
        return None
    
    user_token = None
    try:
        user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
    except ValueError as err:
        print(str(err))
    
    return  user_token

async def getRooms( ):
    error_message = ""
    rooms = []
    try : 
        ref = firestore_db.collection('rooms')
        snapshot = ref.get()
        for room in snapshot:
            rooms.append(
                {
                    "id" : room.id,
                    "createdAt" : room.create_time,
                    "name" : room.get("name"),
                    "number" : room.get("number"),
                    "createdBy" : room.get("createdBy")

                }
            )
    except :
        error_message = "Internal server error"
    return rooms, error_message

async def getBookingsOfSpecificRoom(email:str, roomId:str):
    bookings = []
    ref = firestore_db.collection('bookings').where("booked_by", "==", email).where("roomId", "==" , roomId)
    snapshot = ref.get()
    for booking in snapshot:
        room = firestore_db.collection('rooms').document(booking.get("roomId")).get().to_dict()
        bookings.append(
            {
                "id" : booking.id,
                "booked_by" : booking.get("booked_by"),
                "date" : datetime.fromtimestamp(booking.get("booking_date")).date(),
                "room" : room.get("name"),
                "number" : room.get("number"),
                "start" : booking.get("start"),
                "end" : booking.get("end")
            }
        )
    return bookings


async def getBookingsByEmail( email: str ):
    error_message = ""
    bookings = []
    try:
        ref = firestore_db.collection('bookings').where("booked_by", "==", email)
        snapshot = ref.get()
        for booking in snapshot:
            room = firestore_db.collection('rooms').document(booking.get("roomId")).get().to_dict()
            bookings.append(
                {
                    "id" : booking.id,
                    "booked_by" : booking.get("booked_by"),
                    "date" : datetime.fromtimestamp(booking.get("booking_date")).date(),
                    "room" : room.get("name"),
                    "number" : room.get("number"),
                    "start" : booking.get("start"),
                    "end" : booking.get("end")
                }
            )
    except:
        error_message = "Internal server error"
    
    if len(bookings) == 0:
        return None, error_message

    return bookings, error_message 
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
    existingRoom = firestore_db.collection('rooms').where("name", "==", room_data.get("name")).where("number", "==", room_data.get("number")).get()
    if len(existingRoom) == 0:
        room = firestore_db.collection('rooms').document().set(room_data)
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    
# -------------------------------------------------------------------------------------------------#


@app.delete("/delete-room/{roomId}")
async def deleteRoom( request : Request, roomId: str ):
    id_token =  request.cookies.get("token")

    user_token = validateFirebaseToken(id_token)
    if not user_token:
        raise HTTPException(status_code=400, detail="User not alllowed to delete the room")
    
    bookings = firestore_db.collection("bookings").where("roomId", "==", roomId).get()
    if len(bookings) > 0:
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
@app.get("/available-rooms/{date}/{entryTime}/{checkoutTime}", response_class=JSONResponse)
async def checkRoomAvailability(request: Request, date:str, entryTime:str, checkoutTime:str ):
    id_token =  request.cookies.get("token")

    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/')
    
    startTime = int(entryTime)
    endTime = int(checkoutTime)
    dateObj = datetime.strptime(date, "%Y-%m-%d").date()
    currentDate = datetime.today().date()
    
    if dateObj < currentDate :
        return JSONResponse([], status_code=200)
    
    if startTime >= endTime:
        return JSONResponse([], status_code=200)
    
    available_rooms = []
    booked_rooms = []
    clashedRooms = set()
    bookings = firestore_db.collection('bookings').where("booking_date", "==", datetime.strptime(date, "%Y-%m-%d").timestamp()).get()
    for booked_room in bookings:
        booked_rooms.append(booked_room.to_dict())

    for booking in booked_rooms:
        booking_start = int(booking["start"])
        booking_end = int(booking["end"])

        if (startTime >= booking_start and startTime < booking_end) or \
           (endTime > booking_start and endTime <= booking_end) or \
           (startTime <= booking_start and endTime >= booking_end):
            clashedRooms.add(booking["roomId"])

    all_rooms = firestore_db.collection("rooms").get()

    for room_doc in all_rooms:
        room_data = room_doc.to_dict()
        room_id = room_doc.id
        if room_id not in clashedRooms:
            available_rooms.append({"id": room_id, "name": f"{room_data.get('name')} {room_data.get('number')}"})

    return JSONResponse(available_rooms, status_code=200)
# -------------------------------------------------------------------------------------------------#



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
        "start" : form["booking-start"],
        "end" : form["booking-end"],
        "roomId" : form["select-room"]
    }

    firestore_db.collection("bookings").document().set(booking_data)
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
# -------------------------------------------------------------------------------------------------#


@app.delete("/delete-booking/{bookingId}")
async def deleteBooking( request : Request, bookingId: str ):
    id_token =  request.cookies.get("token")

    user_token = validateFirebaseToken(id_token)
    if not user_token:
        raise HTTPException(status_code=400, detail="User not alllowed to delete the booking")
    
    booking = firestore_db.collection("bookings").document(bookingId)
    
    if ( user_token["email"] != booking.get().to_dict().get("booked_by")) :
        raise HTTPException(status_code=400, detail="User not alllowed to delete the booking")
    
    booking.delete()
    return JSONResponse({ "success" : True }, status_code=200)
# -------------------------------------------------------------------------------------------------#


@app.get("/room/bookings/{roomId}", response_class=HTMLResponse)
async def roomDetails(request: Request, roomId:str):

    bookings = []
    filter_date = request.query_params.get('date')
    if ( filter_date ) :
        timestamp = datetime.strptime(filter_date, "%Y-%m-%d").timestamp()
        booking_obj = firestore_db.collection('bookings').where("roomId", "==", roomId).where("booking_date", "==", timestamp).get()
    else :
        booking_obj = firestore_db.collection('bookings').where("roomId", "==", roomId).get()
    
    if len(booking_obj) == 0 :
        return templets.TemplateResponse('bookings.html', { 'request' : request, 'error' : None, 'bookings': None, "roomId" : roomId })

    for booking in booking_obj:
        bookings.append(
                { 
                    "id" : booking.id,
                    "booked_by" : booking.get("booked_by"),
                    "date" : datetime.fromtimestamp(booking.get("booking_date")).date(),
                    "start" : booking.get("start"),
                    "end" : booking.get("end"),
                    "booked_by" : booking.get("booked_by")
                }
            )
    return templets.TemplateResponse('bookings.html', { 'request' : request, 'error' : None, "roomId" : roomId ,'bookings': bookings})

# -------------------------------------------------------------------------------------------------#

@app.get("/update-booking/{bookingId}", response_class=HTMLResponse)
async def updateBooking(request : Request, bookingId : str):
    id_token =  request.cookies.get("token")

    user_token = validateFirebaseToken(id_token)
    if not user_token:
        raise HTTPException(status_code=400, detail="User not alllowed to edit the booking")

    data = firestore_db.collection('bookings').document(bookingId).get().to_dict()
    room = firestore_db.collection('rooms').document(data.get('roomId')).get()
    formatted_data = {
        'date' : datetime.fromtimestamp(data.get("booking_date")).date(),
        'start' : int(data.get("start")),
        'end' : int(data.get("end")),
        'room' : f'{room.to_dict().get("name")} {room.to_dict().get("number")}',
        'roomId' : room.id,
        'id' : bookingId
    }

    return templets.TemplateResponse('update.html', { 'request' : request, 'error' : None, "data": formatted_data })
# -------------------------------------------------------------------------------------------------#


@app.post("/update-booking/{bookingId}", response_class=RedirectResponse)
async def updateBooking(request : Request, bookingId : str):
    id_token =  request.cookies.get("token")

    user_token = validateFirebaseToken(id_token)
    if not user_token:
        raise HTTPException(status_code=400, detail="User not alllowed to edit the booking")
    
    form = await request.form()

    booking_data = {
        "booked_by" : user_token["email"],
        "booking_date" : datetime.strptime(form["booking-date"], "%Y-%m-%d").timestamp(),
        "start" : form["booking-start"],
        "end" : form["booking-end"],
        "roomId" : form["select-room"]
    }

    booking = firestore_db.collection('bookings').document(bookingId)
    booking.set(booking_data)
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
# -------------------------------------------------------------------------------------------------#
