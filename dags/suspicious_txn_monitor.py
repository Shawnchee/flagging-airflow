import sys
import os

import datetime
import json
from airflow import DAG
from airflow.operators.python import PythonOperator
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

# Define the DAG
default_args = {
    'owner': 'airflow',
    'retries': 1,
    'start_date': datetime.datetime(2025, 4, 18),
}

dag = DAG(
    'suspicious_txn_monitor',
    default_args=default_args,
    description='DAG for flagging suspicious transactions',
    schedule_interval='@daily',  # You can change this to how often you want it to run
)

# Function to fetch transaction data from mock_txns.json
def fetch_transactions():
    with open("/opt/airflow/data/mock_txns.json", "r") as file:
        transactions = json.load(file)
    return transactions

# Function to check for suspicious transactions
def check_suspicious_transactions():
    transactions = fetch_transactions()
    flagged_transactions = []

    # Rule 1: Large Transaction Value
    large_value_threshold = 50  # Any transaction greater than 50 is suspicious

    for tx in transactions:
        if float(tx['value']) > large_value_threshold:
            flagged_transactions.append({
                "tx_hash": tx['hash'],
                "reason": "Large Transaction Value",
                "value": tx['value'],
                "from": tx['from'],
                "to": tx['to'],
            })
    
    # Rule 2: Frequent Transactions
    # This rule assumes we are looking at transactions from the same address within a short timeframe
    suspicious_timeframe = 10  # Seconds
    transactions.sort(key=lambda x: x['timeStamp'])
    for i in range(1, len(transactions)):
        if (int(transactions[i]['timeStamp']) - int(transactions[i-1]['timeStamp'])) <= suspicious_timeframe:
            flagged_transactions.append({
                "tx_hash": transactions[i]['hash'],
                "reason": "Frequent Transaction",
                "value": transactions[i]['value'],
                "from": transactions[i]['from'],
                "to": transactions[i]['to'],
            })

    return flagged_transactions

# Function to store flagged transactions in Supabase (mocked here for now)
def store_flagged_transactions(flagged_transactions):
    for transaction in flagged_transactions:
        txn_data = {
            "hash": transaction["tx_hash"],
            "from_address": transaction["from"],
            "to_address": transaction["to"],
            "value": float(transaction["value"]),  # Assuming value is in ETH
            "flag_reason": transaction["reason"]
        }

        try:
            response = supabase.table("flagged_transactions").insert(txn_data).execute()
            if response.status_code == 201:
                print(f"Transaction {transaction['tx_hash']} flagged successfully.")
            else:
                print(f"Failed to store flagged transaction: {response.status_code}")
        except Exception as e:
            print(f"Error storing flagged transaction: {str(e)}")

# Define the Airflow tasks
fetch_transactions_task = PythonOperator(
    task_id='fetch_transactions',
    python_callable=fetch_transactions,
    dag=dag,
)

check_suspicious_task = PythonOperator(
    task_id='check_suspicious_transactions',
    python_callable=check_suspicious_transactions,
    dag=dag,
)

store_flagged_task = PythonOperator(
    task_id='store_flagged_transactions',
    python_callable=store_flagged_transactions,
    op_args=[check_suspicious_transactions()],
    dag=dag,
)

# Set the task dependencies
fetch_transactions_task >> check_suspicious_task >> store_flagged_task
