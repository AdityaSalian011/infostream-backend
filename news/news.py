import os
from news.utils import get_top_10_news
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

class NewsAPI:
    # def store_top_news(self, api_key, topic, file_name=NEWS_DATA_FILE):
    def get_top_news(self, topic, api_key=None):
        api_key = api_key or NEWS_API_KEY
        """Storing top 10 news articles based on topic."""
        return get_top_10_news(api_key, topic)