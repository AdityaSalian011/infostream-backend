from stock.utils import get_stock_api
import json, os

from config import STOCK_DATA_FILE

class StockAPI:
    # def store_stock_data(self, file_name=STOCK_DATA_FILE):
    def get_stock_data(self):
        """Stores stock data based on time period."""
        return get_stock_api()
    
    def get_stock_data_from_json(self, file_name=STOCK_DATA_FILE):
        """Reading stored stock data from the specified filepath."""
        if os.path.exists(file_name):
            try:
                with open(file_name, 'r', encoding='utf-8') as json_file:
                    json_content = json.loads(json_file.read())
                    return json_content, None
            except Exception as exc:
                return None, f'Error reading file:\n{exc}'
        else:
            return None, f'No filepath such as {file_name} exists.'