# config.py - Central configuration file

# News API Settings
NEWS_CATEGORIES = [
    'general',
    'business',
    'entertainment',
    'health',
    'science',
    'sports',
    'technology'
]

NEWS_LANGUAGE = 'en'
NEWS_SORT_BY = 'relevancy'
MAX_ARTICLES = 10
MIN_ARTICLE_WORDS = 50

# File Paths
USER_DATA_FILE = 'dir/user_dir/userInfo.json'
NEWS_DATA_FILE = 'dir/news_dir/newsInfo.json'
WEATHER_DATA_FILE = 'dir/weather_dir/weatherInfo.json'
STOCK_DATA_FILE = 'dir/stock_dir/stockInfo.json'

# Template Settings
TEMPLATE_FOLDER = 'templates'
HTML_TEMPLATE = 'index-v2.html'
RENDERED_FILE = 'rendered.html'
OUTPUT_PDF = 'output.pdf'

# Stock Settings
STOCK_MARKETS = {
    'NIFTY 50': '^NSEI',
    'SENSEX': '^BSESN',
    'GOLD': 'GC=F',
    'SILVER': 'SI=F',
    'USD/INR': 'USDINR=X'
}
STOCK_PERIOD = '5d'

# GUI Settings
GUI_COLORS = {
    'bg_main': '#2c2c2c',
    'bg_entry': '#212121',
    'fg_entry': '#00FF00',
    'fg_label': 'white',
    'fg_warning': '#ffcc00',
    'btn_bg': '#007acc',
    'btn_active': '#005f99'
}

GUI_FONTS = {
    'title': ('Arial', 16, 'bold'),
    'label': ('Arial', 14),
    'entry': ('Arial', 14),
    'button': ('Arial', 14, 'bold'),
    'loading': ('Arial', 16, 'bold'),
    'radio': ('Arial', 15),
    'warning': ('Arial', 10)
}

# Email Settings
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
FROM_EMAIL = 'adityasalian865@gmail.com'

# Validation Patterns
USERNAME_PATTERN = r'^[a-zA-Z0-9_]{3,20}$'