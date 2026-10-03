# LocalAI ma'lumot tahlilchisi

Excel (`.xlsx`, `.xls`) va JSON fayllarni mahalliy Ollama serveridagi `qwen3.5:9b` yordamida tahlil qiladi. Fayl yuklamasdan ham umumiy chatdan foydalanish mumkin. Excel varag'ini tanlash, jadvalni ko'rish, umumiy statistikani olish va o'zbek tilida savol berish mumkin.

## Ishga tushirish

Ollama ochiq ekanini tekshiring va modelni o'rnating:

```sh
ollama pull qwen3.5:9b
```

Virtual muhitni faollashtirib, paketlarni o'rnating:

```sh
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Ilovani ishga tushiring:

```sh
./start.sh
```

Brauzer manzili: <http://localhost:8501>

Portni almashtirish uchun `PORT=8502 ./start.sh` buyrug'idan foydalaning.

## Boshqa Ollama serveri

Model nomi ataylab `qwen3.5:9b` qilib belgilangan. Ollama boshqa kompyuter yoki serverda ishlasa, ilovani boshlashdan oldin uning API manzilini kiriting:

```sh
export OLLAMA_BASE_URL=http://SERVER_IP:11434
streamlit run app.py --server.maxUploadSize 25
```

Yoki `.env.example` faylidan `.env` nusxa olib, `OLLAMA_BASE_URL` qiymatini o'zgartiring. Uzoq serverda Ollama portini ochiq internetga himoyasiz chiqarmang; VPN yoki TLS/authentication bilan himoyalangan tarmoqdan foydalaning.

## Kuchli serverga joylash

Serverda Python, Ollama va `qwen3.5:9b` tayyor bo'lgach, shu loyihani o'rnating va Streamlit'ni reverse proxy ortida loopback manzilida ishga tushiring:

```sh
OLLAMA_BASE_URL=http://127.0.0.1:11434 .venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.maxUploadSize 25
```

Foydalanuvchilar uchun HTTPS va login qo'yilgan reverse proxy orqali kirish bering. Streamlit portini yoki Ollama portini himoyasiz ochiq internetga chiqarmang. Agar ilova va Ollama alohida serverlarda bo'lsa, `OLLAMA_BASE_URL`ni Ollama joylashgan serverning himoyalangan ichki manziliga sozlang.

## Cheklovlar

- Yuklash limiti 25 MB.
- Jadval ko'rinishida dastlabki 1,000 qator ko'rsatiladi.
- Model kontekstiga raqamli ustunlarning butun fayl statistikasi hamda dastlabki 200 qator (24,000 belgigacha) yuboriladi. Katta fayllarda ko'rinmagan alohida qatorlar bo'yicha javob to'liq bo'lmasligi mumkin.
- Tez javob uchun Qwen'ning ichki thinking rejimi o'chirilgan va kontekst 16K token bilan cheklangan.
- Fayl tarkibi Ollama serveriga yuboriladi. Mahalliy sozlamada bu shu kompyuterning o'zida qoladi.