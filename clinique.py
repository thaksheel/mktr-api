import httpx
from bs4 import BeautifulSoup
import json
import time
import asyncio
import pandas as pd
import re
from datetime import datetime
import copy

p = time.time()
BASE = "https://www.clinique.com"
PRODUCT_CAT_URLS = [
    "https://www.clinique.com/mens",
    "https://www.clinique.com/products/1577/fragrance",
    "https://www.clinique.com/makeup-clinique",
    "https://www.clinique.com/skincare-all",
]
clinique_rating = {
    "product_name": [],
    "product_cat": [],
    "sku": [],
    "review": [],
    "review_count": [],
    "url": [],
}
reviews_template = {
    "sku": [],
    # 'url': [],
    "is_staff_reviewer": [],
    "is_verified_buyer": [],
    "is_verified_reviewer": [],
    "helpful_votes": [],
    "not_helpful_votes": [],
    "rating": [],
    "helpful_score": [],
    "comments": [],
    "headline": [],
    "nickname": [],
    # properties
    "age": [],
    "gender": [],
    "incentive": [],
    "skinconcerns": [],
    "skintype": [],
    "cliniquecustomerfor": [],
    "smartrewards2": [],
    # end
    "locale": [],
    "location": [],
    "created_date": [],
    "updated_date": [],
    "bottom_line": [],
    "product_page_id": [],
    "upc": [],
    "gtin": [],
    "merchant_response": [],
    "merchant_response_date": [],
    "disclosure_code": [],
}
properties = [
    "smartrewards2",
    "age",
    "gender",
    "skinconcerns",
    "skintype",
    "cliniquecustomerfor",
    "incentive",
]
DIRECTORY = "./downloads/"
PRODUCT_CAT = {}


class Clinique:
    def get_response(self, client: httpx.Client, url):
        return client.get(url).json()

    def process_response(self, response, reviews, sku, url):
        for _, res in enumerate(response):
            reviews["sku"].append(sku)
            # processing badges:  {"is_staff_reviewer": false,"is_verified_buyer": false,"is_verified_reviewer": true},
            for k, v in res["badges"].items():
                reviews[k].append(v)
            # processing metrics "metrics": {"helpful_votes": 3,"not_helpful_votes": 0,"rating": 5,"helpful_score": 1835}
            for k, v in res["metrics"].items():
                reviews[k].append(v)
            # processing details: contains comments data and user data
            for k, v in res["details"].items():
                if k == "properties":
                    # TODO: add a way to check list len here
                    collected_keys = []
                    reject = [
                        "fragrancetype",
                        "pros",
                        "cons",
                        "hairtexture",
                        "describeyourself",
                        "bestuses",
                        "brand_base_url",
                    ]
                    for seg in v:
                        if seg["key"] in reject:
                            continue
                        if seg["key"] == "wasthisreviewedaspartofasweepstakesorcontest":
                            reviews["incentive"].append(str(seg["value"][0]))
                            collected_keys.append("incentive")
                        else:
                            if len(seg["value"]) == 1:
                                reviews[seg["key"]].append(str(seg["value"][0]))
                                collected_keys.append(seg["key"])
                            else:
                                reviews[seg["key"]].append(", ".join(seg["value"]))
                                collected_keys.append(seg["key"])
                    for p in properties:
                        if p not in collected_keys:
                            reviews[p].append("")
                else:
                    if (
                        k == "created_date"
                        or k == "updated_date"
                        or k == "merchant_response_date"
                    ):
                        time_stamp = datetime.fromtimestamp((v / 1000))
                        time_stamp = time_stamp.strftime("%Y-%m-%d %H:%M:%S")
                        reviews[k].append(time_stamp)
                    else:
                        if k in reviews:
                            reviews[k].append(v)
            for m in ["merchant_response", "merchant_response_date", "disclosure_code"]:
                if m not in res["details"]:
                    reviews[m].append("")
            for k, v in reviews.items():
                base = len(reviews["sku"])
                if base != len(v):
                    reviews[k].append("")
        return reviews

    def site_map(self, export=0):
        """
        Scrapes all products URLs from Clinique and return a dict with all product links by categories
        """
        site = dict(
            zip(
                [re.search(r"/([^/]*)$", url).group(1) for url in PRODUCT_CAT_URLS],
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
                site[re.search(r"/([^/]*)$", url).group(1)] = data
        site["total_products"] = products

        if export:
            with open(DIRECTORY + "clinique_site_map.json", "w") as f:
                json.dump(site, f)
        return site

    def scrape_reviews(self, urls):
        base_url = "https://display.powerreviews.com/m/"
        api_key = "apikey=528023b7-ebfb-4f03-8fee-2282777437a7&_noconfig=true"
        requests_count = 0
        skipped = []
        clinique_reviews = copy.deepcopy(reviews_template)
        product_ids = []
        skus = clinique_rating["sku"]

        with httpx.Client() as client:
            for i, url in enumerate(urls):
                product_id = int(
                    str(url).strip("https://www.clinique.com/").split("/")[2]
                )
                product_url = f"166973/l/en_US/product/{product_id}/reviews?"
                data_url = base_url + product_url + api_key
                # print(data_url)
                if product_id in product_ids:
                    skipped.append(url)
                    print(i, url)
                    continue

                response = self.get_response(client, data_url)
                requests_count += 1
                num_results = response["paging"]["total_results"]
                page_size = response["paging"]["page_size"]
                response = response["results"][0]["reviews"]
                reviews_length = len(response)
                current_reviews = self.process_response(
                    response, clinique_reviews, skus[i], url
                )

                while True:
                    next_url = f"166973/l/en_US/product/{product_id}/reviews?apikey=528023b7-ebfb-4f03-8fee-2282777437a7&_noconfig=true&paging.from={page_size}&paging.size=25"
                    response = self.get_response(client, (base_url + next_url))[
                        "results"
                    ][0]["reviews"]
                    current_reviews = self.process_response(
                        response, clinique_reviews, skus[i], url
                    )
                    reviews_length += len(response)
                    page_size = reviews_length
                    requests_count += 1

                    if reviews_length >= num_results:
                        break
                product_ids.append(product_id)
                print(
                    f"Reviews Scraping done: {product_id}, Progress: {len(product_ids)}/{len(urls)}"
                )
        with open(DIRECTORY + "clinique_reviews.json", "w") as f:
            json.dump(clinique_reviews, f)
        df = pd.DataFrame(clinique_reviews)
        df.to_excel(DIRECTORY + "clinique_reviews.xlsx", index=False)
        
        return clinique_reviews

    async def get_page(self, client: httpx.Client, url, i, PRODUCT_CAT):
        response = await client.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        js = soup.find("script", {"type": "application/ld+json"})
        try:
            js = json.loads(js.get_text())
            clinique_rating["review"].append(
                float(js["aggregateRating"]["ratingValue"])
            )
            clinique_rating["review_count"].append(
                int(js["aggregateRating"]["reviewCount"])
            )
        except AttributeError:
            print(f"Attribute Error Failed: {url}")
            return {"attributeError": url}
        except KeyError:
            fail = {js["name"]: url}
            print(f"Key Error Failed: {fail}")
            return fail
        clinique_rating["product_name"].append(
            str(js["name"]).replace("\u2122", "").replace("&trade;", "")
        )
        clinique_rating["url"].append(url)
        clinique_rating["sku"].append(js["sku"])
        clinique_rating["product_cat"].append(PRODUCT_CAT[url])
        print(f'{i}) Product Done: {js["name"]}')

    async def scrape_rating(self, reviews, export=0, limit=-1):
        site = self.site_map(export)
        urls = [
            z
            for k, v in site.items()
            if k != "total_products"
            for z in v["product_urls"]
        ]
        PRODUCT_CAT = {
            z: k
            for k, v in site.items()
            if k != "total_products"
            for z in v["product_urls"]
        }

        if limit > 0:
            urls = urls[:limit]
        async with httpx.AsyncClient() as client:
            tasks = []
            print("---------> Started scraping products <---------")
            for i, url in enumerate(urls):
                tasks.append(
                    asyncio.create_task(self.get_page(client, url, i, PRODUCT_CAT))
                )
            failed = await asyncio.gather(*tasks)

            print("---------> Scraping Complete products <---------")
            if export:
                with open(DIRECTORY + "clinique_rating.json", "w") as f:
                    json.dump(reviews, f)
                with open(DIRECTORY + "clinique_failed.json", "w") as f:
                    json.dump(failed, f)
                df = pd.DataFrame(reviews)
                df.to_excel(DIRECTORY + "clinique_rating.xlsx", index=False)
            return reviews, failed, urls

    def run(self, export=0, limit=-1):
        r, f, urls = asyncio.run(
            self.scrape_rating(clinique_rating, export=export, limit=limit)
        )
        clinique_reviews = self.scrape_reviews(urls)

        return r, f, clinique_reviews


if __name__ == "__main__":
    clinique = Clinique()
    clinique.run(1)
    print(f"Duration: {round((time.time() - p), 3)}s")
