import json

from fastapi import FastAPI
from time import time
from typing import Optional
import httpx 
import asyncio
import modelPred
from py_db import prices, prices_d

app = FastAPI()

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

@app.get('/view/')
async def getSymbolPrice(symbol: Optional[str] = None, limit: Optional[int] = 240, interval: Optional[str] = '1h'):
    start = time()
    # res = await task()

    query = ""
    if symbol:
        query = {"Symbol" : f'{symbol}'}
        # return prices.count_documents({"Symbol" : f'{symbol}'})
    if interval == '1d':
        list_cur = list(prices_d.find(query).sort('CloseTime', -1).limit(limit))
    else:
        list_cur = list(prices.find(query).sort('CloseTime', -1).limit(limit))
    res = json.dumps(list_cur, default=str)

    print(limit)
    return json.loads(res)