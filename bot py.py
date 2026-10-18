import time
import requests

# ---------------- SOZLAMALAR ----------------
BOT_TOKEN = "8822520706:AAErLqCSmGLyQjsCjHHAVqROePpTIDXtMHw"
CHAT_ID = "8151656291"

USERNAME = "andijon+fergana"
PASSWORD = "1234"

LOGIN_URL = "https://celogistic.uz/auth/login"
ORDERS_URL = "https://celogistic.uz/senior-courier/pending"

BEARER_TOKEN = None
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    ),
    "Accept": "application/json",
}

sent_order_ids = set()


def send_telegram(message):
  """Telegram bot orqali xabar yuborish"""
  telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
  payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
  try:
    requests.post(telegram_url, json=payload)
  except Exception as e:
    print(f"Telegramga yuborishda xatolik: {e}")


def login_to_site():
  """Saytga avtomatik login qilib yangi token olish"""
  global BEARER_TOKEN, HEADERS
  print("🔄 Saytga avtomatik login qilinmoqda...")

  attempts = [
      # 1. Form-data formatida (FastAPI / OAuth2 standarti)
      {"type": "form", "data": {"username": USERNAME, "password": PASSWORD}},
      {"type": "form", "data": {"login": USERNAME, "password": PASSWORD}},
      # 2. JSON formatida
      {"type": "json", "data": {"username": USERNAME, "password": PASSWORD}},
      {"type": "json", "data": {"login": USERNAME, "password": PASSWORD}},
      {"type": "json", "data": {"phone": USERNAME, "password": PASSWORD}},
  ]

  for attempt in attempts:
    try:
      req_headers = HEADERS.copy()
      req_headers.pop("Authorization", None)

      if attempt["type"] == "json":
        req_headers["Content-Type"] = "application/json"
        res = requests.post(
            LOGIN_URL, json=attempt["data"], headers=req_headers, timeout=10
        )
      else:
        req_headers["Content-Type"] = "application/x-www-form-urlencoded"
        res = requests.post(
            LOGIN_URL, data=attempt["data"], headers=req_headers, timeout=10
        )

      if res.status_code == 200:
        data = res.json()
        raw_token = (
            data.get("token")
            or data.get("access_token")
            or data.get("data", {}).get("token")
            or data.get("data", {}).get("access_token")
        )

        if raw_token:
          BEARER_TOKEN = (
              f"Bearer {raw_token}"
              if not str(raw_token).startswith("Bearer ")
              else raw_token
          )
          HEADERS["Authorization"] = BEARER_TOKEN
          print(
              "✅ Muvaffaqiyatli login qilindi! Yangi token avtomatik olindi."
          )
          return True
      else:
        print(
            f"❌ Urinish ({attempt['type']} -"
            f" {list(attempt['data'].keys())[0]}): status {res.status_code} ->"
            f" {res.text}"
        )

    except Exception as e:
      print(f"❌ Login so'rovi xatoligi: {e}")

  print("❌ Avto-login amalga oshmadi.")
  return False


def check_orders():
  """Saytdan shoshilinch zakazlarni tekshirish"""
  global BEARER_TOKEN

  if not BEARER_TOKEN:
    if not login_to_site():
      return

  response = requests.get(ORDERS_URL, headers=HEADERS)

  if response.status_code == 401:
    print("⚠️ Status 401: Token eskirgan. Qayta login qilinmoqda...")
    if login_to_site():
      response = requests.get(ORDERS_URL, headers=HEADERS)
    else:
      return

  if response.status_code == 200:
    data = response.json()
    orders = data.get("items", [])

    for order in orders:
      order_id = order.get("pending_id") or order.get("external_number")

      if order_id and order_id not in sent_order_ids:
        supplier = (
            order.get("supplier_name")
            or order.get("seller_name")
            or "Ko'rsatilmagan"
        )
        customer = order.get("customer_name", "Ko'rsatilmagan")
        phone = order.get("phone", "Ko'rsatilmagan")
        district = order.get("district_name", "Ko'rsatilmagan")
        amount = order.get("total_amount", 0)

        products_list = []
        for prod in order.get("items", []):
          p_name = prod.get("product_name", "")
          p_qty = prod.get("quantity", 1)
          if p_name:
            products_list.append(f"{p_name} x{p_qty}")

        goods_str = (
            ", ".join(products_list) if products_list else "Ko'rsatilmagan"
        )
        formatted_price = (
            f"{int(amount):,}".replace(",", " ") if amount else "0"
        )

        text = (
            f"🚨 <b>SHOSHILINCH ZAKAZ #{order_id}</b>\n\n"
            f"🏢 <b>Yetkazib beruvchi:</b> {supplier}\n"
            f"👤 <b>Mijoz:</b> {customer}\n"
            f"📞 <b>Tel:</b> {phone}\n"
            f"📍 <b>Tuman/Shahar:</b> {district}\n"
            f"📦 <b>Mahsulot:</b> {goods_str}\n"
            f"💰 <b>Summa:</b> {formatted_price} so'm"
        )

        send_telegram(text)
        sent_order_ids.add(order_id)
        print(f" Yuborildi: #{order_id}")

  else:
    print(f"Saytga ulanishda xatolik statusi: {response.status_code}")


if __name__ == "__main__":
  print("Bot ishga tushdi va avto-login bilan 24/7 kuzatmoqda...")
  while True:
    try:
      check_orders()
    except Exception as err:
      print(f"Xatolik yuz berdi: {err}")
    time.sleep(20)
