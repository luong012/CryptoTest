import json

from fastapi import FastAPI, HTTPException
from time import time
from typing import Optional
import requests
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from modelPred import calc
from pydantic import BaseModel
from py_db import prices, prices_d, models
from fastapi.middleware.cors import CORSMiddleware
from bson.objectid import ObjectId


origins = ["*"]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# URL = "https://www.bitmex.com/api/v1/trade/bucketed?binSize=1m&partial=false&symbol=XBT&count=100&reverse=true"
#
#
# async def request(client):
#     response = await client.get(URL)
#     return response.json()
#
#
# async def task():
#     async with httpx.AsyncClient() as client:
#         tasks = request(client)
#         result = await asyncio.gather(tasks)
#         return result

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

@app.get('/predicts/')
async def getModelResults(id: Optional[str]):
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
        print(updateContent)
    else:
        mapeLs = list(data.get('mapeArr'))
        mapeLs.append(res['mape'])
        updateVal = {"mapeArr": mapeLs, "lastMAPE": res['mape'], "avgMAPE": sum(mapeLs)/len(mapeLs)}
        updateContent['$set'] = updateVal
        print(updateContent)
    try:
        models.update_one(query, updateContent)
    except:
        return JSONResponse(status_code=500)


    return res