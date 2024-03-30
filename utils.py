from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
import yfinance as yf
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import json

load_dotenv("env_variables.env")
client = OpenAI()

class TickerList(BaseModel):
    tickers_list: List[str]


def get_article_text(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        article_text = ' '.join([p.get_text() for p in soup.find_all('p')])
        return article_text
    except:
        return "Error retrieving article text."

def get_stock_data(ticker, years):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=years*365)

    stock = yf.Ticker(ticker)

    # Retrieve historical price data
    hist_data = stock.history(start=start_date, end=end_date)

    # Retrieve balance sheet
    balance_sheet = stock.balance_sheet

    # Retrieve financial statements
    financials = stock.financials

    # Retrieve news articles
    news = stock.news

    return hist_data, balance_sheet, financials, news


def generate_ticker_ideas(industry):
    
    messages = [
        {
            "role": "system",
            "content": f"You are a financial analyst assistant. Generate a list of 3 ticker symbols for major companies in the {industry} industry, as a Python-parseable list."
        },
        {
            "role": "user", "content": f"Please provide a list of 3 ticker symbols for major companies in the {industry} industry as a Python-parseable list. Only respond with the list, no other text."},
    ]

    response = client.chat.completions.create(
        temperature = 0.1,
        model="gpt-3.5-turbo-0125",
        messages=messages,
        functions=[
            {
            "name": "Stock_Ticker_Generator",
            "description": "Generate a list of 3 ticker symbols for major companies",
            "parameters": TickerList.model_json_schema()
            }
        ],
        function_call={"name": "Stock_Ticker_Generator"}
    )


    return json.loads(response.choices[0].message.function_call.arguments)['tickers_list']

def get_sentiment_analysis(ticker, news):

    news_text = ""
    for article in news:
        article_text = get_article_text(article['link'])
        timestamp = datetime.fromtimestamp(article['providerPublishTime']).strftime("%Y-%m-%d")
        news_text += f"\n\n---\n\nDate: {timestamp}\nTitle: {article['title']}\nText: {article_text}"

    messages = [
        {
            "role": "system",
            "content": f"You are a sentiment analysis assistant. Analyze the sentiment of the given news articles for {ticker} and provide a summary of the overall sentiment and any notable changes over time. Be measured and discerning. You are a skeptical investor."
        },
        {
            "role": "user", 
            "content": f"News articles for {ticker}:\n{news_text}\n\n----\n\nProvide a summary of the overall sentiment and any notable changes over time."},
    ]

    
    response = client.chat.completions.create(
        temperature = 0.1,
        model="gpt-3.5-turbo-0125",
        messages=messages
    )
    
    return response

def get_analyst_ratings(ticker):
    stock = yf.Ticker(ticker)
    recommendations = stock.get_recommendations()
    if recommendations is None or recommendations.empty:
        return "No analyst ratings available."

    latest_rating = recommendations.iloc[0]

    rating_summary = f"Latest analyst rating for {ticker}:\n {str(latest_rating.to_dict())}"

    return rating_summary


def get_industry_analysis(ticker):

    stock = yf.Ticker(ticker)
    industry = stock.info['industry']
    sector = stock.info['sector']


    messages = [
        {
            "role": "system",
            "content": f"You are an industry analysis assistant. Provide an analysis of the {industry} industry and {sector} sector, including trends, growth prospects, regulatory changes, and competitive landscape. Be measured and discerning. Truly think about the positives and negatives of the stock. Be sure of your analysis. You are a skeptical investor."
        },
        {
            "role": "user", 
            "content": f"Provide an analysis of the {industry} industry and {sector} sector."}
    ]

    
    response = client.chat.completions.create(
        temperature = 0.1,
        model="gpt-3.5-turbo-0125",
        messages=messages
    )
    
    return response.choices[0].message.content

def get_final_analysis(ticker, sentiment_analysis, analyst_ratings, industry_analysis):


    messages = [
        {
            "role": "system",
            "content": f"You are a financial analyst providing a final investment recommendation for {ticker} based on the given data and analyses. Be measured and discerning. Truly think about the positives and negatives of the stock. Be sure of your analysis. You are a skeptical investor."
        },
        {
            "role": "user", 
            "content": f"Ticker: {ticker}\n\nSentiment Analysis:\n{sentiment_analysis}\n\nAnalyst Ratings:\n{analyst_ratings}\n\nIndustry Analysis:\n{industry_analysis}\n\nBased on the provided data and analyses, please provide a comprehensive investment analysis and recommendation for {ticker}. Consider the company's financial strength, growth prospects, competitive position, and potential risks. Provide a clear and concise recommendation on whether to buy, hold, or sell the stock, along with supporting rationale."}
    ]

    
    response = client.chat.completions.create(
        temperature = 0.1,
        model="gpt-3.5-turbo-0125",
        messages=messages
    )
    
    return response.choices[0].message.content

def get_current_price(ticker):
    stock = yf.Ticker(ticker)
    data = stock.history(period='1d', interval='1m')
    return data['Close'][-1]


def rank_companies(industry, analyses, prices):

    analysis_text = "\n\n".join(
        f"Ticker: {ticker}\nCurrent Price: {prices.get(ticker, 'N/A')}\nAnalysis:\n{analysis}"
        for ticker, analysis in analyses.items()
    )


    messages = [
        {
            "role": "system",
            "content": f"You are a financial analyst providing a ranking of companies in the {industry} industry based on their investment potential. Be discerning and sharp. Truly think about whether a stock is valuable or not. You are a skeptical investor."
        },
        {
            "role": "user", 
            "content": f"Industry: {industry}\n\nCompany Analyses:\n{analysis_text}\n\nBased on the provided analyses, please rank the companies from most attractive to least attractive for investment. Provide a brief rationale for your ranking. In each rationale, include the current price (if available) and a price target."},
    ]

    
    response = client.chat.completions.create(
        temperature = 0.1,
        model="gpt-3.5-turbo-0125",
        messages=messages
    )
    
    return response.choices[0].message.content


def get_openai_verdict(tickers, industry):

    analyses = {}
    prices = {}
    for ticker in tickers:
        try:
            print(f"\nAnalyzing {ticker}...")
            hist_data, balance_sheet, financials, news = get_stock_data(ticker=ticker, years=1)
            
            #this
            sentiment_analysis = get_sentiment_analysis(ticker, news)
            analyst_ratings = get_analyst_ratings(ticker)

            #this
            industry_analysis = get_industry_analysis(ticker)

            #this
            final_analysis = get_final_analysis(ticker, sentiment_analysis, analyst_ratings, industry_analysis)
            
            analyses[ticker] = final_analysis
            prices[ticker] = get_current_price(ticker)
        except:
            pass
    
    ranking = rank_companies(industry, analyses, prices)
    return ranking