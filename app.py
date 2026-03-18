from flask import Flask, render_template, request, redirect, session, send_file
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import os, json, io

app = Flask(__name__)
app.secret_key = "secret123"

# GOOGLE SHEETS
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open("Divine Expense Tracker").sheet1

# STOCK SHEET
try:
    stock_sheet = client.open("Divine Expense Tracker").worksheet("Stocks")
except:
    stock_sheet = client.open("Divine Expense Tracker").add_worksheet(title="Stocks", rows="100", cols="10")
    stock_sheet.append_row(["ID","Item","Type","Actual Price","Sale Price","Difference","Sold"])

# ---------------- DATA ----------------
def get_data():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')

    return df

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        if request.form['username']=="admin" and request.form['password']=="admin":
            session['user']="admin"
            return redirect('/')
        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------------- HOME ----------------
@app.route('/')
def index():
    if 'user' not in session:
        return redirect('/login')

    df = get_data()

    if df.empty:
        return render_template("index.html", income=0, expense=0, balance=0,
                               records=[], daily_labels=[], income_data=[],
                               expense_data=[], categories=[], category_values=[])

    income = int(df[df['Type']=="Income"]['Amount'].sum())
    expense = int(df[df['Type']=="Expense"]['Amount'].sum())
    balance = income - expense

    daily = df.groupby(['Date','Type'])['Amount'].sum().unstack().fillna(0)

    return render_template(
        "index.html",
        income=income,
        expense=expense,
        balance=balance,
        records=df.to_dict(orient='records'),
        daily_labels=[str(x.date()) for x in daily.index],
        income_data=[int(x) for x in daily.get('Income', [])],
        expense_data=[int(x) for x in daily.get('Expense', [])],
        categories=list(df.groupby('Category')['Amount'].sum().index),
        category_values=[int(x) for x in df.groupby('Category')['Amount'].sum().values]
    )

# ---------------- ADD ----------------
@app.route('/add', methods=['POST'])
def add():
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d"),
        request.form['type'],
        request.form['category'],
        float(request.form['amount'])
    ])
    return redirect('/')

# ---------------- DELETE ----------------
@app.route('/delete', methods=['POST'])
def delete():
    df = get_data()
    df['Date'] = df['Date'].astype(str)

    df = df[~(
        (df['Date'] == request.form['date']) &
        (df['Category'] == request.form['category']) &
        (df['Amount'].astype(float) == float(request.form['amount']))
    )]

    sheet.clear()
    sheet.append_row(["Date","Type","Category","Amount"])

    for _, row in df.iterrows():
        sheet.append_row([
            str(row['Date'])[:10],
            row['Type'],
            row['Category'],
            row['Amount']
        ])

    return redirect('/')

# ---------------- DOWNLOAD ----------------
@app.route('/download')
def download():
    df = get_data()
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name="expenses.xlsx", as_attachment=True)

# ---------------- STOCK PAGE ----------------
@app.route('/stocks')
def stocks():
    data = stock_sheet.get_all_records()
    df = pd.DataFrame(data)

    if df.empty:
        return render_template("stocks.html", records=[], sold=0, pending=0)

    df['Difference'] = df['Sale Price'] - df['Actual Price']

    sold = len(df[df['Sold']=="Y"])
    pending = len(df[df['Sold']=="N"])

    return render_template("stocks.html",
        records=df.to_dict(orient='records'),
        sold=sold,
        pending=pending
    )

# ---------------- ADD STOCK ----------------
@app.route('/add_stock', methods=['POST'])
def add_stock():
    stock_sheet.append_row([
        request.form['id'],
        request.form['item'],
        request.form['type'],
        float(request.form['actual']),
        float(request.form['sale']),
        0,
        request.form['sold']
    ])
    return redirect('/stocks')

# ---------------- UPDATE STOCK ----------------
@app.route('/update_stock', methods=['POST'])
def update_stock():
    data = stock_sheet.get_all_records()

    for i, row in enumerate(data, start=2):
        if str(row['ID']) == request.form['id']:
            diff = float(request.form['sale']) - float(request.form['actual'])

            stock_sheet.update(f"A{i}:G{i}", [[
                request.form['id'],
                request.form['item'],
                request.form['type'],
                float(request.form['actual']),
                float(request.form['sale']),
                diff,
                request.form['sold']
            ]])
            break

    return redirect('/stocks')

# ---------------- RUN ----------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
