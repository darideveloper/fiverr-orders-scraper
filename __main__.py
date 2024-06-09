from libs.orders_scraper import OrdersScraper

# Initialize scraper
option = input("Scrape completed (1) or cancelled (2) orders? ")
scraper = OrdersScraper()
if option == "1":
    scraper.extract_orders(order_type="completed")
elif option == "2":
    scraper.extract_orders(order_type="cancelled")
else:
    print("Invalid option")
    exit()

print()