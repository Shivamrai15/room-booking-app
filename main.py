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
    return templets.TemplateResponse('main.html', { 'request' : request, 'user_token' : user_token , 'error_message' : error_message, 'user_info': user.get(), })



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


@app.get("/login", response_class=HTMLResponse)
async def login(request : Request):
    id_token =  request.cookies.get("token")

    user_token = validateFirebaseToken(id_token)
    if not user_token:
       return templets.TemplateResponse('login.html', { 'request' : request }) 
    return RedirectResponse('/')
# -------------------------------------------------------------------------------------------------#

