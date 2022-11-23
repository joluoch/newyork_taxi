import argparse
import pandas as pd
from sqlalchemy import create_engine
from time import time
import os
import sys

def main(params):

    user = params.user
    password = params.password
    host = params.host
    port = params.port
    db = params.db
    table_name = params.table_name
    url = params.url
    # download csv 

    name = 'output.parquet'
    csv_name = 'output.csv'
    try:
        os.system(f"wget {url} -O {name}")
    except Exception as e:
        print(e)
        sys.exit(1)
    print('converting to csv')
    pd.read_parquet('output.parquet').to_csv(csv_name)
    print('done')
    engine = create_engine(f'postgresql://{user}:{password}@{host}:{port}/{db}')

    df_iter = pd.read_csv(csv_name,iterator=True,chunksize=100000)
    df = next(df_iter)

    df.tpep_pickup_datetime = pd.to_datetime(df.tpep_pickup_datetime)
    df.tpep_dropoff_datetime = pd.to_datetime(df.tpep_dropoff_datetime)
    df = df.drop(['Unnamed: 0'],axis=1)

    df.head(n=0).to_sql(name =table_name,con=engine,if_exists='replace')
    df.to_sql(name = table_name,con=engine,if_exists='append')


    while True:
        t_start = time()
        df= next(df_iter)

        df.tpep_pickup_datetime = pd.to_datetime(df.tpep_pickup_datetime)
        df.tpep_dropoff_datetime = pd.to_datetime(df.tpep_dropoff_datetime)
        df = df.drop(['Unnamed: 0'],axis=1)
        
        df.to_sql(name =table_name,con=engine,if_exists='append')
        t_end = time()
        print ('inseted anoter took , %.3f seconds'%(t_end - t_start))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ingest CSV data to Postgress')

    #user, papss, host,port, db,
    parser.add_argument('--user',help='postgres user name')
    parser.add_argument('--password',help='postgres password')
    parser.add_argument('--host',help='postgres host')
    parser.add_argument('--port',help='postgres port')
    parser.add_argument('--db',help='database name postgres')
    parser.add_argument('--table_name',help='tablename')
    parser.add_argument('--url',help='csv url')

    args = parser.parse_args()

    main(args)