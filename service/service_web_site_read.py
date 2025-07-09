import requests
from requests.auth import HTTPBasicAuth
import base64

class WordPressReader:
    def __init__(self, base_url, consumer_key=None, consumer_secret=None):
        self.base_url = base_url.rstrip("/")
        self.wp_api_url = self.base_url + "/wp-json/wp/v2"
        self.wc_api_url = self.base_url + "/wp-json/wc/v3"
        self.headers = {}

        if consumer_key and consumer_secret:
            token = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode()).decode()
            self.headers = {"Authorization": f"Basic {token}"}
            print("✅ Auth ayarlandı")
        else:
            print("❌ Auth ayarlanmadı")

    def get_pages(self):
        response = requests.get(f"{self.wp_api_url}/pages")
        if response.status_code == 200:
            return response.json()
        else:
            print("Sayfalar alınamadı:", response.status_code)
            return []

    def get_posts(self):
        response = requests.get(f"{self.wp_api_url}/posts")
        if response.status_code == 200:
            return response.json()
        else:
            print("Yazılar alınamadı:", response.status_code)
            return []

    def get_categories(self):
        response = requests.get(f"{self.wp_api_url}/categories")
        if response.status_code == 200:
            return response.json()
        else:
            print("Kategoriler alınamadı:", response.status_code)
            return []

    def get_products(self):
        response = requests.get(f"{self.wc_api_url}/products?per_page=50", headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            print("Ürünler alınamadı:", response.status_code, response.text)
            return []

    def print_titles(self, items):
        for item in items:
            print("🔹", item.get("title", {}).get("rendered", "Başlıksız"))