import json

from fastapi import FastAPI, HTTPException
import datetime
from typing import Optional
import requests
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from modelValidate import calc
from py_db import prices, prices_d, models, cronLogs, modelTypes, cryptos
from fastapi.middleware.cors import CORSMiddleware
from bson.objectid import ObjectId
from convert import convert
from pydantic import BaseModel
from pred import predNext


origins = ["*"]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/')
async def testConn():
    return 1

@app.get('/prices/')
async def getSymbolPrice(symbol: Optional[str] = None, limit: Optional[int] = 240, interval: Optional[str] = '1h'):

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
async def getModelPath(symbol: Optional[str], interval: Optional[str] = '1h'):

    query = {"symbol": f'{symbol}',"interval": f'{interval}'}
    print(query)
    list_cur = list(models.find(query).sort('lastMAPE', 1))

    res = json.dumps(list_cur, default=str)
    json_compatible_item_data = jsonable_encoder(res)
    data = json.loads(json_compatible_item_data)

    return JSONResponse(content=data, status_code=200)

@app.get('/validates/{id}')
async def getModelResults(id):
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

    modelJSON = json.dumps(model, default=str)
    data = json.loads(modelJSON)
    res = calc(data.get('symbol'), data.get('interval'), data.get('fileName'))
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
async def updatePriceData(symbol: Optional[str], interval: Optional[str] = '1h'):

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
def writeHCronLogs(event: Optional[str]):
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
def writeHCronLogs(event: Optional[str]):
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
def getLastOpenTime(symbol: Optional[str] = None, interval: Optional[str] = '1h', openTime: Optional[int] = 0):

    query = {"Symbol": f'{symbol}'}
    if interval == '1h':
        price = list(prices.find(query).sort("OpenTime", -1).limit(1))
    else:
        price = list(prices_d.find(query).sort("OpenTime", -1).limit(1))
    res = price[0]['OpenTime']
    if openTime>res:
        res=openTime
    return res

@app.get('/modelTypes/{id}')
async def getModelTypes(id):
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
async def getCryptos():

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
async def getCryptoInfos(id):
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
async def getCryptoInfos(symbol:str):
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
async def updateDefaultModel(id: str, model: Model):
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
async def predNextPrice(id: str):
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

    modelJSON = json.dumps(model, default=str)
    data = json.loads(modelJSON)
    res = predNext(data.get('symbol'), data.get('interval'), data.get('fileName'))

    resJSON = {}
    resJSON['nextVal'] = res
    jsonstr = json.dumps(resJSON, default=str)
    json_compatible_item_data = jsonable_encoder(jsonstr)
    data = json.loads(json_compatible_item_data)

    return JSONResponse(content=data, status_code=200)