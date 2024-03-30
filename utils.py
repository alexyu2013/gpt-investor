from dataclasses import dataclass, field
from typing import List, Dict, Optional
import pandas as pd
import asyncio
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
import yfinance as yf

load_dotenv("env_variables.env")
syncclient = OpenAI()
asyncclient = AsyncOpenAI()

GPT_MODEL = "gpt-3.5-turbo-0125"

@dataclass
class TickerClass:
    name: str
    hist_data: Optional[pd.DataFrame] = field(default=None)
    balance_sheet: Optional[pd.DataFrame] = field(default=None)
    financials: Optional[pd.DataFrame] = field(default=None)
    news: Optional[Dict] = field(default=None)
    analyst_ratings: str = field(default=None)
    price: float = field(default=None)
    ######
    sentiment_analysis: str = field(default=None)
    industry_analysis: str = field(default=None)
    final_analysis: str = field(default=None)

    

def get_article_text(url: str) -> str:
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        article_text = ' '.join([p.get_text() for p in soup.find_all('p')])
        return article_text
    except:
        return "Error retrieving article text."

def get_stock_data(ticker: str, years: int=10) -> tuple:
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

def get_analyst_ratings(ticker: str) -> str:
    stock = yf.Ticker(ticker)
    recommendations = stock.get_recommendations()
    if recommendations is None or recommendations.empty:
        return "No analyst ratings available."

    latest_rating = recommendations.iloc[0]


    rating_summary = f"Latest analyst rating for {ticker}:\n {str(latest_rating.to_dict())}"

    return rating_summary

def get_current_price(ticker :str) -> float:
    stock = yf.Ticker(ticker)
    data = stock.history(period='1d')
    return data.iloc[0]['Close']


async def get_sentiment_analysis(ticker: TickerClass) -> None:
    print(f"analyzing sentiment for {ticker.name}")

    news_text = ""
    for article in ticker.news:
        article_text = get_article_text(article['link'])
        timestamp = datetime.fromtimestamp(article['providerPublishTime']).strftime("%Y-%m-%d")
        news_text += f"\n\n---\n\nDate: {timestamp}\nTitle: {article['title']}\nText: {article_text}"

    messages = [
        {
            "role": "system",
            "content": f"You are a sentiment analysis assistant. Analyze the sentiment of the given news articles for {ticker.name} and provide a summary of the overall sentiment and any notable changes over time. Be measured and discerning. You are a skeptical investor."
        },
        {
            "role": "user", 
            "content": f"News articles for {ticker.name}:\n{news_text}\n\n----\n\nProvide a summary of the overall sentiment and any notable changes over time."},
    ]

    
    response = await asyncclient.chat.completions.create(
        temperature = 0.1,
        model=GPT_MODEL,
        messages=messages
    )
    
    ticker.sentiment_analysis = response.choices[0].message.content




async def get_industry_analysis(ticker: TickerClass) -> None:
    print(f"Industry analysis for {ticker.name}")
    stock = yf.Ticker(ticker.name)
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

    
    response = await asyncclient.chat.completions.create(
        temperature = 0.1,
        model=GPT_MODEL,
        messages=messages
    )
    
    ticker.industry_analysis = response.choices[0].message.content

#def get_final_analysis(ticker: str, sentiment_analysis: str, analyst_ratings :str, industry_analysis: str) -> str:
async def get_final_analysis(ticker: TickerClass) -> None:
    print(f"Final analysis for {ticker.name}")
    messages = [
        {
            "role": "system",
            "content": f"You are a financial analyst providing a final investment recommendation for {ticker.name} based on the given data and analyses. Be measured and discerning. Truly think about the positives and negatives of the stock. Be sure of your analysis. You are a skeptical investor."
        },
        {
            "role": "user", 
            "content": f"Ticker: {ticker.name}\n\nSentiment Analysis:\n{ticker.sentiment_analysis}\n\nLatest Analyst Ratings:\n{ticker.analyst_ratings}\n\nIndustry Analysis:\n{ticker.industry_analysis}\n\nBased on the provided data and analyses, please provide a comprehensive investment analysis and recommendation for {ticker.name}. Consider the company's financial strength, growth prospects, competitive position, and potential risks. Provide a clear and concise recommendation on whether to buy, hold, or sell the stock, along with supporting rationale."}
    ]

    
    response = await asyncclient.chat.completions.create(
        temperature = 0.1,
        model=GPT_MODEL,
        messages=messages
    )
    
    ticker.final_analysis = response.choices[0].message.content




def rank_companies(ticker_info_list: List[TickerClass], industry: str) -> str:
    print(f"Ranking ...")
    analysis_text = "\n\n".join(f"Ticker: {ticker.name}\nCurrent Price: {ticker.price}\nAnslysis:\n{ticker.final_analysis}" for ticker in ticker_info_list)
    analysis_text = analysis_text


    messages = [
        {
            "role": "system",
            "content": f"You are a financial analyst providing a ranking of companies in the {industry} industry based on their investment potential. Be discerning and sharp. Truly think about whether a stock is valuable or not. You are a skeptical investor."
        },
        {
            "role": "user", 
            "content": f"Industry: {industry}\n\nCompany Analyses:\n{analysis_text}\n\nBased on the provided analyses, please rank the companies from most attractive to least attractive for investment. Provide a brief rationale for your ranking. In each rationale, include the current price (if available) and a price target."},
    ]

    
    response = syncclient.chat.completions.create(
        temperature = 0.1,
        model=GPT_MODEL,
        messages=messages
    )
    
    return response.choices[0].message.content



async def get_openai_verdict_2(tickers, industry):
    ticker_info_list = []
    for ticker in tickers:
        temp_ticker_info = TickerClass(name = ticker)
        temp_ticker_info.hist_data, temp_ticker_info.balance_sheet, temp_ticker_info.financials, temp_ticker_info.news = get_stock_data(ticker, years=1)

        temp_ticker_info.analyst_ratings = get_analyst_ratings(ticker)
        temp_ticker_info.price = get_current_price(ticker)
        ticker_info_list.append(temp_ticker_info)

    tasks1 = [get_sentiment_analysis(ticker_object) for ticker_object in ticker_info_list]
    await asyncio.gather(*tasks1)

    tasks2 = [get_industry_analysis(ticker_object) for ticker_object in ticker_info_list]
    await asyncio.gather(*tasks2)

    tasks3 = [get_final_analysis(ticker_object) for ticker_object in ticker_info_list]
    await asyncio.gather(*tasks3)

    final_ranking = rank_companies(ticker_info_list, industry)
    return final_ranking
    

