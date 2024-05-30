from libs.orders_scraper import OrdersScraper

# Initialize scraper
scraper = OrdersScraper()
scraper.extract_orders(order_type="completed")
scraper.extract_orders(order_type="cancelled")

print()