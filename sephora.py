from bs4 import BeautifulSoup
import pandas as pd
import json 
import httpx
import math

BASE = 'https://www.sephora.com'
CLINIQUE_URL = 'https://www.sephora.com/brand/clinique'
RESPONSE = {
    "product_name": [],
    "review": [],
    "review_count": [],
    "url": [],
    "sku": [],
    "product_id": [],
}
DATA = {
    'num_pages': 3, 
}
QUERY = '?currentPage='
DIRECTORY = './downloads/'
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/109.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1", 
    "Referer": "http://www.google.com/", # this made it work 
    'Accept-Encoding': 'gzip, deflate, br', # this made it work 
    }
# HEADERS = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
#     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
#     "Accept-Language": "en-US,en;q=0.5",
#     "DNT": "1",  # Do Not Track Request Header
#     "Connection": "close",
# }

class Sephora:
    def get_pages_num(self, soup: BeautifulSoup):
        try: 
            num_products = int(soup.find(
                'p', 
                {"data-at": 'number_of_products'}
            ).get_text().split()[0])
            num_pages = math.ceil(num_products/60)
        except AttributeError:
            num_pages = 124
        return num_pages, num_products

    def _scrape(self, export=0):
        print('---------> Started scraping products <---------')
        page = httpx.get(CLINIQUE_URL, headers=HEADERS, timeout=30.0)
        soup = BeautifulSoup(page.text, 'html.parser')
        DATA['num_pages'], num_products = self.get_pages_num(soup)
        # num_products = 124

        with httpx.Client(limits=httpx.Limits(max_connections=20), timeout=httpx.Timeout(60.0, connect=60.0)) as client:
            for k in range(DATA['num_pages']):
                new_url = CLINIQUE_URL+QUERY+str(k+1)
                page = client.get(new_url, headers=HEADERS)
                soup = BeautifulSoup(page.text, 'html.parser')
                products_data = json.loads(soup.find(
                    'script', 
                    {'id': 'linkStore'}
                ).get_text())
                products = products_data['page']['nthBrand']['products']
                for i, product in enumerate(products):
                    if product['displayName'] in RESPONSE['product_name']:
                        continue 
                    else:
                        RESPONSE['review'].append(product['rating'])
                        RESPONSE['review_count'].append(product['reviews'])
                        RESPONSE['sku'].append(product['currentSku']['skuId'])
                        RESPONSE['product_id'].append(product['productId'])
                        RESPONSE['product_name'].append(str(product['displayName']).replace('\u2122', ''))
                        RESPONSE['url'].append(BASE + product['targetUrl'])
                print(f'Progress ({round(len(RESPONSE["product_id"])/num_products, 2) * 100}%): {len(RESPONSE["product_id"])}/{num_products}')
                new_url = CLINIQUE_URL+QUERY+str(k+1)
                page = client.get(new_url, headers=HEADERS)
                soup = BeautifulSoup(page.text, 'html.parser')
        print('---------> Scraping Complete products <---------')
        if export:
            with open(DIRECTORY+'sephora_data.json', 'w') as f:
                json.dump(RESPONSE, f)
            df = pd.DataFrame(RESPONSE)
            df.to_excel(DIRECTORY+ 'sephora_data.xlsx', index=False)
            print(f'Sephore scraping done ({round(len(RESPONSE["product_id"])/num_products, 2) * 100}%): {len(RESPONSE["product_id"])}/{num_products}')
        return RESPONSE

    def scrape(self, export=0):
        res = self._scrape(export=export)
        return res

if __name__ == "__main__":
    sephora = Sephora()
    sephora.scrape(export=1)


