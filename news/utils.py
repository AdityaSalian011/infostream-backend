from newsapi import NewsApiClient
from newspaper import Article
import datetime, json, requests

from config import (
    NEWS_CATEGORIES, 
    NEWS_LANGUAGE, 
    NEWS_SORT_BY, 
    MAX_ARTICLES,
    MIN_ARTICLE_WORDS
)

def get_from_to_dates():
    """A helper function to retrieve today and yesterday datetime."""
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    return today, yesterday

def get_news_content(api_key, topic, language=NEWS_LANGUAGE, sort_by=NEWS_SORT_BY):
    """
    A helper function to get news articles based on the topic.
    parameters: 
        - Asks for news api key(if not provided uses default).
        - news topic to generate articles for.
        - language -> by default english.
        - sroted by -> most relevant   
    output:
        - 1. A list of articles generated based on the news topic and other parameters.
        - 2. An error (if any).
    """
    today, yesterday = get_from_to_dates()

    news_api = NewsApiClient(api_key=api_key)

    try:
        if topic in NEWS_CATEGORIES:
            content = news_api.get_top_headlines(
                category=topic,
                language=language
            )
        
        else:
            content = news_api.get_everything(
                q=topic,
                language=language,
                sort_by=sort_by,
                from_param=str(yesterday),
                to=str(today)
            )


        if content.get('status') != 'ok':
            """If there is an error in generating news content
                i.e. invalid api key etc. we will get an error"""
            return None, content.get('message', 'Unknown error from NewsAPI')
    
    except requests.exceptions.RequestException as e:
        """Handling network error"""
        return None, f'Network error: {e}'
    except Exception as e:
        return None, f'Unexpected error: {e}'

    return content['articles'], None

# def store_top_10_news(api_key, topic, file_name):
def get_top_10_news(api_key, topic):
    """Stores top 10(if available) news article data inside specified filepath."""
    articles, error = get_news_content(api_key, topic)
    if error:
        return error
    
    article_content = []
    for article in articles:
        if len(article_content) == MAX_ARTICLES:
            break
        url = article['url']
        try:
            article_ = Article(url)
            init_article_methods(article=article_)

            is_valid_text = check_valid_article_text(article=article_)
            if is_valid_text:

                article_info = store_article_info(url, article=article_)
                article_content.append(article_info)

        except Exception as e:
            print(f'Failed to scrap data as exception occured\n{e}')
            continue
    
    return article_content
    # store_article_in_json(article=article_content, file_name=file_name)

def init_article_methods(article):
    """A helper function to initialize article object's methods."""
    article.download()
    article.parse()
    article.nlp()

def store_article_info(url, article):
    """A helper function to store data scrapped through article object"""
    article_info = {
        'url': url,
        'title': article.title,
        'authors': article.authors[0] if article.authors else None,
        'publish_date': str(article.publish_date.date()) if article.publish_date else None,
        'summary': article.summary,
        'text': article.text
    }
    return article_info

def check_valid_article_text(article):
    """A helper function to check articles' text(main news content) and summary validity"""
    article_text = article.text.strip()
    article_summary = article.summary.strip()
    if len(article_text.split()) < MIN_ARTICLE_WORDS or len(article_text.split()) <= len(article_summary.split()):
        """If len of article text is less than 50 OR if it's length is <= article summary.  Return False"""
        return False
    else:
        return True
    
def store_article_in_json(article, file_name):
    """A helper function to store news article data inside the specified file.
        File is stored as a json format. For easy access and retieve of data.
    """
    with open(file_name, 'w', encoding='utf-8') as json_file:
        json_content = json.dumps(article, indent=4)
        json_file.write(json_content)