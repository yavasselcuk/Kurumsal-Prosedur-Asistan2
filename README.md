# 🤖 Kurumsal Prosedür Asistanı (KPA)

AI destekli doküman soru-cevap sistemi. Word dokümanlarınızı yükleyin, yapay zeka ile prosedürler hakkında anında cevaplar alın.

## ✨ Özellikler

- 📄 **Word Doküman İşleme**: .docx formatında dokümanları okuma ve işleme
- 🤖 **AI Soru-Cevap**: Google Gemini 2.0 Flash ile halüsinasyon önlemeli cevaplar
- 🔍 **Akıllı Arama**: RAG sistemi ile anlamsal doküman arama
- 💬 **Chat Sistemi**: Session tabanlı konuşma takibi
- 📱 **Responsive Tasarım**: Mobil ve tablet uyumlu modern arayüz
- 🇹🇷 **Türkçe Destek**: Tam Türkçe arayüz ve optimizeli AI promptları

## 🛠️ Teknoloji Yığını

- **Frontend**: React 18 + Tailwind CSS
- **Backend**: FastAPI (Python 3.11+)  
- **Veritabanı**: MongoDB
- **AI/LLM**: Google Gemini 2.0 Flash
- **Vector Search**: FAISS + SentenceTransformer
- **Document Processing**: python-docx

## 🚀 Hızlı Başlangıç

### Gereksinimler

- Python 3.11+
- Node.js 18+
- MongoDB 6.0+
- Google Gemini API Key

### Kurulum

1. **Projeyi İndirin**
```bash
git clone <repo-url>
cd kurumsal-prosedur-asistani
```

2. **Backend Kurulumu**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
```

3. **Environment Variables**
```bash
# backend/.env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="kpa_database"
GEMINI_API_KEY="your-gemini-api-key"
```

4. **Frontend Kurulumu**
```bash
cd ../frontend
yarn install
```

5. **Servisleri Başlatın**
```bash
# Backend (terminal 1):
cd backend
source venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Frontend (terminal 2):
cd frontend
yarn start
```

## 📖 Kullanım

1. **Doküman Yükleme**: Doküman Yönetimi sekmesinden .docx dosyalarınızı yükleyin
2. **Soru Sorma**: Soru-Cevap sekmesinden prosedürler hakkında soru sorun
3. **AI Cevapları**: Gemini sadece yüklediğiniz dokümanlardan cevap verecek

## 📁 Proje Yapısı

```
kpa-project/
├── backend/                # FastAPI backend
│   ├── server.py          # Ana uygulama
│   ├── requirements.txt   # Python bağımlılıkları
│   └── .env              # Environment variables
├── frontend/              # React frontend
│   ├── src/
│   │   ├── App.js        # Ana bileşen
│   │   ├── App.css       # Stil dosyası
│   │   └── index.js      # Giriş noktası
│   ├── package.json      # Node.js bağımlılıkları
│   └── .env             # Frontend environment
├── KURULUM_DOKUMANTASYONU.md  # Hosting kurulum rehberi
└── README.md             # Bu dosya
```

## 🏗️ Mimari

```
[React Frontend] ←→ [FastAPI Backend] ←→ [MongoDB]
                           ↓
                    [Google Gemini AI]
                           ↓
                  [FAISS Vector Search]
                           ↓
                  [SentenceTransformer]
```

## 🔧 API Endpoints

- `GET /api/` - Ana endpoint
- `GET /api/status` - Sistem durumu
- `POST /api/upload-document` - Doküman yükleme
- `POST /api/ask-question` - Soru sorma
- `GET /api/documents` - Doküman listesi
- `GET /api/chat-history/{session_id}` - Chat geçmişi
- `DELETE /api/documents/{document_id}` - Doküman silme

## 🧪 Test

```bash
# Backend testleri:
python backend_test.py

# Frontend testleri (geliştirme ortamında):
cd frontend
yarn test
```

## 📦 Production Deployment

Detaylı kurulum talimatları için `KURULUM_DOKUMANTASYONU.md` dosyasına bakın.

### Docker ile Hızlı Kurulum

```bash
# Docker Compose ile:
docker-compose up -d
```

### Manuel Kurulum

1. Nginx reverse proxy yapılandırması
2. SSL sertifikası (Let's Encrypt)
3. PM2 ile process management
4. MongoDB güvenlik ayarları
5. Log management ve monitoring

## 🔒 Güvenlik

- API anahtarları environment variables'da saklanır
- MongoDB authentication aktif
- CORS politikaları yapılandırılmış
- Input validation ve sanitization
- Rate limiting (production için)

## 📊 Performans

- Async FastAPI endpoints
- MongoDB connection pooling
- FAISS optimizeli vektör arama
- React lazy loading
- Nginx static file caching

## 🐛 Sorun Giderme

### Yaygın Sorunlar

1. **Backend başlamıyor**: Python versiyonu ve bağımlılık kontrolü
2. **MongoDB bağlantı hatası**: Servis durumu ve URL kontrolü
3. **AI model yüklenmiyor**: İnternet bağlantısı ve disk alanı kontrolü
4. **Frontend build hatası**: Node.js versiyon ve memory kontrolü

### Debug Modu

```bash
# Backend debug:
export DEBUG=True
uvicorn server:app --reload --log-level debug

# Frontend debug:
yarn start
```

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Commit yapın (`git commit -am 'Yeni özellik eklendi'`)
4. Push yapın (`git push origin feature/yeni-ozellik`)
5. Pull Request oluşturun

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakın.

## 📞 İletişim ve Destek

- **Dokümantasyon**: `KURULUM_DOKUMANTASYONU.md`
- **Issues**: GitHub Issues sekmesi
- **Wiki**: Proje wiki sayfası

## 🗂️ Sürüm Geçmişi

### v1.0.0 (Mevcut)
- ✅ Word doküman işleme
- ✅ Google Gemini entegrasyonu
- ✅ RAG sistemi
- ✅ Modern React UI
- ✅ Session-based chat
- ✅ Türkçe optimizasyon

### Gelecek Sürümler
- 📄 PDF desteği
- 👤 Kullanıcı yetkilendirme
- 📊 Analytics dashboard
- 🔍 Gelişmiş arama filtreleri
- 🌍 Çoklu dil desteği

---

**Kurumsal Prosedür Asistanı (KPA)** - AI ile prosedür yönetimini kolaylaştırın! 🚀