from flask import Flask, render_template, request, redirect, session, send_file
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import os, json, io

app = Flask(__name__)
app.secret_key = "secret123"   # for login session

# ---------------- GOOGLE SHEETS ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open("Divine Expense Tracker").sheet1


def get_data():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')

    return df


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == "admin" and request.form['password'] == "admin":
            session['user'] = "admin"
            return redirect('/')
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')


# ---------------- HOME ----------------
@app.route('/')
def index():
    if 'user' not in session:
        return redirect('/login')

    df = get_data()

    if df.empty:
        return render_template("index.html", income=0, expense=0, balance=0,
                               labels=[], values=[], records=[],
                               daily_labels=[], income_data=[], expense_data=[],
                               categories=[], category_values=[])

    # Calculations
    income = df[df['Type'] == 'Income']['Amount'].sum()
    expense = df[df['Type'] == 'Expense']['Amount'].sum()
    balance = income - expense

    # Monthly chart
    monthly = df.groupby(df['Date'].dt.to_period('M'))['Amount'].sum()

    # Daily chart
    daily = df.groupby(['Date', 'Type'])['Amount'].sum().unstack().fillna(0)

    daily_labels = [str(x.date()) for x in daily.index]
    income_data = [int(x) for x in daily.get('Income', [])]
    expense_data = [int(x) for x in daily.get('Expense', [])]

    # Category pie
    cat = df.groupby('Category')['Amount'].sum()

    return render_template(
        "index.html",
        income=int(income),
        expense=int(expense),
        balance=int(balance),
        labels=[str(x) for x in monthly.index],
        values=[int(x) for x in monthly.values],
        records=df.to_dict(orient='records'),
        daily_labels=daily_labels,
        income_data=income_data,
        expense_data=expense_data,
        categories=list(cat.index),
        category_values=[int(x) for x in cat.values]
    )


# ---------------- ADD ----------------
@app.route('/add', methods=['POST'])
def add():
    if 'user' not in session:
        return redirect('/login')

    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d"),
        request.form['type'],
        request.form['category'],
        float(request.form['amount'])
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


# ---------------- RUN ----------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
