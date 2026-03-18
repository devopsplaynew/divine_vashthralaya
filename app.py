from flask import Flask, render_template, request, redirect
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import os
import json

app = Flask(__name__)

# -------------------------------
# GOOGLE SHEETS CONNECTION
# -------------------------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Load credentials from Render environment variable
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open("Divine Expense Tracker").sheet1


# -------------------------------
# GET DATA FROM SHEET
# -------------------------------
def get_data():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')

    return df


# -------------------------------
# HOME PAGE
# -------------------------------
@app.route('/', methods=['GET'])
def index():
    df = get_data()

    if df.empty:
        return render_template(
            "index.html",
            income=0,
            expense=0,
            balance=0,
            labels=[],
            values=[]
        )

    # Filters
    start = request.args.get('start')
    end = request.args.get('end')
    search = request.args.get('search')

    if start:
        df = df[df['Date'] >= pd.to_datetime(start)]
    if end:
        df = df[df['Date'] <= pd.to_datetime(end)]
    if search:
        df = df[df['Category'].str.contains(search, case=False, na=False)]

    # Calculations
    income = df[df['Type'] == 'Income']['Amount'].sum()
    expense = df[df['Type'] == 'Expense']['Amount'].sum()
    balance = income - expense

    # Monthly Profit
    monthly = df.groupby(df['Date'].dt.to_period('M'))['Amount'].sum()

    return render_template(
        "index.html",
        income=int(income),
        expense=int(expense),
        balance=int(balance),
        labels=[str(x) for x in monthly.index],
        values=[int(x) for x in monthly.values]  # ✅ FIXED JSON ERROR
    )


# -------------------------------
# ADD DATA
# -------------------------------
@app.route('/add', methods=['POST'])
def add():
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d"),
        request.form['type'],
        request.form['category'],
        float(request.form['amount'])
    ])
    return redirect('/')


# -------------------------------
# RUN APP
# -------------------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
