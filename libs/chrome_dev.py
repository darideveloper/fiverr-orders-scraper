import os
import sys
import psutil
from time import sleep
import PyChromeDevTools


class ChromDevWrapper():
    
    def __init__(self, chrome_path, port: int = 9222,
                 proxy_host: str = "", proxy_port: str = "",
                 start_chrome: bool = True, start_killing: bool = True):
        """ Open chrome and conhect using PyChromeDevTools

        Args:
            port(int): port or chrome running in debug mode
            proxy_host(str, optional): Proxy ip. Defaults to "".
            proxy_port(str, optional): Proxy port. Defaults to "".
            start_chrome(bool, optional): Open new chrome instance. Defaults to True.
            start_killing(bool, optional): Kill (true) chrome before start.
                Defaults to True.
        """
        
        # Validate chrome path
        if not os.path.exists(chrome_path):
            print(f"Chrome path not found: {chrome_path}")
            sys.exit()
        
        if start_killing:
            self.quit()
            
        if start_chrome:
            command = f'"{chrome_path}" --remote-debugging-port={port} '
            command += '--remote-allow-origins=*'
            if proxy_host != "" and proxy_port != "":
                # Start chrome with proxies
                command += f' --proxy-server={proxy_host}:{proxy_port}'
                
            os.popen(command)
                
            sleep(1)
        
        self.base_wait_time = 2
        
        try:
            self.chrome = PyChromeDevTools.ChromeInterface(port=port)
        except Exception:
            print(
                "Chrome is not open",
                "Please open chrome with the custom shorcut and try again."
            )
            sys.exit(1)
            
        self.chrome.Network.enable()
        self.chrome.Page.enable()
        
    def count_elems(self, selector: str) -> int:
        """ Count elemencts who match with specific css selector

        Args:
            selector(str): css selector
            
        Returns:
            int: number of elements
        """
        
        script = f'document.querySelectorAll("{selector}").length'
        response = self.chrome.Runtime.evaluate(expression=script)
        try:
            return response[0]['result']["result"]["value"]
        except Exception:
            return 0
    
    def set_page(self, page: str):
        """ Navigate to specific page

        Args:
            page(str): url to navigate
        """
        
        self.chrome.Page.navigate(url=page)
        self.chrome.wait_event("Page.frameStoppedLoading", timeout=60)
        sleep(self.base_wait_time)
        
    def delete_cookies(self):
        """ Delete all cookies in chrome
        """
        
        self.chrome.Network.clearBrowserCookies()
        sleep(self.base_wait_time)
    
    def set_cookies(self, cookies: list):
        """ Set cookies in chrome

        Args:
            cookies(list): cookies to set with name, value, domain, path,
                secure, httpOnly and sameSite
        """
        
        for cookie in cookies:
            try:
                self.chrome.Network.setCookie(
                    name=cookie["name"],
                    value=cookie["value"],
                    domain=cookie["domain"],
                    path=cookie["path"],
                    secure=cookie["secure"],
                    httpOnly=cookie["httpOnly"],
                    sameSite=cookie["sameSite"]
                )
            except Exception:
                pass
                
        sleep(self.base_wait_time)
            
    def send_data_js(self, selector: str, data: str):
        """ Send data to specific input, with js

        Args:
            selector(str): css selector
            data(str): data to send
        """
        
        script = f'document.querySelector("{selector}").value = "{data}";'
        self.chrome.Runtime.evaluate(expression=script)
        sleep(self.base_wait_time)
        
    def send_data(self, selector: str, data: str):
        """ Send data to specific input using chrome api

        Args:
            selector(str): css selector
            data(str): data to send
        """
        
        # Get input
        element = self.chrome.DOM.getDocument()[0]["result"]["root"]["nodeId"]
        result = self.chrome.DOM.querySelector(nodeId=element, selector=selector)
        node_id = result[0]["result"]["nodeId"]
        
        # Focus on the input text box
        self.chrome.DOM.focus(nodeId=node_id)
        
        # Type text
        for char in data:
            self.chrome.Input.dispatchKeyEvent(
                type="char",
                text=char,
                unmodifiedText=char
            )
        sleep(self.base_wait_time)
                
    def click(self, selector: str):
        """ Click on specific element

        Args:
            selector(str): css selector
        """
        
        script = f'document.querySelector("{selector}").click();'
        self.chrome.Runtime.evaluate(expression=script)
        sleep(self.base_wait_time)
        
    def get_text(self, selector: str) -> str:
        """ Get text of visible element

        Args:
            selector(str): css selector
            
        Returns:
            str: text of element
        """
        
        script = f'document.querySelector("{selector}").textContent'
        response = self.chrome.Runtime.evaluate(expression=script)
        try:
            return response[0]['result']["result"]["value"].strip()
        except Exception:
            return ""
        
    def get_texts(self, selector: str) -> list:
        """ Get texts of visible elements

        Args:
            selector(str): css selector
            
        Returns:
            list: texts of elements
        """
        
        script = 'values = [];'
        script += f'document.querySelectorAll("{selector}")'
        script += '.forEach(elem => values.push(elem.textContent));'
        script += 'values;'
        response = self.chrome.Runtime.evaluate(expression=script, returnByValue=True)
        try:
            texts = list(map(
                lambda text: text.strip(),
                response[0]['result']["result"]["value"]
            ))
        except Exception:
            return []
        return texts
        
    def get_attrib(self, selector: str, attrib: str) -> str:
        """ Get specific attribute from visible element

        Args:
            selector(str): css selector
            attrib(str): attribute to get
            
        Returns:
            str: attribute value
        """
        
        script = f'document.querySelector("{selector}").getAttribute("{attrib}")'
        response = self.chrome.Runtime.evaluate(expression=script)
        try:
            return response[0]['result']["result"]["value"].strip()
        except Exception:
            return ""
        
    def get_attribs(self, selector: str, attrib: str) -> list:
        """ Get specific attribute from visible elements

        Args:
            selector(str): css selector
            attrib(str): attribute to get
            
        Returns:
            list: attribute values
        """
        
        script = 'values = [];'
        script += f'document.querySelectorAll("{selector}")'
        script += f'.forEach(elem => values.push(elem.getAttribute("{attrib}")));'
        script += 'values;'
        response = self.chrome.Runtime.evaluate(expression=script, returnByValue=True)
        
        values = []
        try:
            values = list(map(
                lambda value: value.strip(),
                response[0]['result']["result"]["value"]
            ))
        except Exception:
            pass
        return values
        
    def quit(self, kill_chrome: bool = True):
        """ Close chrome and conexion

        Args:
            kill_chrome(bool, optional): Kill(true) all chrome windows. Defaults to True.
        """
        
        if kill_chrome:
            for process in psutil.process_iter(['pid', 'name']):
                if 'chrome' in process.info['name']:
                    try:
                        process.kill()
                    except Exception:
                        pass
                    
    def execute_script(self, script: str):
        """ Run js script and get returns

        Args:
            script(str): _description_
        """
        
        response = self.chrome.Runtime.evaluate(expression=script)
        sleep(self.base_wait_time)
        if response[0]['result']["result"]["type"] == "undefined":
            return None
        return response[0]['result']["result"]["value"]
    
    def get_prop(self, selector: str, prop: str) -> str:
        """ Get specific propery from visible element

        Args:
            selector(str): css selector
            prop(str): property to get
            
        Returns:
            str: property value
        """
        
        script = f'document.querySelector("{selector}").{prop}'
        response = self.chrome.Runtime.evaluate(expression=script)
        try:
            return response[0]['result']["result"]["value"].strip()
        except Exception:
            return ""
    
    def set_prop(self, selector: str, prop: str, value: str):
        """ Set specific propery from visible element

        Args:
            selector(str): css selector
            prop(str): property to get
            value(str): value to set
        """
        
        script = f'document.querySelector("{selector}").{prop} = "{value}";'
        self.chrome.Runtime.evaluate(expression=script)
        
    def set_zoom(self, zoom: float = 1):
        """ Change zoom in the page.

        Args:
            zoom(float, optional): Zoom betweenb 0 and 1. Defaults to 1.
        """
        
        script = f'document.body.style.zoom = "{zoom*100}%";'
        self.chrome.Runtime.evaluate(expression=script)
        
    def go_down(self):
        """ Scroll down in the page
        """
        
        script = "window.scrollTo(0, document.body.scrollHeight);"
        self.chrome.Runtime.evaluate(expression=script)
        