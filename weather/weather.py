from utils import get_weather_api
from key import my_weather_api_key
import json, os

from config import WEATHER_DATA_FILE

class WeatherAPI:
    # def store_weather_info(self, api_key, city_name, file_name=WEATHER_DATA_FILE):
    def get_weather_info(self, city_name, api_key=my_weather_api_key):
        """Stores weather data for specified city at the desired file path(JSON format)."""
        return get_weather_api(api_key, city_name)
    
    def get_weather_data_from_json(self, file_name=WEATHER_DATA_FILE):
        """Reading stored weather data from the specified filepath."""
        if os.path.exists(file_name):
            try:
                with open(file_name, 'r', encoding='utf-8') as json_file:
                    json_content = json.loads(json_file.read())
                    return json_content, None
            except Exception as exc:
                return None, f'Error reading file:\n{exc}'
        else:
            return None, f'No filepath such as {file_name} exists.'