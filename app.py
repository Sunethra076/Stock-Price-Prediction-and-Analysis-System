import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Portfolio
from utils import get_stock_data, plot_chart, get_news, analyze_sentiment, stock_calculator
from flask import Flask, render_template
from newsapi import NewsApiClient
from flask import Flask, render_template, request
import requests
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from models import db
from flask import send_file, render_template
from flask_login import login_required, current_user

API_KEY = 'b26170b95a744bea929b285b7dd6742e'
app = Flask(__name__)

users = {}

app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

with app.app_context():
    db.create_all()

admin = Admin(app, name='Admin Panel', template_mode='bootstrap4')

# Register your models (add more as needed)
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Portfolio, db.session))


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'message')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'error')
        else:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful. Please log in.', 'message')
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/viewer', methods=['GET', 'POST'])
@login_required
def viewer():
    stock_data = None
    ticker = None
    chart_html = None
    if request.method == 'POST':
        ticker = request.form['ticker']
        period = request.form.get('period', '5d')
        df = get_stock_data(ticker, period)
        if not df.empty:
            latest = df.iloc[-1]
            stock_data = {
                'date': latest.name.strftime('%Y-%m-%d'),
                'open': latest['Open'],
                'close': latest['Close'],
                'high': latest['High'],
                'low': latest['Low'],
                'volume': int(latest['Volume'])
            }
            # Generate a Plotly chart
            import plotly.graph_objs as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Close Price'))
            fig.update_layout(title=f'{ticker.upper()} Closing Prices', xaxis_title='Date', yaxis_title='Price')
            chart_html = fig.to_html(full_html=False)
    return render_template('viewer.html', stock_data=stock_data, ticker=ticker, chart_html=chart_html)


@app.route('/compare', methods=['GET', 'POST'])
@login_required
def compare():
    chart_html = None
    if request.method == 'POST':
        ticker1 = request.form['ticker1']
        ticker2 = request.form['ticker2']
        period = request.form['period']
        chart_type = request.form['chart_type']
        df1 = get_stock_data(ticker1, period)
        df2 = get_stock_data(ticker2, period)
        
        import plotly.graph_objs as go
        if chart_type == 'line':
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df1.index, y=df1['Close'], name=ticker1))
            fig.add_trace(go.Scatter(x=df2.index, y=df2['Close'], name=ticker2))
        elif chart_type == 'bar':
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df1.index, y=df1['Close'], name=ticker1))
            fig.add_trace(go.Bar(x=df2.index, y=df2['Close'], name=ticker2))
        elif chart_type == 'candlestick':
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df1.index, open=df1['Open'], high=df1['High'],
                                         low=df1['Low'], close=df1['Close'], name=ticker1))
            fig.add_trace(go.Candlestick(x=df2.index, open=df2['Open'], high=df2['High'],
                                         low=df2['Low'], close=df2['Close'], name=ticker2))
        chart_html = fig.to_html(full_html=False)
    return render_template('compare.html', chart_html=chart_html)


@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    predicted = None
    if request.method == 'POST':
        ticker = request.form['ticker']
        df = get_stock_data(ticker, '1mo')
        from sklearn.linear_model import LinearRegression
        import numpy as np
        df = df.reset_index()
        df['Date_ordinal'] = pd.to_datetime(df['Date']).map(pd.Timestamp.toordinal)
        X = df[['Date_ordinal']]
        y = df['Close']
        model = LinearRegression().fit(X, y)
        tomorrow = df['Date_ordinal'].max() + 1
        predicted = model.predict([[tomorrow]])[0]
    return render_template('predict.html', predicted=predicted)

@app.route('/news', methods=['GET', 'POST'])
def news():
    articles = []
    ticker = ''
    if request.method == 'POST':
        ticker = request.form['ticker']
        url = f'https://newsapi.org/v2/everything?q={ticker}&apiKey={API_KEY}&language=en'
        response = requests.get(url)
        data = response.json()
        articles = data.get('articles', [])
    return render_template('news.html', articles=articles, ticker=ticker)


@app.route('/calculator', methods=['GET', 'POST'])
@login_required
def calculator():
    result = None
    profit_loss = None
    profit_loss_percent = None  # Ensure it's defined
    error = None
    if request.method == 'POST':
        try:
            price = request.form.get('price', type=float)
            shares = request.form.get('shares', type=int)
            buy_price = request.form.get('buy_price', type=float)
            if price is None or shares is None or buy_price is None:
                error = "Please fill in all fields."
            else:
                result = stock_calculator(price, shares)
                profit_loss = (price - buy_price) * shares
                if buy_price > 0:
                    profit_loss_percent = ((price - buy_price) / buy_price) * 100
        except Exception as e:
            error = "Invalid input. Please check your numbers."
    # Always pass profit_loss_percent, even if None
    return render_template(
        'calculator.html',
        result=result,
        profit_loss=profit_loss,
        profit_loss_percent=profit_loss_percent,
        error=error
    )

@app.route('/trade', methods=['GET', 'POST'])
@login_required
def trade():
    result = None
    error = None
    if request.method == 'POST':
        try:
            ticker = request.form['ticker']
            shares = int(request.form['shares'])
            trade_type = request.form['trade_type']
            price = float(request.form['price'])
            if trade_type == 'buy':
                result = f"Bought {shares} shares of {ticker.upper()} at ₹{price:.2f} each."
            else:
                result = f"Sold {shares} shares of {ticker.upper()} at ₹{price:.2f} each."
        except Exception as e:
            error = "Invalid input, please check your entries."
    return render_template('trade.html', result=result, error=error)

if __name__ == '__main__':
    app.run(debug=True)
