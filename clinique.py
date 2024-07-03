import httpx
from bs4 import BeautifulSoup
import json
import time
import asyncio
import pandas as pd

p = time.time()
BASE = "https://www.clinique.com"
PRODUCT_CAT_URLS = [
    "https://www.clinique.com/mens",
    "https://www.clinique.com/products/1577/fragrance",
    "https://www.clinique.com/makeup-clinique",
    "https://www.clinique.com/skincare-all",
]
reviews = {
    "product_name": [],
    "review": [],
    "review_count": [],
    "url": [],
    "sku": [],
}
DIRECTORY = './downloads/'

class Clinique:
    def site_map(self, export=0):
        """
        Scrapes all products URLs from Clinique and return a dict with all product links by categories
        """
        site = dict(
            zip(
                [url.replace(BASE + "/", "") for url in PRODUCT_CAT_URLS],
                list([[] for _ in range(len(PRODUCT_CAT_URLS))]),
            )
        )
        products = 0
        with httpx.Client() as client:
            for url in PRODUCT_CAT_URLS:
                data = {
                    "product_urls": [],
                    "count_products": 0,
                    "products_collected": 0,
                }
                page = client.get(url)
                soup = BeautifulSoup(page.text, "html.parser")
                # TODO: class is not the best way for a generic long term app. Find a better way to crawl through
                p = soup.find(
                    "ul",
                    class_="w-full grid gap-x-6 sm:gap-y-4 md:gap-y-8 px-0 sm:max-md:grid-cols-1 md:max-lg:grid-cols-2 [&>li]:overflow-x-auto lg:grid-cols-3",
                )
                li = p.find("li")
                html_list = li.find_next_siblings()
                data["count_products"] = len(html_list)
                for html in html_list:
                    # Removes ads since they have an "overflow-hidden" class on the first 50 characters
                    if "overflow-hidden" in str(html)[:50]:
                        continue
                    u = html.find("a").get("href")
                    if BASE in u:
                        continue
                    else:
                        product_url = BASE + str(u)
                    data["product_urls"].append(product_url)
                products += len(data["product_urls"])
                data["products_collected"] = len(data["product_urls"])
                site[url.replace(BASE + "/", "")] = data
        site["total_products"] = products

        if export:
            with open(DIRECTORY + "clinique_site_map.json", "w") as f:
                json.dump(site, f)
        return site

    async def get_page(self, client: httpx.Client, url, i):
        response = await client.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        js = soup.find("script", {"type": "application/ld+json"})
        js = json.loads(js.get_text())
        try:
            reviews["review"].append(float(js["aggregateRating"]["ratingValue"]))
            reviews["review_count"].append(int(js["aggregateRating"]["reviewCount"]))
        except KeyError:
            fail = {js["name"]: url}
            print(f'Failed: {fail}')
            return fail
        reviews["product_name"].append(js["name"])
        reviews["url"].append(url)
        reviews["sku"].append(js["sku"])
        print(f'{i}) Product Done: {js["name"]}')

    async def main(self, reviews, export=0):
        site = self.site_map(export)
        urls = [
            z
            for k, v in site.items()
            if k != "total_products"
            for z in v["product_urls"]
        ]
        async with httpx.AsyncClient(limits=httpx.Limits(max_connections=20), timeout=httpx.Timeout(10.0, connect=60.0)) as client:
            tasks = []
            print('---------> Started scraping products <---------')
            for i, url in enumerate(urls):
                tasks.append(asyncio.create_task(self.get_page(client, url, i)))
            failed = await asyncio.gather(*tasks)
            print('---------> Scraping Complete products <---------')
            if export:
                with open(DIRECTORY + "clinique_reviews.json", "w") as f:
                    json.dump(reviews, f)
                with open(DIRECTORY + "clinique_failed.json", "w") as f:
                    json.dump(failed, f)
                df = pd.DataFrame(reviews)
                df.to_excel(DIRECTORY + "clinique_reviews.xlsx", index=False)
            return reviews, failed

    def run(self, export=0):
        r, f = asyncio.run(self.main(reviews, export=export))
        return r, f


# if __name__ == "__main__":
#     clinique = Clinique()
#     clinique.run(1)
#     print(f"Duration: {round((time.time() - p), 3)}")
