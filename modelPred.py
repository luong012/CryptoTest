def calc():
    from tensorflow import keras
    # importing required libraries
    from sklearn.preprocessing import MinMaxScaler

    import numpy as np

    import pandas as pd
    scaler = MinMaxScaler(feature_range=(0, 1))
    df = pd.read_csv('btcprice.csv')
    df.drop(df.columns[0], axis=1, inplace=True)

    # setting index as date
    # df['OpenTime'] = pd.to_datetime(df.Date,format='%Y-%m-%d')
    df.index = df['OpenTime']

    # creating dataframe
    data = df.sort_index(ascending=True, axis=0)
    new_data = pd.DataFrame(index=range(0, len(df)), columns=['OpenTime', 'Close'])
    for i in range(0, len(data)):
        new_data['OpenTime'][i] = data['OpenTime'][i]
        new_data['Close'][i] = data['Close'][i]
    # setting index
    new_data.index = new_data.OpenTime
    new_data.drop('OpenTime', axis=1, inplace=True)
    new_data

    # creating train and test sets
    dataset = new_data.values

    train = dataset[0:979, :]
    valid = dataset[979:, :]

    # converting dataset into x_train and y_train
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(dataset)

    x_train, y_train = [], []
    for i in range(120, len(train)):
        x_train.append(scaled_data[i - 120:i, 0])
        y_train.append(scaled_data[i, 0])
    x_train, y_train = np.array(x_train), np.array(y_train)

    x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))

    import tensorflow as tf
    model = tf.keras.models.load_model('LSTM-Simple.h5')


    # predicting 246 values, using past 60 from the train data
    inputs = new_data[len(new_data) - len(valid) - 60:].values
    inputs = inputs.reshape(-1, 1)
    inputs = scaler.transform(inputs)

    X_test = []
    for i in range(60, inputs.shape[0]):
        X_test.append(inputs[i - 60:i, 0])
    X_test = np.array(X_test)
    X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))
    closing_price = model.predict(X_test)
    closing_price = scaler.inverse_transform(closing_price)

    # Evaluating model accuracy
    rms = np.sqrt(np.mean(np.power((valid - closing_price), 2)))
    mape = np.sqrt(np.mean(np.abs((valid - closing_price) / valid)))
    print(mape)
    return mape

