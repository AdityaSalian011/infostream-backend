from weather.utils import get_weather_api
import os
from dotenv import load_dotenv

load_dotenv()
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')

class WeatherAPI:
    # def store_weather_info(self, api_key, city_name, file_name=WEATHER_DATA_FILE):
    def get_weather_info(self, city_name, api_key=None):
        """Stores weather data for specified city at the desired file path(JSON format)."""
        api_key = api_key or WEATHER_API_KEY
        return get_weather_api(api_key, city_name)