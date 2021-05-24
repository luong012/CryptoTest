from fastapi import FastAPI
from time import time
import httpx 
import asyncio
import modelPred


app = FastAPI()

URL = "https://www.bitmex.com/api/v1/trade/bucketed?binSize=1m&partial=false&symbol=XBT&count=100&reverse=true"


async def request(client):
    response = await client.get(URL)
    return response.json()


async def task():
    async with httpx.AsyncClient() as client:
        tasks = request(client)
        result = await asyncio.gather(tasks)
        return result


@app.get('/')
async def f():
    start = time()
    res = await task()
    c = modelPred.calc()
    return c