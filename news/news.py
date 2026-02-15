import nltk, json, os
from utils import get_top_10_news
from key import my_news_api_key

from config import NEWS_DATA_FILE

class NewsAPI:
    def __init__(self):
        """Initializing our NewsAPI class by downloading latest versions for punktb(used for nlp generation i.e. news summarization.)"""
        nltk.download('punkt')
        nltk.download('punkt_tab')
    
    # def store_top_news(self, api_key, topic, file_name=NEWS_DATA_FILE):
    def get_top_news(self, topic, api_key=my_news_api_key):
        """Storing top 10 news articles based on topic."""
        return get_top_10_news(api_key, topic)

    def get_news_data_from_json(self, file_name=NEWS_DATA_FILE):
        """Reading stored news articles from the specified filepath."""
        if os.path.exists(file_name):
            try:
                with open(file_name, 'r', encoding='utf-8') as json_file:
                    json_content = json.loads(json_file.read())
                    return json_content, None
            except Exception as exc:
                return None, f'Error reading file:\n{exc}'
        else:
            return None, f'No filepath such as {file_name} exists.'