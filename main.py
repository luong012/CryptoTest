import json

from fastapi import FastAPI, HTTPException
from time import time
from typing import Optional
import httpx 
import asyncio
import modelPred
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from py_db import prices, prices_d
from fastapi.middleware.cors import CORSMiddleware

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