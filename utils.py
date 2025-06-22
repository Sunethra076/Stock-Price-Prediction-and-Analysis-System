import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from textblob import TextBlob
import requests
from bs4 import BeautifulSoup

# Fetch stock data for a given ticker and period
def get_stock_data(ticker, period):
    stock = yf.Ticker(ticker)
    interval = '1d' if period == '1d' else '1d'
    return stock.history(period=period, interval=interval)

# Plot stock data as line, bar, or candlestick chart
def plot_chart(df, chart_type):
    if chart_type == 'line':
        fig = go.Figure([go.Scatter(x=df.index, y=df['Close'])])
    elif chart_type == 'bar':
        fig = go.Figure([go.Bar(x=df.index, y=df['Close'])])
    elif chart_type == 'candlestick':
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close']
        )])
    return fig.to_html(full_html=False)

def get_news():
    url = "https://finance.yahoo.com/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    headlines = [a.text for a in soup.find_all('h3')]
    print("HEADLINES:", headlines)  # Debug
    return headlines[:5]


# (Optional) Fetch news headlines for a specific ticker from Yahoo Finance
def get_news_by_ticker(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}?p={ticker}"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    headlines = [a.text for a in soup.find_all('h3')]
    return headlines[:5]

# Analyze sentiment of a list of news headlines
def analyze_sentiment(news_list):
    sentiments = []
    for news in news_list:
        analysis = TextBlob(news)
        sentiments.append({'headline': news, 'polarity': analysis.sentiment.polarity})
    return sentiments

# Simple stock calculator (price * shares)
def stock_calculator(price, shares):
    return price * shares
