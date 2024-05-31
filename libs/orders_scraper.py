import os
import csv
from datetime import datetime
from time import sleep
from dotenv import load_dotenv
from libs.chrome_dev import ChromDevWrapper

load_dotenv()
CHROME_PATH = os.getenv("CHROME_PATH")
FIVERR_USERNAME = os.getenv("FIVERR_USERNAME")
DEBUG = os.getenv("DEBUG") == "True"
DEBUG_LOAD_NUM = int(os.getenv("DEBUG_LOAD_NUM"))


class OrdersScraper(ChromDevWrapper):
    
    def __init__(self):
        """ Initialize chrome """
        super().__init__(CHROME_PATH, start_killing=True)

        self.orders_page = f"https://www.fiverr.com/users/{FIVERR_USERNAME}/" \
            "manage_orders?source=header_nav&search_type="
        
        # Paths
        self.current_folder = os.path.dirname(os.path.abspath(__file__))
        self.project_folder = os.path.dirname(self.current_folder)
        self.ouput_folder = os.path.join(self.project_folder, "output")
        os.makedirs(self.ouput_folder, exist_ok=True)
            
    def __load_results__(self):
        """ Load all results from the page """
    
        selectors = {
            "btn_next": '.orders-load-more > a',
        }
        
        print("Loading results...")
        
        load_counter = 0
        while True:
            
            if DEBUG and load_counter >= DEBUG_LOAD_NUM:
                print("DEBUG: Load counter reached")
                break
            
            btn_next = self.count_elems(selectors["btn_next"])
            if btn_next:
                self.click(selectors["btn_next"])
                sleep(5)
                load_counter += 1
                continue
            break
    
    def __get_clean_price__(self, text: str) -> float:
        """ Clean price from text (remove extra characters and convert to float)

        Args:
            text (str): Text with the price

        Returns:
            float: Price as float
        """
        
        price = text.replace("$", "")
        return float(price)
    
    def __get_clean_date__(self, text: str) -> str:
        """ Clean date from text with the formats:
        "Jan 09", "Dec 10, 2020", "Apr 8, 2024, 2:14 PM"

        Args:
            text (str): Date in text format

        Returns:
            str: Date in format "dd/mm/yyyy"
        """
        
        # Convert date to datetime
        date_str = text
        date_parts = date_str.split(",")
        if len(date_parts) == 1:
            date = datetime.strptime(date_str, "%b %d")
            date = date.replace(year=datetime.now().year)
        elif len(date_parts) == 2:
            date = datetime.strptime(date_str, "%b %d, %Y")
        elif len(date_parts) == 3:
            date = datetime.strptime(date_str, "%b %d, %Y, %I:%M %p")
        date_str = date.strftime("%d/%m/%Y")
        return date_str
    
    def __get_order_row_general__(self, selector_row: int,
                                  selectors: dict) -> dict:
        """ Get general data from a row of done orders
        
        Args:
            selector_row (int): Selector for the row
            selectors (dict): Selectors for the row elements
        
        Returns:
            dict: Data from the order based on the selectors
        """
        
        row_data = {}
        
        # Get general data
        for selector_name, selector_value in selectors.items():
            selector_value = f"{selector_row} {selector_value}"
            row_data[selector_name] = self.get_text(selector_value)
        
        # Get order link
        selector_order_link = f"{selector_row} {selectors['order_link']}"
        order_link = self.get_attrib(selector_order_link, "href")
        row_data["order_link"] = f"https://www.fiverr.com{order_link}"
        
        # Clean row_data
        row_data["total"] = self.__get_clean_price__(row_data["total"])
        if not row_data["stars"]:
            row_data["stars"] = 0
        
        # Convert date
        row_data["date_end"] = self.__get_clean_date__(row_data["date_end"])
        
        return row_data
    
    def __get_order_row_extra__(self, selector_row: int,
                                selectors: dict, last_row: dict):
        """ Add extra data from a row to the last done order
        
        Args:
            selector_row (int): Selector for the row
            selectors (dict): Selectors for the row elements
            last_row (dict): Last row data
        """
                
        # Get data
        selector_name = f"{selector_row} {selectors['name']}"
        selector_amount = f"{selector_row} {selectors['amount']}"
        name = self.get_text(selector_name)
        amount = self.get_text(selector_amount)
            
        # Validate extra time
        if "Extend Delivery" in name:
            last_row["extend_delivery"] = 1
            
        # Increase extras amount and price
        last_row["extras_amount"] += 1
        last_row["extras_price"] += self.__get_clean_price__(amount)
        
    def __get_order_details__(self, order_url: str) -> dict:
        """ Get details from an order

        Args:
            order_url (str): URL of the order

        Returns:
            dict: Details from the order
            Structure:
            {
                "details": str,
                "description": str,
                "includes": str,
                "expected_days": int
            }
        """
        
        selectors = {
            "show_details_btn": '.activity-collapsible-title-wrapper',
            "description": '.floating-activities-block p + p',
            "includes": '.floating-activities-block ul > li',
            "expected_days": '.floating-activities-block div:nth-child(3) > p',
            "date_ordered": '.floating-activities-block div + p'
        }
        
        # Set page and load info
        self.set_page(order_url)
        self.click(selectors["show_details_btn"])
        sleep(5)
        
        # Get data
        description = self.get_text(selectors["description"])
        includes = self.get_texts(selectors["includes"])
        expected_days = self.get_text(selectors["expected_days"])
        date_ordered = self.get_text(selectors["date_ordered"])
        
        # Clean data
        expected_days = expected_days.lower()
        expected_days = expected_days.replace("days", "").replace("day", "").strip()
        expected_days = int(expected_days)
        date_ordered = date_ordered.replace("Date ordered ", "")
        description = description.replace("\n", " ").replace(",", " ")
        
        # Convert datetimes
        date_ordered = self.__get_clean_date__(date_ordered)
        
        sleep(10)
        
        return {
            "description": description,
            "includes": " | ".join(includes),
            "expected_days": expected_days,
            "date_ordered": date_ordered
        }
    
    def extract_orders(self, order_type: str) -> list:
        """ Get data from done orders
        
        Args:
            order_type (str): Type of orders to get (done, cancelled)
        
        Returns:
            list: List of done orders
            Structure:
            [
                {
                    "buyer": str,
                    "extras_amount": int,
                    "extras_price": float,
                    "extend_delivery": int
                    "gig": str,
                    "total": float,
                    "stars": int,
                    "status": str,
                    "order_link": str,
                }
            ]
        
        """
        
        print("Getting done orders...")
        
        csv_filename = f"{order_type}_orders.csv"
        csv_path = os.path.join(self.ouput_folder, csv_filename)
        
        selectors = {
            "row": ".table > div",
            "general": {
                "buyer": '.username',
                "gig": '.gig-name',
                "order_link": '.gig-name > a',
                "date_end": '.delivered-at',
                "total": '.total',
                "stars": '.review .order-review-star',
                "status": '.status'
            },
            "extra": {
                "name": "[title]",
                "amount": ".order-extra-price"
            }
        }
        
        # Set page
        page = self.orders_page + order_type
        self.set_page(page)
        sleep(2)
        self.__load_results__()
        
        rows_data = []
        rows_num = self.count_elems(selectors["row"])
        for row_index in range(rows_num)[1:]:
            selector_row = f"{selectors['row']}:nth-child({row_index + 1})"
            selector_row_extras = f"{selector_row}.sub-row"
            
            # Skip spacers
            row_class = self.get_attrib(selector_row, "class")
            if "spacer" in row_class:
                continue
            
            is_extra_row = self.get_texts(selector_row_extras)
            if is_extra_row:
                last_row = rows_data[-1]
                self.__get_order_row_extra__(
                    selector_row,
                    selectors["extra"],
                    last_row
                )
            else:
                row_data = self.__get_order_row_general__(
                    selector_row,
                    selectors["general"]
                )
                
                # TODO: skip already saved orders
                
                # Add extrad default data
                row_data["extras_amount"] = 0
                row_data["extras_price"] = 0
                row_data["extend_delivery"] = 0
                
                rows_data.append(row_data)
                
        print(f"{len(rows_data)} orders found")
        
        # Extract details from each order
        for row_data in rows_data:
            
            # Logs
            order_url = row_data["order_link"]
            order_index = rows_data.index(row_data) + 1
            counter = f"({order_index} / {len(rows_data)})"
            print(f"Getting details from order {counter}: {order_url}...")
            
            # Extract data
            order_details = self.__get_order_details__(order_url)
            row_data.update(order_details)
            
            # Short by keys
            row_data = {key: row_data[key] for key in sorted(row_data)}
            row_values = list(row_data.values())

            # Write data in csv
            with open(csv_path, "a", newline="", encoding="utf-8") as file:
                
                csv_writer = csv.writer(file)
                
                # Write header if its first row
                if order_index == 1:
                    header = list(row_data.keys())
                    csv_writer.writerow(header)
                
                # Write row
                csv_writer.writerow(row_values)
        
        print(f"Data saved in {csv_path}\n")
