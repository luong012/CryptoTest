import json

from fastapi import FastAPI, HTTPException, status, Depends
import datetime
from datetime import timedelta
from typing import Optional
import requests
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from modelValidate import calc
from py_db import prices, prices_d, models, cronLogs, modelTypes, cryptos, users
from fastapi.middleware.cors import CORSMiddleware
from bson.objectid import ObjectId
from convert import convert
from pydantic import BaseModel
from pred import predNext

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext


SECRET_KEY = "0e5f57fdf004e117296a9c6c4a2f1b9f7ed6d09e24419b48ef64edfb612505db"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 5000

origins = ["*"]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(username: str):
    query = {"username": username}
    user = users.find_one(query)
    return user

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user['hashed_password']):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user['disabled']:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@app.get('/')
async def testConn():
    return 1

class RegUser(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None

@app.post('/auth/register/')
def register(user: RegUser):
    existed_user = get_user(user.username)
    if existed_user:
        return JSONResponse(content=json.loads(json.dumps({"message": "Username already exists"})), status_code=400)

    hashed_password = get_password_hash(user.password)
    username = user.username
    email = user.email
    full_name = user.full_name
    disabled = False
    user_data = {
        "username": username,
        "hashed_password": hashed_password,
        "email": email,
        "fullname": full_name,
        "disabled": disabled
    }

    try:
        user = users.insert_one(user_data)
    except:
        return JSONResponse(content=json.loads(json.dumps({"message": "Cannot create user"})), status_code=400)

    return JSONResponse(content=json.loads(json.dumps({"message": "success"})), status_code=201)


@app.post('/auth/login')
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(  form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['username']}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@app.get("/users/me/items/")
async def read_own_items(current_user: User = Depends(get_current_active_user)):
    return [{"item_id": "Foo", "owner": current_user.username}]

@app.get('/prices/')
async def get_symbol_price(symbol: Optional[str] = None, limit: Optional[int] = 240, interval: Optional[str] = '1h'):

    #LIMIT MUST BE A POSITIVE INT
    if limit<1:
        raise HTTPException(status_code=400, detail="Bad Request")

    query = ""

    if symbol:
        query = {"Symbol" : f'{symbol}'}

    #PRICES COLLECTION FOR HOUR INTERVAL. PRICES_D COLLECTION FOR DATE INTERVAL
    if interval == '1d':
        list_cur = list(prices_d.find(query).sort('CloseTime', -1).limit(limit))
        if len(list_cur) < 1:
            raise HTTPException(status_code=400, detail="Bad Request")
    else:
        list_cur = list(prices.find(query).sort('CloseTime', -1).limit(limit))
        if len(list_cur) < 1:
            raise HTTPException(status_code=400, detail="Bad Request")

    #REVERSE TO MAEK DATE ASC
    list_cur.reverse()
    res = json.dumps(list_cur, default=str)
    json_compatible_item_data = jsonable_encoder(res)
    data = json.loads(json_compatible_item_data)

    return JSONResponse(content=data, status_code=200)

@app.get('/models/')
async def get_model_path(symbol: Optional[str], interval: Optional[str] = '1h', outputWindows: Optional[int] = 1):

    modelTypeQuery = {"outputWindows": outputWindows}
    list_md_types = list(modelTypes.find(modelTypeQuery))

    list_md_types_id = [str(r['_id']) for r in list_md_types]

    query = {"symbol": f'{symbol}',"interval": f'{interval}', "modelType": {"$in": list_md_types_id}}
    list_cur = list(models.find(query).sort('lastMAPE', 1))

    res = json.dumps(list_cur, default=str)
    json_compatible_item_data = jsonable_encoder(res)
    data = json.loads(json_compatible_item_data)

    return JSONResponse(content=data, status_code=200)

@app.get('/validates/{id}')
async def get_model_results(id):
    try:
        query = {"_id": ObjectId(id)}
    except:
        return JSONResponse(content="Not Found", status_code=404)
    try:
        model = models.find_one(query)
    except:
        return JSONResponse(status_code=404)
    if model is None:
        return JSONResponse(status_code=404)

    try:
        typeQuery = {"_id": ObjectId(str(model['modelType']))}
    except:
        return JSONResponse(status_code=404)
    try:
        modelType = modelTypes.find_one(typeQuery)
    except:
        return JSONResponse(status_code=404)

    modelJSON = json.dumps(model, default=str)
    data = json.loads(modelJSON)
    res = calc(data.get('symbol'), data.get('interval'), data.get('fileName'), modelType['outputWindows'])
    updateContent = {}
    if data.get('mapeArr') is None:
        mapeLs = list()
        mapeLs.append(res['mape'])
        updateVal = {"mapeArr": mapeLs, "lastMAPE": res['mape'], "avgMAPE": res['mape']}
        updateContent['$set']=updateVal
    else:
        mapeLs = list(data.get('mapeArr'))
        mapeLs.append(res['mape'])
        updateVal = {"mapeArr": mapeLs, "lastMAPE": res['mape'], "avgMAPE": sum(mapeLs)/len(mapeLs)}
        updateContent['$set'] = updateVal
    try:
        models.update_one(query, updateContent)
    except:
        return JSONResponse(status_code=500)


    return res

@app.post('/updates')
async def update_price_data(symbol: Optional[str], interval: Optional[str] = '1h'):

    query = {"Symbol": f'{symbol}'}
    if interval=='1h':
        price = list(prices.find(query).sort("CloseTime", -1).limit(1))
    else:
        price = list(prices_d.find(query).sort("CloseTime", -1).limit(1))
    startTime = price[0]['CloseTime']

    url = f'https://api1.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=1000&startTime={startTime}'
    result = requests.get(url)
    apiJSON = result.json()
    res = {}
    res = convert(symbol, apiJSON)
    if interval=="1h":
        try:
            results = prices.insert_many(res)
            print('ok')
        except:
            print('err')
            JSONResponse(status_code=500)
    else:
        try:
            results = prices_d.insert_many(res)
            print('ok')
        except:
            print('err')
            JSONResponse(status_code=500)

    jsonstr = json.dumps(res, default=str)
    json_compatible_item_data = jsonable_encoder(jsonstr)
    data = json.loads(json_compatible_item_data)

    return JSONResponse(content=data, status_code=201)

@app.post('/hourlyCrons')
def write_hourly_cron_logs(event: Optional[str]):
    log = {}
    log["event"] = ""
    if event=="start":
        log["event"] = "Hourly cronjob started"
    if event=="stop":
        log["event"] = "Hourly cronjob stopped"
    log["executedTime"] = str(datetime.datetime.now())
    try:
        res = cronLogs.insert_one(log)
        print('Sent')
    except:
        print('Err')
        JSONResponse(status_code=500)

    jsonstr = json.dumps(log, default=str)
    json_compatible_item_data = jsonable_encoder(jsonstr)
    data = json.loads(json_compatible_item_data)
    return JSONResponse(content=data, status_code=201)

@app.post('/dailyCrons')
def write_daily_cron_logs(event: Optional[str]):
    log = {}
    log["event"] = ""
    if event=="start":
        log["event"] = "Daily cronjob started"
    if event=="stop":
        log["event"] = "Daily cronjob stopped"
    log["executedTime"] = str(datetime.datetime.now())
    try:
        res = cronLogs.insert_one(log)
        print('Sent')
    except:
        print('Err')
        JSONResponse(status_code=500)

    jsonstr = json.dumps(log, default=str)
    json_compatible_item_data = jsonable_encoder(jsonstr)
    data = json.loads(json_compatible_item_data)
    return JSONResponse(content=data, status_code=201)

@app.get('/times/')
def get_last_close_time_value(symbol: Optional[str] = None, interval: Optional[str] = '1h', closeTime: Optional[int] = 0):

    query = {"Symbol": f'{symbol}'}
    if interval == '1h':
        price = list(prices.find(query).sort("CloseTime", -1).limit(1))
    else:
        price = list(prices_d.find(query).sort("CloseTime", -1).limit(1))
    res = price[0]['CloseTime']
    if closeTime>res:
        res=closeTime
    return res

@app.get('/modelTypes/{id}')
async def get_model_types(id):
    try:
        query = {"_id": ObjectId(id)}
    except:
        return JSONResponse(content="Not Found", status_code=404)
    try:
        modelType = modelTypes.find_one(query)
    except:
        return JSONResponse(status_code=404)
    if modelType is None:
        return JSONResponse(status_code=404)

    jsonstr = json.dumps(modelType, default=str)
    json_compatible_item_data = jsonable_encoder(jsonstr)
    data = json.loads(json_compatible_item_data)
    return JSONResponse(content=data, status_code=200)

@app.get('/cryptos/all')
async def get_cryptos():

    try:
        cryptoLs = list(cryptos.find())
    except:
        return JSONResponse(status_code=404)
    if cryptoLs is None:
        return JSONResponse(status_code=404)

    jsonstr = json.dumps(cryptoLs, default=str)
    json_compatible_item_data = jsonable_encoder(jsonstr)
    data = json.loads(json_compatible_item_data)
    return JSONResponse(content=data, status_code=200)

@app.get('/cryptos/{id}')
async def get_crypto_infos(id):
    try:
        query = {"_id": ObjectId(id)}
    except:
        return JSONResponse(content="Not Found", status_code=404)
    try:
        crypto = cryptos.find_one(query)
    except:
        return JSONResponse(status_code=404)
    if crypto is None:
        return JSONResponse(status_code=404)

    jsonstr = json.dumps(crypto, default=str)
    json_compatible_item_data = jsonable_encoder(jsonstr)
    data = json.loads(json_compatible_item_data)
    return JSONResponse(content=data, status_code=200)

@app.get('/cryptos/')
async def get_crypto_infos(symbol:str):
    query = {"altSymbol": symbol}
    try:
        crypto = cryptos.find_one(query)
    except:
        return JSONResponse(status_code=404)
    if crypto is None:
        return JSONResponse(status_code=404)

    jsonstr = json.dumps(crypto, default=str)
    json_compatible_item_data = jsonable_encoder(jsonstr)
    data = json.loads(json_compatible_item_data)
    return JSONResponse(content=data, status_code=200)

class Model(BaseModel):
    interval: str
    defaultModel: str


@app.put('/cryptos/{id}')
async def update_default_model(id: str, model: Model):
    try:
        query = {"_id": ObjectId(id)}
    except:
        return JSONResponse(content="Not Found", status_code=404)

    try:
        crypto = cryptos.find_one(query)
    except:
        return JSONResponse(content="Not Found", status_code=404)

    if crypto is None:
        return JSONResponse(content="Not Found", status_code=404)

    if model.interval!='1h' and model.interval!='1d':
        return JSONResponse(content="Bad Request", status_code=400)

    updateContent = {}
    updateVal = {f'defaultModel.{model.interval}': model.defaultModel}
    updateContent['$set'] = updateVal

    try:
        crypto = cryptos.update_one(query, updateContent)
    except:
        return JSONResponse(status_code=500)

    return JSONResponse(content='success', status_code=200)

@app.get('/predicts/{id}')
async def pred_next_price(id: str):
    #get model info
    try:
        query = {"_id": ObjectId(id)}
    except:
        return JSONResponse(content="Not Found", status_code=404)
    try:
        model = models.find_one(query)
    except:
        return JSONResponse(status_code=404)
    if model is None:
        return JSONResponse(status_code=404)

    # get numbers of model's output windows
    try:
        typeQuery = {"_id": ObjectId(model['modelType'])}
    except:
        return JSONResponse(content="Not Found", status_code=404)

    try:
        modelType = modelTypes.find_one(typeQuery)
    except:
        return JSONResponse(status_code=404)


    modelJSON = json.dumps(model, default=str)
    data = json.loads(modelJSON)
    res = predNext(data.get('symbol'), data.get('interval'), data.get('fileName'), modelType['outputWindows'])

    resJSON = {}
    resJSON['prediction'] = res
    jsonstr = json.dumps(resJSON, default=str)
    json_compatible_item_data = jsonable_encoder(jsonstr)
    data = json.loads(json_compatible_item_data)

    return JSONResponse(content=data, status_code=200)