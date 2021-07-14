import json
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from modelValidate import preProcessing
import numpy as np

import tensorflow as tf

# inputSize = 60

def predNext(symbol, interval, modelPath, inputSize ,outputWindows):
    df = preProcessing(symbol, interval).drop('CloseTime', axis=1)

    print(df)

    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(df)
    df = df[-inputSize:]
    if interval == '1d':
        step = 86400000
    else:
        step = 3600000

    baseTime = df.tail(1).index.item().timestamp() * 1000

    inputs = df.values
    inputs = inputs.reshape(-1,1)
    inputs  = scaler.transform(inputs)


    # Load model
    fileName = modelPath
    model = tf.keras.models.load_model(f'models/{outputWindows}/{interval}/{symbol}/{fileName}')

    X_test = []
    # for i in range(60,inputs.shape[0]+1):
    X_test.append(inputs[1:61,0])
    X_test = np.array(inputs)
    X_test = X_test.reshape(1, -1)
    X_test = np.reshape(X_test, (X_test.shape[0],X_test.shape[1],1))

    closing_price = model.predict(tf.constant(X_test))
    closing_price = scaler.inverse_transform(closing_price)

    predTime = baseTime + step
    resLs = []

    print(baseTime)

    for i in range(outputWindows):
        predTime += step
        resLs.append([predTime-1, closing_price[0][i]])
        # row = pd.DataFrame(data = [baseTime-1, closing_price[0][i]],columns=["CloseTime", "Close"])
        # resDF.append(row)
        # print(predTime-1, closing_price[0][i])

    resDF = pd.DataFrame(data = resLs, columns=["CloseTime", "Close"])
    resJSON = resDF.to_json(orient="records")
    res = json.loads(resJSON)

    return res