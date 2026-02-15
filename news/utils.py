from newsapi import NewsApiClient
from newspaper import Article
import datetime, requests
import logging

from config import (
    NEWS_CATEGORIES, 
    NEWS_LANGUAGE, 
    NEWS_SORT_BY, 
    MAX_ARTICLES,
    MIN_ARTICLE_WORDS
)

logger = logging.getLogger(__name__)

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
    """
    SIMPLIFIED VERSION: Uses News API data directly without scraping.
    Much faster and more reliable than newspaper3k scraping.
    """
    articles, error = get_news_content(api_key, topic)
    if error:
        logger.error(f'Error fetching news content: {error}')
        return error
    
    if not articles:
        logger.warning(f"No articles found for topic: {topic}")
        return "No articles found for this topic"
    
    article_content = []
    failed_count = 0

    for article in articles:  
        # Stop if we have enough articles
        if len(article_content) >= MAX_ARTICLES:
            break

        # Get URL - skip if missing or invalid
        url = article.get('url')
        if not url or not isinstance(url, str):
            logger.warning('Skipping article with invalid URL')
            failed_count += 1
            continue

        # Get News API metadata (fast - already fetched)
        title = article.get('title', 'No Title')
        author = article.get('author', 'Unknown')
        published_at = article.get('publishedAt', 'Unknown')
        description = article.get('description', 'No description available')

        # Parse publish date
        publish_date = 'Unknown'
        if published_at and published_at != 'Unknown':
            try:
                publish_date = published_at[:10]  # Get YYYY-MM-DD
            except:
                publish_date = published_at

        try:
            article_ = Article(url)
            article_.download()
            article_.parse()

            # Validate we got good text
            if not article_.text or len(article_.text.strip()) < MIN_ARTICLE_WORDS:
                logger.warning(f"Article too short or empty: {url}")
                failed_count += 1
                continue

            # Use scraped text + News API metadata
            article_info = {
                'url': url,
                'title': title,  # From News API (reliable)
                'authors': author,  # From News API (reliable)
                'publish_date': publish_date,  # From News API (reliable)
                'summary': description,  # From News API (fast, professional)
                'text': article_.text  # From scraping (full content!)
            }

            article_content.append(article_info)
            logger.info(f"✅ Scraped: {title[:50]}...")

        except Exception as e:
            logger.warning(f'Failed to scrape {url}: {str(e)}')
            failed_count += 1
            continue
    
    logger.info(f"Fetched {len(article_content)} articles for topic: {topic}")

    if not article_content:
        return "Could not fetch any valid articles. Please try again later."
    
    return article_content