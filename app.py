from flask import Flask, render_template, request, redirect
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd

app = Flask(__name__)

# Google Sheets connection
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

sheet = client.open("Divine Expense Tracker").sheet1


# Convert sheet to DataFrame
def get_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)


@app.route('/', methods=['GET'])
def index():
    df = get_data()

    if df.empty:
        return render_template("index.html", income=0, expense=0, balance=0, labels=[], values=[])

    # Filters
    start = request.args.get('start')
    end = request.args.get('end')
    search = request.args.get('search')

    if start:
        df = df[df['Date'] >= start]
    if end:
        df = df[df['Date'] <= end]
    if search:
        df = df[df['Category'].str.contains(search, case=False)]

    # Calculations
    income = df[df['Type'] == 'Income']['Amount'].sum()
    expense = df[df['Type'] == 'Expense']['Amount'].sum()
    balance = income - expense

    # Monthly profit
    df['Date'] = pd.to_datetime(df['Date'])
    monthly = df.groupby(df['Date'].dt.to_period('M'))['Amount'].sum()

    return render_template(
        "index.html",
        income=income,
        expense=expense,
        balance=balance,
        labels=list(map(str, monthly.index)),
        values=list(monthly.values)
    )


@app.route('/add', methods=['POST'])
def add():
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d"),
        request.form['type'],
        request.form['category'],
        float(request.form['amount'])
    ])
    return redirect('/')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
