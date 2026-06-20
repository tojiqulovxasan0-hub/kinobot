# 🎬 Kino Bot

Telegram kino boti — kinolarni kod orqali ulashish, majburiy obuna tekshiruvi, admin panel va statistika.

## 📋 Xususiyatlar

- ✅ Kino qo'shish / o'chirish (video, hujjat, audio, rasm)
- ✅ Kinolar Telegram serverida saqlanadi (file_id orqali)
- ✅ Majburiy kanallar qo'shish / o'chirish
- ✅ Obuna tekshiruvi (bot kanalda admin bo'lishi shart)
- ✅ Kod orqali kino olish (`1`, `42`, `action1` kabi)
- ✅ Hammaga xabar yuborish (matn, rasm, video, ovoz, audio, hujjat)
- ✅ Statistika (bugungi foydalanuvchilar, ko'rishlar, mashhur kinolar)
- ✅ Foydalanuvchilar ro'yxati

## 🚀 O'rnatish

### 1. Talablar

- Python 3.10+
- pip

### 2. Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

### 3. .env faylini sozlash

`.env` faylida quyidagilar bor:

```
BOT_TOKEN=your_bot_token
ADMIN_ID=your_telegram_id
```

### 4. Botni ishga tushirish

```bash
python main.py
```

## 👑 Admin buyruqlari

| Tugma | Vazifasi |
|-------|---------|
| 🎬 Kino qo'shish | Yangi kino qo'shish |
| 🗑 Kino o'chirish | Kino kodini kiritib o'chirish |
| 📋 Kinolar ro'yxati | Barcha kinolar |
| 📢 Kanal qo'shish | Majburiy kanal qo'shish |
| ❌ Kanal o'chirish | Kanal o'chirish |
| 📡 Kanallar ro'yxati | Barcha kanallar |
| 📊 Statistika | Bot statistikasi |
| 👥 Foydalanuvchilar | Foydalanuvchilar ro'yxati |
| 📨 Hammaga xabar | Ommaviy xabar yuborish |

## 📢 Kanal qo'shish formati

```
kanal_id | Kanal nomi | https://t.me/kanal
```

Misol:
```
-1001234567890 | Mening Kanalim | https://t.me/mening_kanalim
```

⚠️ **Bot kanalda admin bo'lishi shart!**

## 📁 Fayl tuzilmasi

```
kinobot/
├── main.py           # Asosiy fayl
├── database.py       # SQLite ma'lumotlar bazasi
├── keyboards.py      # Klaviaturalar
├── middlewares.py    # Foydalanuvchi ro'yxatga olish
├── handlers/
│   ├── __init__.py
│   ├── admin.py      # Admin handler'lari
│   └── user.py       # Foydalanuvchi handler'lari
├── .env              # Token va ID (yashirin)
├── requirements.txt  # Kutubxonalar
└── kinobot.db        # Ma'lumotlar bazasi (avtomatik yaratiladi)
```
