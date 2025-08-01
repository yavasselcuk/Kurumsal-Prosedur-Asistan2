# 🚀 KPA - Ubuntu 24.04 LTS Hızlı Kurulum Rehberi

## 📦 Ubuntu 24.04 LTS Sunucuda Kurulum

### ⚡ Tek Komutla Otomatik Kurulum

```bash
# Proje dosyalarını indirin ve çıkarın
wget [ZIP_DOWNLOAD_URL] -O kpa-project.zip
unzip kpa-project.zip
cd kpa-project

# Otomatik kurulum script'ini çalıştırın
chmod +x ubuntu24-install.sh
sudo ./ubuntu24-install.sh
```

### 🎯 Manuel Kurulum (Adım Adım)

#### 1. Sistem Hazırlığı (Ubuntu 24.04 LTS)
```bash
# Sistem güncellemesi
sudo apt update && sudo apt upgrade -y

# Gerekli paketleri kurun
sudo apt install -y curl wget git vim htop build-essential

# Python 3.12 (Ubuntu 24.04 varsayılan)
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Node.js 20.x LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# MongoDB 7.0
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
   sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu noble/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update && sudo apt install -y mongodb-org

# Nginx
sudo apt install -y nginx

# PM2 (Process Manager)
sudo npm install -g pm2 yarn
```

#### 2. Servisleri Başlatın
```bash
# MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod

# Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

#### 3. Proje Kurulumu
```bash
# Proje dizini
sudo mkdir -p /opt/kpa
sudo chown $USER:$USER /opt/kpa
cd /opt/kpa

# Dosyaları çıkarın
unzip ~/kpa-project.zip
mv kpa-project/* .

# Environment variables
cp .env.example .env
nano .env  # Gemini API anahtarınızı ekleyin
```

#### 4. Backend Kurulumu
```bash
cd /opt/kpa/backend

# Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
```

#### 5. Frontend Build
```bash
cd /opt/kpa/frontend

# Dependencies ve build
yarn install
yarn build

# Build çıktısını kontrol edin
ls -la build/
```

#### 6. Production Deployment
```bash
# PM2 ile backend başlatın
cd /opt/kpa/backend
pm2 start ecosystem.config.js
pm2 save
pm2 startup

# Nginx konfigürasyonu
sudo cp /opt/kpa/nginx.conf /etc/nginx/sites-available/kpa
sudo ln -s /etc/nginx/sites-available/kpa /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

### 🐳 Docker ile Hızlı Kurulum (Ubuntu 24.04)

```bash
# Docker kurulumu
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# KPA deployment
cd /opt/kpa
chmod +x deploy.sh
./deploy.sh deploy
```

### 🔑 Gerekli API Anahtarı

Google Gemini API anahtarı gereklidir:
1. https://makersuite.google.com/app/apikey adresine gidin
2. API anahtarınızı oluşturun
3. `.env` dosyasında `GEMINI_API_KEY` değerini güncelleyin

### ✅ Kurulum Doğrulama

```bash
# Servisleri kontrol edin
sudo systemctl status mongod nginx
pm2 status

# Portları kontrol edin
sudo netstat -tlnp | grep -E ':27017|:8001|:80|:443'

# API testleri
curl http://localhost:8001/api/status
curl http://localhost/health

# Web arayüzünü test edin
curl -I http://localhost/
```

### 🌍 Domain ve SSL Kurulumu

```bash
# Domain'inizi DNS'de sunucunuza yönlendirin
# A record: yourdomain.com -> SERVER_IP

# Let's Encrypt SSL
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com

# SSL yenileme testi
sudo certbot renew --dry-run
```

### 📊 Monitoring ve Bakım

```bash
# Health check script
sudo nano /opt/kpa/scripts/health-check.sh
sudo chmod +x /opt/kpa/scripts/health-check.sh

# Crontab ile otomatik health check
crontab -e
# Şu satırı ekleyin:
*/15 * * * * /opt/kpa/scripts/health-check.sh

# Log monitoring
tail -f /var/log/kpa/backend.log
pm2 logs kpa-backend
```

### 🆘 Sorun Giderme (Ubuntu 24.04)

```bash
# Sistem kaynaklarını kontrol edin
htop
df -h
free -h

# Servis loglarını kontrol edin
sudo journalctl -u mongod -f
sudo journalctl -u nginx -f
pm2 logs kpa-backend --lines 50

# Port kullanımı
sudo lsof -i :8001
sudo lsof -i :27017

# Nginx test
sudo nginx -t

# MongoDB bağlantı test
mongosh --eval "db.adminCommand('ping')"
```

### 🎯 Performans Optimizasyonu (Ubuntu 24.04)

```bash
# MongoDB performans ayarları
sudo nano /etc/mongod.conf
# cacheSizeGB: 2  # RAM'inizin yarısı

# Nginx worker processes
sudo nano /etc/nginx/nginx.conf
# worker_processes auto;
# worker_connections 1024;

# System limits
sudo nano /etc/security/limits.conf
# kpa soft nofile 65536
# kpa hard nofile 65536

# PM2 cluster mode (CPU core sayınıza göre)
pm2 delete kpa-backend
pm2 start ecosystem.config.js --instances 4
```

## ✨ Özellikler

- 📄 **Word Doküman İşleme**: .docx upload ve parsing
- 🤖 **AI Soru-Cevap**: Google Gemini 2.0 Flash
- 🔍 **Akıllı Arama**: RAG sistemi ile anlamsal arama
- 💬 **Chat Sistemi**: Session tabanlı konuşma
- 📱 **Responsive Tasarım**: Mobil uyumlu arayüz
- 🇹🇷 **Türkçe Destek**: Tam Türkçe optimizasyon

## 📋 Sistem Gereksinimleri (Ubuntu 24.04 LTS)

- **CPU**: 2+ vCPU
- **RAM**: 4GB+ (8GB önerilen)
- **Disk**: 20GB+ SSD
- **Network**: 100 Mbps+
- **OS**: Ubuntu 24.04 LTS

## 🔗 Yararlı Linkler

- **Detaylı Dokümantasyon**: KURULUM_DOKUMANTASYONU.md
- **Google Gemini API**: https://makersuite.google.com/app/apikey
- **Let's Encrypt**: https://letsencrypt.org/
- **PM2 Dokümantasyon**: https://pm2.keymetrics.io/

Bu rehber Ubuntu 24.04 LTS için optimize edilmiştir. Sisteminiz kurulduktan sonra http://localhost veya domain adresiniz üzerinden erişebilirsiniz!