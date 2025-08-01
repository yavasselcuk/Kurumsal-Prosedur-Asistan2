# 🚀 KPA - Hızlı Kurulum Rehberi

## 📦 Zip Dosyasından Kurulum

### 1. Dosyaları Çıkarın
```bash
unzip kpa-project-final.zip
cd kpa-project
```

### 2. Environment Variables Ayarlayın
```bash
cp .env.example .env
nano .env  # Gemini API anahtarınızı ekleyin
```

### 3. Docker ile Hızlı Başlangıç
```bash
chmod +x deploy.sh
./deploy.sh deploy
```

### 4. Manuel Kurulum (Docker olmadan)

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
uvicorn server:app --host 0.0.0.0 --port 8001
```

**Frontend:**
```bash
cd frontend
yarn install
yarn start
```

### 5. Test Edin
- Frontend: http://localhost (Docker) veya http://localhost:3000 (Manuel)
- Backend API: http://localhost:8001/api/status

## 🔑 Gerekli API Anahtarı

Google Gemini API anahtarı gereklidir:
1. https://makersuite.google.com/app/apikey adresine gidin
2. API anahtarınızı oluşturun
3. `.env` dosyasında `GEMINI_API_KEY` değerini güncelleyin

## 📋 Sistem Gereksinimleri

- **Docker Kurulumu**: Docker + Docker Compose
- **Manuel Kurulum**: Python 3.11+, Node.js 18+, MongoDB 6.0+

## 🆘 Yardım

Detaylı kurulum için `KURULUM_DOKUMANTASYONU.md` dosyasını okuyun.