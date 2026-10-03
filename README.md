# LocalAI

Shaxsiy AI yordamchi va agent. To'liq sizning kompyuteringizda, [Ollama](https://ollama.com) va ochiq kodli `qwen3.5:9b` modeli ustida ishlaydi. Internet kerak emas, suhbat va fayllar kompyuterdan chiqmaydi.

LocalAI ikki shaklda ishlaydi:

- **Model.** `localai` nomli Ollama modeli avtomatik yaratiladi. U LocalAI xarakteri, uslubi va imlo xatolariga chidamliligini o'zida saqlaydi. Terminalda `ollama run localai` bilan yoki Ollama API'ni ishlatadigan istalgan dasturda ishlatish mumkin.
- **Chat va agent.** Zamonaviy, minimal veb interfeys. LocalAI kompyuterdagi papka va fayllarni **faqat sizning ruxsatingiz bilan** ko'rib, o'qib, tahlil qiladi.

## Imkoniyatlar

| | |
|---|---|
| 💬 Chat | Oqimli javoblar, Markdown, rangli kod bloklari, suhbatlar tarixi, qayta javob olish, to'xtatish |
| 📁 Fayllar | Papkani ko'rish, fayl o'qish (kod, matn, PDF, DOCX, Jupyter), fayllar ichida qidirish |
| 🔐 Ruxsatlar | Har bir murojaat uchun so'rov: **Ruxsat berish**, **Papkaga doimiy** (shu suhbat davomida) yoki **Rad etish**. Faylga yozishdan oldin mazmuni ko'rsatiladi |
| 📊 Jadvallar | Excel, CSV, JSON: statistika, filtrlar, guruhlash, yig'indi/o'rtacha/soni. Hisob-kitob butun fayl bo'yicha aniq bajariladi |
| 🧮 Hisob | Xavfsiz kalkulyator: foizlar, formulalar, katta sonlar |
| ✍️ Imlo | Shoshib yozilgan, xato, apostrofsiz (`boladi`, `togri`) yoki lotin/kirill aralash xabarlarni tushunadi. Papka va ustun nomidagi kichik xatolarni ham o'zi tuzatadi |
| 🧠 Chuqur o'ylash | Murakkab savollar uchun model avval o'ylab, keyin javob beradi |
| 📎 Biriktirish | Faylni tortib tashlang, nusxalab qo'ying yoki 📎 tugmasini bosing |

### Ko'nikmalar (skills)

Ko'nikmalar xabar mazmuniga qarab o'zi yoqiladi. Xabar boshida `/` yozib, qo'lda ham tanlash mumkin:

| Buyruq | Vazifasi |
|---|---|
| `/kod` | Kod yozish, xato topish, tushuntirish, refaktoring |
| `/tahlil` | Excel, CSV va JSON ma'lumotlarini tahlil qilish |
| `/papka` | Kompyuterdagi papka va loyihalarni o'rganish |
| `/imlo` | Imlo, grammatika va punktuatsiyani tuzatish |
| `/tarjima` | O'zbek, rus, ingliz va boshqa tillar o'rtasida tarjima |
| `/xulosa` | Matn yoki hujjatning qisqa mazmuni |
| `/hisob` | Aniq hisob-kitob va masalalar |
| `/tushuntir` | Murakkab mavzuni oddiy tilda tushuntirish |

## O'rnatish

1. [Ollama](https://ollama.com/download)'ni o'rnating va oching.
2. Modelni yuklab oling (bir marta, taxminan 6 GB):

   ```sh
   ollama pull qwen3.5:9b
   ```

3. LocalAI'ni ishga tushiring:

   ```sh
   ./start.sh          # macOS / Linux
   start.bat           # Windows
   ```

Skript virtual muhit yaratadi, paketlarni o'rnatadi, model yo'q bo'lsa yuklab oladi va brauzerda <http://127.0.0.1:8501> manzilini ochadi. Birinchi ishga tushishda `localai` modeli avtomatik yaratiladi.

Qo'lda ishga tushirish:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m localai --open
```

Python 3.10 yoki undan yangisi kerak.

## LocalAI modeli

```sh
ollama run localai                                     # terminalda suhbat
.venv/bin/python -m localai create-model               # modelni yaratish yoki yangilash
.venv/bin/python -m localai doctor                     # Ollama, model va imkoniyatlarni tekshirish
```

Modelni Ollama CLI bilan qo'lda yaratsangiz ham bo'ladi: `ollama create localai -f Modelfile`. Boshqa dasturlar uchun Ollama API: `http://localhost:11434`, model nomi `localai`. OpenAI bilan mos API manzili: `http://localhost:11434/v1`.

## Sozlamalar

`.env.example` faylidan `.env` nusxa oling va kerakli qiymatni o'zgartiring:

| O'zgaruvchi | Standart | Izoh |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama manzili |
| `LOCALAI_BASE_MODEL` | `qwen3.5:9b` | Asosiy model |
| `LOCALAI_MODEL` | `localai` | Yaratiladigan model nomi |
| `LOCALAI_NUM_CTX` | `16384` | Kontekst hajmi (token). Xotira kam bo'lsa `8192` |
| `LOCALAI_WORKSPACE` | uy papkasi | Nisbiy yo'llar shu papkadan boshlanadi |
| `PORT` | `8501` | Veb interfeys porti |
| `LOCALAI_MAX_UPLOAD_MB` | `25` | Biriktiriladigan fayl limiti |

## Xavfsizlik

- Server faqat `127.0.0.1` manzilida tinglaydi. Boshqa saytlardan va begona host nomlaridan kelgan so'rovlar rad etiladi.
- Har bir fayl yoki papkaga murojaat ruxsat so'raydi. "Papkaga doimiy" ruxsati faqat shu suhbat uchun amal qiladi va server qayta ishga tushganda bekor bo'ladi.
- Faylga yozish har safar alohida tasdiqlanadi.
- Maxfiy fayllar (`.env`, `.ssh`, kalitlar, parollar bazasi) doimiy ruxsatga kirmaydi. Ular uchun har safar ogohlantirish bilan alohida so'raladi.
- Fayl ichidagi matnlar model uchun buyruq emas, faqat ma'lumot hisoblanadi.
- Ollama boshqa serverda bo'lsa, fayl mazmuni o'sha serverga yuboriladi. Uni ochiq internetga himoyasiz chiqarmang (VPN yoki TLS ishlating).

## Cheklovlar

- Model bilimi o'qitilgan sanagacha. Internetga kirmaydi.
- 9B model kuchli, lekin mukammal emas. Muhim raqam va xulosalarni tekshirib ko'ring.
- Skanerlangan PDF (rasm) matnini o'qiy olmaydi. `.doc`, `.pptx` formatlarini PDF yoki DOCX'ga o'tkazing.
- Suhbatlar tarixi brauzerning `localStorage` xotirasida saqlanadi.

## Ishlab chiquvchilar uchun

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

Ollama'siz interfeysni sinash uchun soxta server:

```sh
.venv/bin/python tests/fake_ollama.py --port 11500 &
OLLAMA_BASE_URL=http://127.0.0.1:11500 .venv/bin/python -m localai --open
```

Tuzilma:

```
localai/
  server.py       HTTP API, oqimli chat, ruxsatlar, fayl yuklash
  agent.py        agent sikli: model, vositalar, ruxsat kutish, kontekst boshqaruvi
  tools.py        vositalar: list_directory, read_file, search_files, analyze_table, write_file, calculate
  files.py        PDF, DOCX, Excel, CSV va matn o'qish, jadval so'rovlari
  permissions.py  yo'llarni aniqlash (xatolarga chidamli), maxfiy fayllar, ruxsatlar
  skills.py       ko'nikmalar va slash-buyruqlar
  prompts.py      LocalAI xarakteri va tizim ko'rsatmalari, Modelfile
  models.py       Ollama holati va `localai` modelini yaratish
static/           veb interfeys (tashqi kutubxonalarsiz, oflayn ishlaydi)
```
