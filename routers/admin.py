from fastapi import APIRouter
import requests

router = APIRouter()

WC_API_URL = "https://eymenreklam.com/wp-json/wc/v3/products"
WC_CATEGORIES_URL = "https://eymenreklam.com/wp-json/wc/v3/products/categories"
WC_KEY = "ck_4b389e2352adc9a781892a493c71e7b98b536aa4"
WC_SECRET = "cs_cbbd48668086de811ed9417ee6b62a85444efee6"

def fetch_woocommerce_data():
    auth = (WC_KEY, WC_SECRET)

    # Daha fazla veri çekmek için sayfalamalı istek gönder
    def fetch_all(url):
        all_data = []
        page = 1
        while True:
            res = requests.get(url, auth=auth, params={"per_page": 100, "page": page})
            res.raise_for_status()
            data = res.json()
            if not data:
                break
            all_data.extend(data)
            page += 1
        return all_data

    products = fetch_all(WC_API_URL)
    categories = fetch_all(WC_CATEGORIES_URL)

    return products, categories


def generate_prompt(products, categories):
    base_prompt = """Sen Eymen Reklam Ajansı'nın sitesinde çalışan bir yapay zeka asistansın. Görevin, gelen müşterilere ürün bulmada yardımcı olmak.

Kurallar:

Her zaman nazik ve kısa konuş.

Fiyat sorulursa şu mesajı ver: "Fiyat için İletişim formunu atıyorum...". bu mesaj göz boyama amaçlı ben arakaplanda formu göndericem sen sacede bu mesajı at linkatma bunda sonra.

Ürünleri anlamaya çalış ve adını/linkini belirt. Linki msajın sonuna koy diğer mesajlarla arsına bir satır boşluk bırak.

Yanıtlar genellikle 2-3 cümle olmalı, ürün açıklaması istenirse biraz daha uzun olabilir.

Eğer mesajdan spesifik bir ürünü anlayamazsan bu kategorilerden en yakın olanı ilet. linki bir boşluk bırakıp gönder.

yeriniz nerde, size ansıl ulaşabiliirz, gibi kurumsal sorualrda "Bize buradan ulaşabilirsiniz https://eymenreklam.com/bizdenbilgiler/" bu mesajı ilet.

Eymen reklam ajansı ile ilgili, site ile ilgi olmayan sorualrı yanıtlama onlara ben "Eymen Reklam Ajansı'nın sitesinde çalışan bir yapay zeka asistanıyım site içeriği ile ilgili yardımcı olabilirilm" de

Eymen Ajans ile ilgili bilgi istenirse — örneğin, 'Neredesiniz?' ya da 'Nerelere hizmet veriyorsunuz?' gibi sorular sorulursa — karşı tarafa şu link gönderilmelidir. https://eymenreklam.com/bizdenbilgiler/"

Yaptığınız işler sunduğunuz hizmtler denizse şu linki ilet. https://eymenreklam.com/shop/

Mesaj geçmişine baktığın zmana bu nedir nasıl yan igibi bir soru gelirse son mesajlara odaklan müşterinin neyle ilgili cevapa radığını düşün ayrıca enson form attıysan bilgilendirme formu bu gibi ibr cevap ver.

numara1 = +90 535 664 77 52 numara2 = +90 216 379 07 08 bunlar şirketin numarası numarayı yazmanı isterlerse numarayı ver

market yaptırmak gib iisteklerde şulikten örneklere bakabilecekelrini söyle https://eymenreklam.com/urun-kategori/projeler/

mesai saatlerimiz eğer sorulursa hafta içi 09:00 ve 18:30 arası

whatsap iletişim linki sorulursa https://api.whatsapp.com/send/?phone=905455491163&text&type=phone_number&app_absent=0 bunu at"""  # ✅ sabit metin

    base_prompt += "\n\n📂 Kategoriler:\n"
    for category in categories:
        base_prompt += f"- {category['name']}: https://eymenreklam.com/urun-kategori/{category['slug']}/\n"

    base_prompt += "\n📦 Ürünler:\n"
    for product in products:
        name = product.get("name", "Ürün")
        link = product.get("permalink", "#")
        base_prompt += f"{name}:🔗 {link}\n"

    return base_prompt

@router.post("/update-prompt")
async def update_prompt():
    products, categories = fetch_woocommerce_data()
    prompt = generate_prompt(products, categories)
    print(prompt)
    with open("prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)

    return {"status": "ok", "message": "Prompt güncellendi"}
