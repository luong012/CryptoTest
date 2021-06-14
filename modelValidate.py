from py_db import prices, prices_d
import pandas as pd
from utils.evaluation import mean_absolute_percentage_error
import json

def preProcessing(symbol, interval):
    query = {"Symbol": f'{symbol}'}
    if interval == '1d':
        list_cur = prices_d.find(query).sort('CloseTime', 1)
    else:
        list_cur = prices.find(query).sort('CloseTime', 1)
    newDF = pd.DataFrame(list_cur)

    newDF['OpenTime'] = pd.to_numeric(newDF['OpenTime'])
    newDF['OpenTime'] = newDF['OpenTime'].apply(lambda x: x * 1000000)
    newDF['OpenTime'] = pd.to_datetime(newDF['OpenTime'])

    newDF['CloseTime'] = pd.to_numeric(newDF['CloseTime'])
    newDF['CloseTime'] = newDF['CloseTime'].apply(lambda x: x * 1000000)
    newDF['CloseTime'] = pd.to_datetime(newDF['CloseTime'])


    newDF.index = newDF['OpenTime']

    newDF.drop(newDF.columns[[0, 1, 2, 3, 4, 6, 7, 8]], axis=1, inplace=True)

    return newDF


def calc(symbol, interval, modelPath):

    from sklearn.preprocessing import MinMaxScaler

    import numpy as np

    import pandas as pd
    import tensorflow as tf

    df = preProcessing(symbol, interval)

    ratio = 0.8

    df['Close'] = pd.to_numeric(df['Close'])

    train_set_len= int(len(df)*ratio)

    # creating train and test sets
    dataset = df.values
    dataset = dataset.astype(float)
    train = dataset[0:train_set_len, :]
    valid = dataset[train_set_len:, :]

    # converting dataset into x_train and y_train
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(dataset)



    # predict
    inputs = df[len(df) - len(valid) - 60:].values
    inputs = inputs.reshape(-1, 1)
    inputs = scaler.transform(inputs)

    X_test = []
    for i in range(60, inputs.shape[0]):
        X_test.append(inputs[i - 60:i, 0])
    X_test = np.array(X_test)
    X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))

    pd.options.mode.chained_assignment = None


    # Load model
    fileName = modelPath
    model = tf.keras.models.load_model(f'models/1/{interval}/{symbol}/{fileName}')
    closing_price = model.predict(X_test)
    closing_price = scaler.inverse_transform(closing_price)

    # Evaluating model accuracy
    rms = np.sqrt(np.mean(np.power((valid - closing_price), 2)))

    # print(mape)
    mape = mean_absolute_percentage_error(valid, closing_price)




    valid = df[train_set_len:]


    valid['Predictions'] = closing_price
    # plt.plot(train['Close'])
    # plt.plot(valid['Close', 'Predictions'])
    # plt.show()
    valid['Time'] = valid.index
    validJSON = valid.to_json(orient="records")
    validParsed = json.loads(validJSON)


    res = {}
    res["mape"]=mape
    res["testRes"] = validParsed
    return res