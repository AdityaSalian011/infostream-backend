from stock.utils import get_stock_api

class StockAPI:
    # def store_stock_data(self, file_name=STOCK_DATA_FILE):
    def get_stock_data(self):
        """Stores stock data based on time period."""
        return get_stock_api()