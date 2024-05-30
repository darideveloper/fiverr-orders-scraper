from libs.orders_scraper import OrdersScraper

# Initialize scraper
scraper = OrdersScraper()
orders_completed = scraper.get_orders(order_type="completed")
orders_cancelled = scraper.get_orders(order_type="cancelled")

print()