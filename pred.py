import json

from sklearn.preprocessing import MinMaxScaler
from modelValidate import preProcessing
import numpy as np

import tensorflow as tf

inputSize = 60

def predNext(symbol, interval, modelPath):
    df = preProcessing(symbol, interval)

    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(df)
    df = df[-inputSize:]



    inputs = df.values
    # print(inputs)
    inputs = inputs.reshape(-1,1)
    inputs  = scaler.transform(inputs)


    # Load model
    fileName = modelPath
    model = tf.keras.models.load_model(f'models/{interval}/{symbol}/{fileName}')

    X_test = []
    # for i in range(60,inputs.shape[0]+1):
    X_test.append(inputs[1:61,0])
    X_test = np.array(inputs)
    X_test = X_test.reshape(1, -1)
    X_test = np.reshape(X_test, (X_test.shape[0],X_test.shape[1],1))

    closing_price = model.predict(tf.constant(X_test))
    closing_price = scaler.inverse_transform(closing_price)

    return closing_price[0][0]