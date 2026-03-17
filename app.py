
from flask import Flask, render_template, request, redirect, session, send_file
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"
FILE = 'data.csv'

if not os.path.exists(FILE):
    df = pd.DataFrame(columns=['Date','Type','Category','Amount'])
    df.to_csv(FILE, index=False)

@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        if request.form['username']=="admin" and request.form['password']=="admin":
            session['user']="admin"
            return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    df = pd.read_csv(FILE)
    income = df[df['Type']=='Income']['Amount'].sum()
    expense = df[df['Type']=='Expense']['Amount'].sum()
    balance = income - expense

    df['Date'] = pd.to_datetime(df['Date'])
    monthly = df.groupby(df['Date'].dt.to_period('M'))['Amount'].sum().astype(float)

    return render_template('dashboard.html',
        income=income, expense=expense, balance=balance,
        monthly_labels=list(map(str, monthly.index)),
        monthly_values=list(monthly.values))

@app.route('/add', methods=['POST'])
def add():
    df = pd.read_csv(FILE)
    df.loc[len(df)] = [
        datetime.now().strftime("%Y-%m-%d"),
        request.form['type'],
        request.form['category'],
        float(request.form['amount'])
    ]
    df.to_csv(FILE, index=False)
    return redirect('/dashboard')

@app.route('/download')
def download():
    return send_file(FILE, as_attachment=True)

app.run(host="0.0.0.0", port=10000)
