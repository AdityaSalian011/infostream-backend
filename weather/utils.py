import requests, json

# def store_weather_api(api_key ,city_name, file_name):
def get_weather_api(api_key ,city_name):
    """Recieves today's weather condition based on city name:
    Parameters: 
        - api_key -> uses default api key if not provided by user
        - city_name -> weather condition for particular city.
        - file_name -> file path to store these information.

    Returns:
        - Error(if any else None).
    """

    BASE_URL = 'https://api.openweathermap.org/data/2.5/weather'
    API_KEY = api_key
    CITY = city_name.strip()

    params = {
        'q': CITY,
        'appid': API_KEY,
        'units': 'metric'
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=5).json()
    except requests.exceptions.ConnectTimeout:
        return 'Weather API request timed Out. Try again Later.'

    error = check_response_validity(response)
    if error:
        return error['error']

    weather_info = get_weather_info(response)
    weather_icon_url = get_weather_icon_url(response)

    return {
        'weather_info': weather_info,
        'weather_icon_url': weather_icon_url
    }

    # store_weather_data(weather_data, file_name)

def get_weather_info(response):
    """Returns a dictionary
    Stores weather status i.e cloudy, windy etc
    Temperature
    Real temperature(feels like).
    And humidty"""

    weather_info = {}
    weather_info['status'] = response['weather'][0]['description']
    weather_info['temp'] = response['main']['temp']
    weather_info['feels_like'] = response['main']['feels_like']
    weather_info['humidity'] = response['main']['humidity']

    return weather_info

def get_weather_icon_url(response):
    """Returns a 2x sized weather icon based on weather condition."""
    icon_code = response['weather'][0]['icon']
    icon_url = f'http://openweathermap.org/img/wn/{icon_code}@2x.png'

    return icon_url

def check_response_validity(response):
    """Checks if request object has status code "200" 
        If not returns an error message
        e.g. Invalid city name.
    """
    if response.get('cod') != 200:
        return {'error': response['message']}
    return None

def store_weather_data(weather_data, file_name):
    """Stores weather information as a json formatted file."""
    with open(file_name, 'w', encoding='utf-8') as f:
        json_content = json.dumps(weather_data, indent=4)
        f.write(json_content)