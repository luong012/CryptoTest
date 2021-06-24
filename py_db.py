import json

from pymongo import MongoClient

f = open('config.json',)
js = json.load(f)

user = js['user']
passw = js['pass']
ip = js['ip']
uri = f'mongodb://{user}:{passw}@{ip}:27017/'

client = MongoClient(uri)
db = client.Crypto
prices = db.Price
prices_d = db.PriceByDate
models = db.Model
cronLogs = db.cronLog
modelTypes = db.ModelType
cryptos = db.Crypto
users = db.User