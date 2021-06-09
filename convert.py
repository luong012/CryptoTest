import json
import pandas as pd

def convert(symbol, df):

    priceDF= [r[0:7] for r in df]
    newDF = pd.DataFrame(data = priceDF, columns = ['OpenTime', 'Open', 'High', 'Low', 'Close', 'Volume', 'CloseTime'])
    newDF['OpenTime']=pd.to_numeric(newDF['OpenTime'])
    newDF['OpenTime']=newDF['OpenTime'].apply(lambda x: x*1000000)
    newDF['OpenTime']=pd.to_datetime(newDF['OpenTime'])

    newDF['Symbol']=symbol

    newDF['CloseTime']=pd.to_numeric(newDF['CloseTime'])
    newDF['CloseTime']=newDF['CloseTime'].apply(lambda x: x*1000000)
    newDF['CloseTime']=pd.to_datetime(newDF['CloseTime'])
    newDF.drop(newDF.tail(1).index, inplace=True)


    resJSON = newDF.to_json(orient='records')
    parsedJSON = json.loads(resJSON)

    #datetimeCol = [datetime.fromtimestamp(int(r['OpenTime'])) for r in newDF]
    #newDF.to_json(path_or_buf="output.json", orient="records")
    return parsedJSON

