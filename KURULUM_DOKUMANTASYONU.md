# Kurumsal Prosedür Asistanı (KPA) - Hosting Kurulum Rehberi

## 📋 Proje Özeti

**Kurumsal Prosedür Asistanı (KPA)**, Word dokümanlarından AI destekli soru-cevap sistemi sunan hibrit web uygulamasıdır.

### Teknoloji Yığını
- **Frontend**: React 18 + Tailwind CSS
- **Backend**: FastAPI (Python 3.11+)
- **Veritabanı**: MongoDB
- **AI/LLM**: Google Gemini 2.0 Flash
- **Vector Search**: FAISS + SentenceTransformer
- **Document Processing**: python-docx

---

## 🚀 Hızlı Kurulum (Üretim)

### 1. Sistem Gereksinimleri

```bash
# Minimum Sistem Gereksinimleri:
- CPU: 2 vCPU
- RAM: 4GB (önerilen: 8GB)
- Disk: 20GB SSD
- OS: Ubuntu 20.04+ / CentOS 8+ / Docker destekli sistem
```

### 2. Gerekli Yazılımlar

#### Ubuntu 24.04 LTS için Özel Kurulum

```bash
# Sistem güncellemesi
sudo apt update && sudo apt upgrade -y

# Temel geliştirme araçları
sudo apt install -y build-essential curl wget git vim nano htop

# Python 3.11+ (Ubuntu 24.04'te varsayılan Python 3.12)
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Python versiyonunu kontrol edin
python3 --version  # Python 3.12.x çıktısı beklenir

# Node.js 20.x LTS kurulumu (Ubuntu 24.04 için önerilen)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Node.js versiyonunu kontrol edin
node --version    # v20.x.x
npm --version     # 10.x.x

# Yarn package manager
npm install -g yarn

# PM2 process manager (production için)
npm install -g pm2

# Git konfigürasyonu (opsiyonel)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

#### Diğer Dağıtımlar için

```bash
# Ubuntu/Debian (Eski sürümler) için:
sudo apt update
sudo apt install -y python3.11 python3.11-pip nodejs npm mongodb git

# CentOS/RHEL için:
sudo yum install -y python3.11 python3.11-pip nodejs npm mongodb-org git

# Arch Linux için:
sudo pacman -S python python-pip nodejs npm mongodb git

# macOS için (Homebrew):
brew install python@3.11 node mongodb/brew/mongodb-community git
```

### 3. MongoDB Kurulumu

#### Ubuntu 24.04 LTS için MongoDB 7.0 Kurulumu

```bash
# MongoDB GPG anahtarını import edin
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
   sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg \
   --dearmor

# MongoDB repository ekleyin (Ubuntu 24.04 "noble" için)
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu noble/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# Paket listesini güncelleyin
sudo apt update

# MongoDB Community Edition'ı kurun
sudo apt install -y mongodb-org

# MongoDB servisini başlatın ve enable edin
sudo systemctl start mongod
sudo systemctl enable mongod

# MongoDB servis durumunu kontrol edin
sudo systemctl status mongod

# MongoDB bağlantısını test edin
mongosh --eval "db.adminCommand('ismaster')"

# MongoDB versiyonunu kontrol edin
mongosh --eval "db.version()"  # 7.0.x çıktısı beklenir
```

#### Firewall Yapılandırması (Ubuntu 24.04)

```bash
# UFW firewall'ı aktifleştirin
sudo ufw enable

# SSH, HTTP, HTTPS portlarını açın
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# MongoDB ve backend portlarını yerel ağla sınırlayın (güvenlik için)
sudo ufw allow from 127.0.0.1 to any port 27017
sudo ufw allow from 127.0.0.1 to any port 8001

# UFW durumunu kontrol edin
sudo ufw status verbose
```

#### MongoDB Yapılandırma Dosyası (Ubuntu 24.04)

```bash
# MongoDB konfigürasyon dosyasını düzenleyin
sudo nano /etc/mongod.conf
```

```yaml
# /etc/mongod.conf - Ubuntu 24.04 için optimize edilmiş
storage:
  dbPath: /var/lib/mongodb
  journal:
    enabled: true

systemLog:
  destination: file
  logAppend: true
  path: /var/log/mongodb/mongod.log
  logRotate: reopen

net:
  port: 27017
  bindIp: 127.0.0.1

processManagement:
  timeZoneInfo: /usr/share/zoneinfo

# Güvenlik ayarları (production için)
security:
  authorization: enabled

# Memory ve performans ayarları
storage:
  wiredTiger:
    engineConfig:
      cacheSizeGB: 2  # RAM'inizin yarısı kadar
    collectionConfig:
      blockCompressor: snappy
    indexConfig:
      prefixCompression: true
```

#### Diğer Dağıtımlar için MongoDB

```bash
# Ubuntu 22.04 LTS için:
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org

# CentOS 9 / RHEL 9 için:
sudo tee /etc/yum.repos.d/mongodb-org-7.0.repo << 'EOF'
[mongodb-org-7.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/$releasever/mongodb-org/7.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-7.0.asc
EOF

sudo yum install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod

# Docker ile MongoDB (platform bağımsız):
docker run -d --name mongodb \
  -p 27017:27017 \
  -v mongodb_data:/data/db \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=password123 \
  mongo:7.0
```

---

## 📦 Proje Kurulumu

### 1. Projeyi İndirin

#### Ubuntu 24.04 LTS için

```bash
# Proje dizini oluşturun
sudo mkdir -p /opt/kpa
sudo chown $USER:$USER /opt/kpa
cd /opt/kpa

# GitHub'dan clone edin (eğer reponuz varsa):
git clone https://github.com/[kullanici-adi]/kurumsal-prosedur-asistani.git .

# Veya zip dosyasını indirin ve çıkarın:
wget https://github.com/[kullanici-adi]/kurumsal-prosedur-asistani/archive/main.zip
unzip main.zip
mv kurumsal-prosedur-asistani-main/* .
rm -rf kurumsal-prosedur-asistani-main main.zip

# Veya yerel zip dosyasını çıkarın:
unzip kpa-project-final.zip
mv kpa-project/* .
rm -rf kpa-project

# Dizin izinlerini ayarlayın
sudo chown -R $USER:$USER /opt/kpa
chmod +x deploy.sh
```

#### Dosya Yapısını Kontrol Edin

```bash
# Proje yapısını görüntüleyin
tree /opt/kpa || ls -la /opt/kpa

# Beklenen yapı:
# /opt/kpa/
# ├── backend/
# ├── frontend/
# ├── docker-compose.yml
# ├── deploy.sh
# └── README.md
```

### 2. Backend Kurulumu (Ubuntu 24.04 LTS)

```bash
cd /opt/kpa/backend

# Python sanal ortam oluşturun (Ubuntu 24.04'te Python 3.12)
python3 -m venv venv

# Sanal ortamı aktifleştirin
source venv/bin/activate

# Python ve pip versiyonlarını kontrol edin
python --version  # Python 3.12.x
pip --version     # pip 24.x

# Pip'i güncelleyin
pip install --upgrade pip

# Sistem bağımlılıklarını kurun (gerekli C kütüphaneleri)
sudo apt install -y python3-dev python3-setuptools python3-wheel
sudo apt install -y build-essential libssl-dev libffi-dev libblas3 liblapack3
sudo apt install -y libatlas-base-dev gfortran  # NumPy/SciPy için

# Python bağımlılıklarını yükleyin
pip install -r requirements.txt

# Özel kütüphane kurulumu
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

# Kurulumu doğrulayın
python -c "import fastapi; print('FastAPI:', fastapi.__version__)"
python -c "import sentence_transformers; print('SentenceTransformers: OK')"
python -c "import faiss; print('FAISS: OK')"
python -c "from emergentintegrations.llm.chat import LlmChat; print('EmergentIntegrations: OK')"

# Environment variables ayarlayın
cp .env.example .env 2>/dev/null || true
nano .env
```

#### Backend Test ve Geliştirme

```bash
# Backend'i development modunda çalıştırın
cd /opt/kpa/backend
source venv/bin/activate

# Development server başlatın
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Başka bir terminalde test edin
curl http://localhost:8001/api/status
```

### 3. Environment Variables (.env) - Ubuntu 24.04

```bash
# backend/.env dosyası:
MONGO_URL="mongodb://localhost:27017"
DB_NAME="kpa_production"
GEMINI_API_KEY="[GOOGLE-GEMINI-API-ANAHTARINIZ]"

# Ubuntu 24.04 için optimizasyonlar:
ENVIRONMENT="production"
DEBUG="false"
LOG_LEVEL="INFO"
WORKERS="4"  # CPU core sayınıza göre ayarlayın

# Güvenlik ayarları:
SECRET_KEY="[GUVENLI-RASTGELE-ANAHTAR-32-KARAKTER]"
ALLOWED_HOSTS="localhost,127.0.0.1,[DOMAIN-ADINIZ]"

# Performance ayarları (Ubuntu 24.04):
MAX_WORKERS="8"
TIMEOUT="300"
KEEPALIVE="2"
```

#### Güvenli Secret Key Oluşturma

```bash
# Güvenli secret key oluşturun
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Veya OpenSSL ile:
openssl rand -base64 32
```

### 4. Frontend Kurulumu (Ubuntu 24.04 LTS)

```bash
cd /opt/kpa/frontend

# Node.js ve npm versiyonlarını kontrol edin
node --version  # v20.x.x (Ubuntu 24.04 için önerilen)
npm --version   # 10.x.x
yarn --version  # 1.22.x

# Node.js memory limitini artırın (büyük projeler için)
export NODE_OPTIONS="--max-old-space-size=4096"

# Bağımlılıkları yükleyin (Yarn önerilen)
yarn install --frozen-lockfile

# Alternatif olarak npm:
# npm ci --production=false

# Development dependencies kontrolü
yarn list --depth=0

# Production build oluşturun
yarn build

# Build çıktısını kontrol edin
ls -la build/
du -sh build/

# Environment variables ayarlayın:
cp .env.example .env 2>/dev/null || true
nano .env
```

#### Frontend Environment Variables (Ubuntu 24.04)

```bash
# frontend/.env dosyası:
REACT_APP_BACKEND_URL=https://[DOMAIN-ADINIZ]/api
REACT_APP_ENV=production
REACT_APP_VERSION=1.0.0

# Development ayarları:
# REACT_APP_BACKEND_URL=http://localhost:8001/api
# REACT_APP_ENV=development

# Build optimizasyonları (Ubuntu 24.04):
GENERATE_SOURCEMAP=false
INLINE_RUNTIME_CHUNK=false
IMAGE_INLINE_SIZE_LIMIT=0

# Performance monitoring (opsiyonel):
REACT_APP_ENABLE_ANALYTICS=false
```

#### Build Optimizasyonu

```bash
# Production build ile bundle analizi
cd /opt/kpa/frontend
yarn build

# Bundle boyutunu analiz edin
npx webpack-bundle-analyzer build/static/js/*.js

# Gzip sıkıştırma simülasyonu
find build -name "*.js" -o -name "*.css" | xargs gzip -c > /dev/null
echo "Gzip sıkıştırma testi başarılı"
```

### 5. Frontend Environment Variables

```bash
# frontend/.env dosyası:
REACT_APP_BACKEND_URL=https://[DOMAIN-ADINIZ]/api
REACT_APP_ENV=production
```

---

## 🌐 Web Sunucusu Konfigürasyonu (Ubuntu 24.04 LTS)

### Nginx ile Reverse Proxy (Ubuntu 24.04)

```bash
# Nginx kurulumu
sudo apt update
sudo apt install -y nginx

# Nginx versiyonunu kontrol edin
nginx -v  # nginx/1.24.x

# Nginx servisini başlatın
sudo systemctl start nginx
sudo systemctl enable nginx

# Nginx durumunu kontrol edin
sudo systemctl status nginx

# Firewall ayarları
sudo ufw allow 'Nginx Full'
sudo ufw status

# Site konfigürasyonu oluşturun
sudo nano /etc/nginx/sites-available/kpa
```

#### Nginx Konfigürasyon Dosyası (Ubuntu 24.04 Optimized)

```nginx
# /etc/nginx/sites-available/kpa
server {
    listen 80;
    listen [::]:80;
    server_name [DOMAIN-ADINIZ] www.[DOMAIN-ADINIZ];
    
    # Security headers (Ubuntu 24.04 için güncellenmiş)
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://api.google.com" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    
    # Modern gzip konfigürasyonu
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_comp_level 6;
    gzip_proxied any;
    gzip_disable "msie6";
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/javascript
        application/xml+rss
        application/json
        application/xml
        image/svg+xml;

    # Brotli compression (Ubuntu 24.04'te mevcut)
    brotli on;
    brotli_comp_level 4;
    brotli_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Frontend static files
    location / {
        root /opt/kpa/frontend/build;
        try_files $uri $uri/ /index.html;
        index index.html index.htm;
        
        # Modern cache headers
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            add_header X-Content-Type-Options nosniff;
            access_log off;
        }
        
        # HTML files cache
        location ~* \.(html)$ {
            expires 1h;
            add_header Cache-Control "public, must-revalidate";
        }
    }
    
    # Backend API reverse proxy
    location /api {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # CORS headers
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization" always;
        
        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin * always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
            add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization" always;
            add_header Access-Control-Max-Age 1728000;
            add_header Content-Type 'text/plain charset=UTF-8';
            add_header Content-Length 0;
            return 204;
        }
        
        # File upload ve timeout ayarları
        client_max_body_size 100M;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # Nginx status (admin için)
    location /nginx_status {
        stub_status on;
        access_log off;
        allow 127.0.0.1;
        deny all;
    }

    # Security: deny access to hidden files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Security: deny access to backup and temporary files
    location ~* \.(bak|backup|old|tmp|temp|log)$ {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Robots.txt
    location = /robots.txt {
        allow all;
        log_not_found off;
        access_log off;
    }
}
```

#### Nginx Site Aktivasyonu ve Test

```bash
# Konfigürasyon dosyasını test edin
sudo nginx -t

# Site'ı aktifleştirin
sudo ln -s /etc/nginx/sites-available/kpa /etc/nginx/sites-enabled/

# Default site'ı deaktive edin (opsiyonel)
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx'i yeniden yükleyin
sudo systemctl reload nginx

# Nginx durumunu kontrol edin
sudo systemctl status nginx

# Log dosyalarını kontrol edin
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### SSL Sertifikası (Let's Encrypt - Ubuntu 24.04)

```bash
# Certbot ve Nginx plugin kurulumu
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# Certbot versiyonunu kontrol edin
certbot --version

# SSL sertifikası alın (interaktif)
sudo certbot --nginx -d [DOMAIN-ADINIZ] -d www.[DOMAIN-ADINIZ]

# Veya otomatik mod:
sudo certbot --nginx -d [DOMAIN-ADINIZ] -d www.[DOMAIN-ADINIZ] --non-interactive --agree-tos --email [EMAIL-ADRESINIZ]

# Sertifika durumunu kontrol edin
sudo certbot certificates

# Test renewal
sudo certbot renew --dry-run

# Otomatik yenileme için crontab ayarlayın
sudo crontab -e
# Şu satırı ekleyin:
0 12 * * * /usr/bin/certbot renew --quiet --post-hook "systemctl reload nginx"

# Alternatif olarak systemd timer kullanın
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
sudo systemctl status certbot.timer
```

#### SSL Konfigürasyonu Doğrulama

```bash
# SSL Labs test için (manuel kontrol)
echo "SSL test URL: https://www.ssllabs.com/ssltest/analyze.html?d=[DOMAIN-ADINIZ]"

# Command line SSL testi
openssl s_client -connect [DOMAIN-ADINIZ]:443 -servername [DOMAIN-ADINIZ] < /dev/null

# Nginx SSL konfigürasyonunu test edin
sudo nginx -t

# SSL certificate detaylarını görüntüleyin
sudo openssl x509 -in /etc/letsencrypt/live/[DOMAIN-ADINIZ]/fullchain.pem -text -noout
```

---

## 🔧 Servis Konfigürasyonu (Ubuntu 24.04 LTS)

### Systemd ile Backend Servisi

```bash
# KPA kullanıcısı oluşturun (güvenlik için)
sudo useradd --system --create-home --shell /bin/bash kpa
sudo usermod -aG www-data kpa

# Proje dizini sahipliğini ayarlayın
sudo chown -R kpa:kpa /opt/kpa
sudo chmod -R 755 /opt/kpa

# Log dizinleri oluşturun
sudo mkdir -p /var/log/kpa
sudo chown kpa:kpa /var/log/kpa

# Systemd servis dosyası oluşturun
sudo nano /etc/systemd/system/kpa-backend.service
```

#### KPA Backend Systemd Service (Ubuntu 24.04)

```ini
# /etc/systemd/system/kpa-backend.service
[Unit]
Description=KPA Backend Service - Kurumsal Prosedür Asistanı
Documentation=https://github.com/[username]/kurumsal-prosedur-asistani
After=network.target mongodb.service
Wants=mongodb.service

[Service]
Type=exec
User=kpa
Group=kpa
WorkingDirectory=/opt/kpa/backend
Environment=PATH=/opt/kpa/backend/venv/bin
EnvironmentFile=/opt/kpa/backend/.env

# Güvenlik ayarları (Ubuntu 24.04)
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/kpa /var/log/kpa
PrivateDevices=yes
ProtectControlGroups=yes
ProtectKernelModules=yes
ProtectKernelTunables=yes
RestrictRealtime=yes
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

# Ana komut
ExecStart=/opt/kpa/backend/venv/bin/uvicorn server:app \
    --host 0.0.0.0 \
    --port 8001 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --log-level info \
    --access-log \
    --log-config /opt/kpa/backend/logging.conf

# Health check
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
Restart=always
RestartSec=10
TimeoutStopSec=30

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=kpa-backend

[Install]
WantedBy=multi-user.target
```

#### Logging Konfigürasyonu

```bash
# Logging konfigürasyon dosyası oluşturun
sudo nano /opt/kpa/backend/logging.conf
```

```ini
# /opt/kpa/backend/logging.conf
[loggers]
keys=root,uvicorn.error,uvicorn.access

[handlers]
keys=default,access

[formatters]
keys=default,access

[logger_root]
level=INFO
handlers=default

[logger_uvicorn.error]
level=INFO
handlers=default
propagate=1
qualname=uvicorn.error

[logger_uvicorn.access]
level=INFO
handlers=access
propagate=0
qualname=uvicorn.access

[handler_default]
class=logging.handlers.RotatingFileHandler
formatter=default
args=('/var/log/kpa/backend.log', 'a', 10485760, 5)

[handler_access]
class=logging.handlers.RotatingFileHandler
formatter=access
args=('/var/log/kpa/access.log', 'a', 10485760, 5)

[formatter_default]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
datefmt=%Y-%m-%d %H:%M:%S

[formatter_access]
format=%(asctime)s - %(client_addr)s - "%(request_line)s" %(status_code)s
```

#### Systemd Servisini Başlatma

```bash
# Systemd daemon'ı yeniden yükleyin
sudo systemctl daemon-reload

# Servisi enable edin (boot'ta otomatik başlama)
sudo systemctl enable kpa-backend

# Servisi başlatın
sudo systemctl start kpa-backend

# Servis durumunu kontrol edin
sudo systemctl status kpa-backend

# Servis loglarını izleyin
sudo journalctl -u kpa-backend -f

# Servis performansını kontrol edin
sudo systemctl show kpa-backend --property=MainPID,ActiveState,SubState,LoadState
```

### PM2 ile Alternatif Kurulum (Ubuntu 24.04 - Önerilen)

```bash
# PM2'yi global olarak kurun
sudo npm install -g pm2@latest

# PM2 versiyonunu kontrol edin
pm2 --version

# Backend için PM2 ecosystem dosyası oluşturun
cd /opt/kpa/backend
sudo -u kpa nano ecosystem.config.js
```

```javascript
// /opt/kpa/backend/ecosystem.config.js
module.exports = {
  apps: [{
    name: 'kpa-backend',
    script: 'venv/bin/uvicorn',
    args: 'server:app --host 0.0.0.0 --port 8001 --workers 4 --worker-class uvicorn.workers.UvicornWorker',
    cwd: '/opt/kpa/backend',
    user: 'kpa',
    
    // Process management
    instances: 1,
    exec_mode: 'fork',
    autorestart: true,
    watch: false,
    max_memory_restart: '2G',
    
    // Logging
    log_file: '/var/log/kpa/pm2-combined.log',
    out_file: '/var/log/kpa/pm2-out.log',
    error_file: '/var/log/kpa/pm2-error.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    
    // Environment
    env: {
      NODE_ENV: 'production',
      PYTHONPATH: '/opt/kpa/backend',
      PATH: '/opt/kpa/backend/venv/bin:' + process.env.PATH
    },
    
    // Health monitoring
    min_uptime: '10s',
    max_restarts: 10,
    
    // Advanced settings
    kill_timeout: 5000,
    listen_timeout: 8000,
    
    // Cron restart (günlük 3:00'da yeniden başlat)
    cron_restart: '0 3 * * *'
  }]
};
```

#### PM2 ile Başlatma ve Yönetim

```bash
# PM2'yi kpa kullanıcısı olarak başlatın
sudo -u kpa pm2 start /opt/kpa/backend/ecosystem.config.js

# PM2 durumunu kontrol edin
sudo -u kpa pm2 status

# Logları izleyin
sudo -u kpa pm2 logs kpa-backend --lines 50

# PM2 monitoring
sudo -u kpa pm2 monit

# PM2 konfigürasyonunu kaydedin
sudo -u kpa pm2 save

# Sistem boot'unda otomatik başlatma için
sudo -u kpa pm2 startup systemd
# Çıktıdaki komutu root olarak çalıştırın

# PM2 web monitoring (opsiyonel)
sudo -u kpa pm2 web
```

#### PM2 Yönetim Komutları

```bash
# Servis yeniden başlatma
sudo -u kpa pm2 restart kpa-backend

# Servis durdurma
sudo -u kpa pm2 stop kpa-backend

# Servis silme
sudo -u kpa pm2 delete kpa-backend

# Tüm servisleri yeniden başlatma
sudo -u kpa pm2 restart all

# Memory kullanımını kontrol etme
sudo -u kpa pm2 show kpa-backend

# Process scaling (load arttığında)
sudo -u kpa pm2 scale kpa-backend 6
```

---

## 🗃️ Veritabanı Konfigürasyonu (Ubuntu 24.04 LTS)

### MongoDB Güvenlik Ayarları

```bash
# MongoDB shell'e bağlanın
mongosh

# Veya authentication varsa:
# mongosh --username admin --password --authenticationDatabase admin
```

```javascript
// MongoDB shell komutları

// 1. Admin kullanıcısı oluşturun
use admin
db.createUser({
  user: "kpa_admin",
  pwd: passwordPrompt(), // Güvenli şifre girin
  roles: [
    "userAdminAnyDatabase", 
    "dbAdminAnyDatabase", 
    "readWriteAnyDatabase",
    "clusterAdmin"
  ]
})

// 2. Uygulama veritabanı oluşturun
use kpa_production
db.createUser({
  user: "kpa_user", 
  pwd: passwordPrompt(), // Uygulama şifresi girin
  roles: ["readWrite"]
})

// 3. İndeksleri oluşturun (performans için)
// Documents collection
db.documents.createIndex({ "filename": 1 })
db.documents.createIndex({ "created_at": -1 })
db.documents.createIndex({ "embeddings_created": 1 })
db.documents.createIndex({ "id": 1 }, { unique: true })

// Chat sessions collection
db.chat_sessions.createIndex({ "session_id": 1, "created_at": -1 })
db.chat_sessions.createIndex({ "created_at": -1 })

// TTL indeks (30 gün sonra chat geçmişini sil)
db.chat_sessions.createIndex(
  { "created_at": 1 }, 
  { expireAfterSeconds: 2592000 }
)

// Metin arama indeksi (opsiyonel)
db.documents.createIndex({ 
  "filename": "text", 
  "content": "text" 
}, { 
  default_language: "turkish",
  name: "document_text_search" 
})

// Veritabanı istatistiklerini görüntüleyin
db.stats()
quit()
```

### MongoDB Authentication Aktifleştirme (Ubuntu 24.04)

```bash
# MongoDB konfigürasyon dosyasını düzenleyin
sudo nano /etc/mongod.conf
```

```yaml
# /etc/mongod.conf - Ubuntu 24.04 için güvenlik optimizasyonu
storage:
  dbPath: /var/lib/mongodb
  journal:
    enabled: true
  wiredTiger:
    engineConfig:
      cacheSizeGB: 2  # Sunucunuzun RAM'inin %50'si
      directoryForIndexes: true
    collectionConfig:
      blockCompressor: snappy
    indexConfig:
      prefixCompression: true

systemLog:
  destination: file
  logAppend: true
  path: /var/log/mongodb/mongod.log
  logRotate: reopen
  component:
    accessControl:
      verbosity: 1
    command:
      verbosity: 1

net:
  port: 27017
  bindIp: 127.0.0.1  # Sadece localhost erişimi
  maxIncomingConnections: 100
  compression:
    compressors: snappy,zstd

processManagement:
  timeZoneInfo: /usr/share/zoneinfo
  fork: true
  pidFilePath: /var/run/mongodb/mongod.pid

# Güvenlik ayarları
security:
  authorization: enabled
  javascriptEnabled: false  # JavaScript execution'ı kapat

# Performans ayarları
operationProfiling:
  slowOpThresholdMs: 100
  mode: slowOp

# Replikasyon (gelecek için hazırlık)
#replication:
#  replSetName: "kpa-replica-set"

# Sharding (büyük veri için)
#sharding:
#  clusterRole: shardsvr
```

#### MongoDB Servisini Yeniden Başlatma

```bash
# Konfigürasyonu test edin
sudo mongod --config /etc/mongod.conf --fork --logpath /tmp/mongod-test.log
sudo pkill mongod

# MongoDB'yi yeniden başlatın
sudo systemctl restart mongod

# Servis durumunu kontrol edin
sudo systemctl status mongod

# Authentication testi
mongosh --username kpa_admin --password --authenticationDatabase admin

# Connection string test
mongosh "mongodb://kpa_user:UYGULAMA_SIFRESI@localhost:27017/kpa_production"
```

### Backend .env Dosyasını Güncelleme

```bash
# backend/.env dosyasını authentication bilgileri ile güncelleyin
nano /opt/kpa/backend/.env
```

```bash
# /opt/kpa/backend/.env - Authentication ile
MONGO_URL="mongodb://kpa_user:UYGULAMA_SIFRESI_BURAYA@localhost:27017/kpa_production"
DB_NAME="kpa_production"
GEMINI_API_KEY="your-gemini-api-key-here"

# Connection pool ayarları
MONGO_MAX_POOL_SIZE="20"
MONGO_MIN_POOL_SIZE="5"
MONGO_MAX_IDLE_TIME_MS="30000"
MONGO_SERVER_SELECTION_TIMEOUT_MS="5000"

# Diğer ayarlar...
```

---

## 🔍 Monitoring ve Loglama (Ubuntu 24.04 LTS)

### Sistem Monitoring Kurulumu

```bash
# Sistem monitoring araçları kurulumu
sudo apt update
sudo apt install -y htop iotop nethogs ncdu tree

# Log analiz araçları
sudo apt install -y multitail ccze lnav

# Performance monitoring
sudo apt install -y sysstat dstat glances

# Disk ve network monitoring
sudo apt install -y iftop vnstat

# Vnstat konfigürasyonu
sudo systemctl enable vnstat
sudo systemctl start vnstat
```

### Log Konfigürasyonu ve Yönetimi

```bash
# Log dizinleri oluşturun
sudo mkdir -p /var/log/kpa/{nginx,mongodb,backend,frontend}
sudo chown -R kpa:kpa /var/log/kpa
sudo chmod -R 755 /var/log/kpa

# Logrotate konfigürasyonu
sudo nano /etc/logrotate.d/kpa
```

```bash
# /etc/logrotate.d/kpa
/var/log/kpa/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 kpa kpa
    sharedscripts
    postrotate
        # PM2 logları için
        if [ -f /home/kpa/.pm2/pm2.pid ]; then
            sudo -u kpa pm2 reloadLogs
        fi
        # Nginx reload
        if [ -f /var/run/nginx.pid ]; then
            /usr/sbin/nginx -s reopen
        fi
    endscript
}

/var/log/nginx/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 www-data www-data
    sharedscripts
    postrotate
        if [ -f /var/run/nginx.pid ]; then
            /usr/sbin/nginx -s reopen
        fi
    endscript
}
```

### Health Check Script'leri

```bash
# Health check script oluşturun
sudo nano /opt/kpa/scripts/health-check.sh
```

```bash
#!/bin/bash
# /opt/kpa/scripts/health-check.sh - Ubuntu 24.04 KPA Health Check

# Renk kodları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

LOG_FILE="/var/log/kpa/health-check.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Log function
log_message() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Check services
check_service() {
    if systemctl is-active --quiet "$1"; then
        log_message "${GREEN}[OK]${NC} $1 is running"
        return 0
    else
        log_message "${RED}[ERROR]${NC} $1 is not running"
        return 1
    fi
}

# Check port
check_port() {
    if nc -z localhost "$1" 2>/dev/null; then
        log_message "${GREEN}[OK]${NC} Port $1 is open"
        return 0
    else
        log_message "${RED}[ERROR]${NC} Port $1 is not accessible"
        return 1
    fi
}

# Check URL
check_url() {
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$1" --max-time 10)
    if [ "$HTTP_CODE" -eq 200 ]; then
        log_message "${GREEN}[OK]${NC} $1 returned HTTP $HTTP_CODE"
        return 0
    else
        log_message "${RED}[ERROR]${NC} $1 returned HTTP $HTTP_CODE"
        return 1
    fi
}

# Main health check
main() {
    log_message "\n=== KPA Health Check - $TIMESTAMP ==="
    
    # System resources
    MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
    DISK_USAGE=$(df / | awk 'NR==2{printf "%s", $5}' | sed 's/%//')
    LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    
    log_message "Memory Usage: ${MEMORY_USAGE}%"
    log_message "Disk Usage: ${DISK_USAGE}%"
    log_message "Load Average: ${LOAD_AVG}"
    
    # Warning thresholds
    if (( $(echo "$MEMORY_USAGE > 80" | bc -l) )); then
        log_message "${YELLOW}[WARNING]${NC} High memory usage: ${MEMORY_USAGE}%"
    fi
    
    if [ "$DISK_USAGE" -gt 80 ]; then
        log_message "${YELLOW}[WARNING]${NC} High disk usage: ${DISK_USAGE}%"
    fi
    
    # Service checks
    log_message "\n--- Service Status ---"
    check_service "mongod"
    check_service "nginx"
    check_service "kpa-backend" || {
        # PM2 alternatifi kontrol et
        if sudo -u kpa pm2 describe kpa-backend >/dev/null 2>&1; then
            PM2_STATUS=$(sudo -u kpa pm2 describe kpa-backend | grep "status" | awk '{print $4}')
            if [ "$PM2_STATUS" = "online" ]; then
                log_message "${GREEN}[OK]${NC} kpa-backend (PM2) is running"
            else
                log_message "${RED}[ERROR]${NC} kpa-backend (PM2) status: $PM2_STATUS"
            fi
        fi
    }
    
    # Port checks
    log_message "\n--- Port Status ---"
    check_port "27017"  # MongoDB
    check_port "8001"   # Backend
    check_port "80"     # Nginx HTTP
    check_port "443"    # Nginx HTTPS (if SSL enabled)
    
    # Application health checks
    log_message "\n--- Application Health ---"
    check_url "http://localhost:8001/api/status"
    check_url "http://localhost/health"
    
    # MongoDB specific checks
    MONGO_STATUS=$(sudo -u kpa mongosh --quiet --eval "db.adminCommand('ping').ok" kpa_production 2>/dev/null)
    if [ "$MONGO_STATUS" = "1" ]; then
        log_message "${GREEN}[OK]${NC} MongoDB ping successful"
    else
        log_message "${RED}[ERROR]${NC} MongoDB ping failed"
    fi
    
    # Log file sizes
    log_message "\n--- Log File Sizes ---"
    find /var/log/kpa -name "*.log" -exec du -sh {} \; | while read size file; do
        log_message "Log size: $file - $size"
    done
    
    log_message "=== Health Check Completed ===\n"
}

# Create log directory if not exists
mkdir -p "$(dirname "$LOG_FILE")"

# Run main function
main

# Exit with error code if any critical service is down
if ! systemctl is-active --quiet mongod || ! systemctl is-active --quiet nginx; then
    exit 1
fi
```

```bash
# Script'i executable yapın
sudo chmod +x /opt/kpa/scripts/health-check.sh
sudo mkdir -p /opt/kpa/scripts

# Test edin
sudo /opt/kpa/scripts/health-check.sh
```

### Monitoring Dashboard (Grafana + Prometheus - Opsiyonel)

```bash
# Docker ile monitoring stack kurulumu
sudo docker run -d \
  --name=grafana \
  -p 3000:3000 \
  -v grafana-storage:/var/lib/grafana \
  grafana/grafana:latest

# Prometheus node exporter
sudo docker run -d \
  --name=node-exporter \
  -p 9100:9100 \
  --pid=host \
  --restart=unless-stopped \
  prom/node-exporter:latest

# Access
echo "Grafana: http://localhost:3000 (admin/admin)"
echo "Node Exporter: http://localhost:9100/metrics"
```

### Health Check Endpoint'i

```bash
# Backend health check:
curl http://localhost:8001/api/status

# Frontend check:
curl http://localhost/

# MongoDB check:
mongosh --eval "db.adminCommand('ping')"
```

---

## 🐳 Docker ile Kurulum (Alternatif)

### Dockerfile Oluşturma

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

COPY . .

EXPOSE 8001

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
```

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  mongodb:
    image: mongo:6.0
    restart: always
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: password123
    volumes:
      - mongodb_data:/data/db

  backend:
    build: ./backend
    restart: always
    ports:
      - "8001:8001"
    environment:
      - MONGO_URL=mongodb://admin:password123@mongodb:27017/kpa_production?authSource=admin
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      - mongodb
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    restart: always
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  mongodb_data:
```

```bash
# Docker ile çalıştırma:
docker-compose up -d

# Logları izleme:
docker-compose logs -f backend
```

---

## 📊 Performans Optimizasyonu

### Backend Optimizasyonu

```python
# server.py içinde eklenebilecek optimizasyonlar:

# Redis cache (isteğe bağlı):
import redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Connection pooling:
from motor.motor_asyncio import AsyncIOMotorClient
client = AsyncIOMotorClient(
    mongo_url, 
    maxPoolSize=20,
    minPoolSize=5
)

# Async processing:
from fastapi import BackgroundTasks
```

### Frontend Optimizasyonu

```json
// package.json build optimizasyonu:
{
  "scripts": {
    "build": "NODE_ENV=production npm run build:analyze",
    "build:analyze": "npm run build && npx webpack-bundle-analyzer build/static/js/*.js"
  }
}
```

### Database İndeksleme

```javascript
// MongoDB'de indeks oluşturma:
use kpa_production

// Documents collection indeksleri:
db.documents.createIndex({ "filename": 1 })
db.documents.createIndex({ "created_at": -1 })
db.documents.createIndex({ "embeddings_created": 1 })

// Chat sessions indeksleri:
db.chat_sessions.createIndex({ "session_id": 1, "created_at": -1 })
db.chat_sessions.createIndex({ "created_at": -1 })

// TTL indeks (chat geçmişi için):
db.chat_sessions.createIndex(
  { "created_at": 1 }, 
  { expireAfterSeconds: 2592000 } // 30 gün
)
```

---

## 🔧 Bakım ve Güncelleme

### Düzenli Bakım Görevleri

```bash
#!/bin/bash
# /opt/kpa/maintenance.sh

# Log temizleme:
find /var/log/kpa -name "*.log" -mtime +30 -delete

# MongoDB backup:
mongodump --uri="mongodb://kpa_user:SIFRE@localhost:27017/kpa_production" --out=/backup/mongodb/$(date +%Y%m%d)

# Disk kullanımı kontrolü:
df -h / | awk 'FNR==2 {print $5}' | sed 's/%//' | xargs -I {} sh -c 'if [ {} -gt 80 ]; then echo "Disk usage high: {}%"; fi'

# Servis health check:
curl -f http://localhost:8001/api/status || systemctl restart kpa-backend
```

```bash
# Crontab'a ekleme:
sudo crontab -e
# Şu satırları ekleyin:
0 2 * * * /opt/kpa/maintenance.sh
0 3 * * 0 /opt/kpa/backup.sh
```

### Güncelleme Süreci

```bash
#!/bin/bash
# /opt/kpa/update.sh

# Backup oluştur:
./backup.sh

# Git pull (eğer git kullanıyorsanız):
git pull origin main

# Backend güncelleme:
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Frontend güncelleme:
cd ../frontend
yarn install
yarn build

# Servisleri yeniden başlat:
pm2 restart kpa-backend
sudo systemctl reload nginx

echo "Güncelleme tamamlandı!"
```

---

## 🚨 Sorun Giderme

### Yaygın Sorunlar

**1. Backend Başlamıyor:**
```bash
# Log kontrolü:
sudo journalctl -u kpa-backend -f

# Port kontrolü:
sudo netstat -tlnp | grep :8001

# Environment variables:
source backend/venv/bin/activate
python -c "import os; print(os.environ.get('GEMINI_API_KEY', 'NOT SET'))"
```

**2. MongoDB Bağlantı Sorunu:**
```bash
# MongoDB status:
sudo systemctl status mongod

# Connection test:
mongosh --eval "db.adminCommand('ping')"

# Log kontrolü:
sudo tail -f /var/log/mongodb/mongod.log
```

**3. Frontend Build Hatası:**
```bash
# Node.js versiyonu:
node --version  # 18+ olmalı

# Cache temizleme:
yarn cache clean
rm -rf node_modules
yarn install

# Memory artırma:
NODE_OPTIONS="--max-old-space-size=4096" yarn build
```

**4. AI Model Yükleme Hatası:**
```bash
# Python packages:
pip list | grep sentence-transformers
pip list | grep faiss

# Model indirme:
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### Debug Modu

```bash
# Backend debug:
cd backend
source venv/bin/activate
export DEBUG=True
uvicorn server:app --host 0.0.0.0 --port 8001 --reload --log-level debug

# Frontend debug:
cd frontend
yarn start
```

---

## 📞 Destek ve İletişim

### Log Dosyaları Konumları

- **Backend Logs**: `/var/log/kpa/backend.log`
- **Nginx Logs**: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- **MongoDB Logs**: `/var/log/mongodb/mongod.log`
- **PM2 Logs**: `~/.pm2/logs/`

### Performans Metrikleri

```bash
# Sistem kaynakları:
htop
iotop
df -h

# PM2 monitoring:
pm2 monit

# Nginx status:
curl http://localhost/nginx_status
```

---

## 📝 Sürüm Notları

### v1.0.0 (İlk Sürüm)
- ✅ Word doküman işleme (.docx)
- ✅ Google Gemini 2.0 Flash entegrasyonu
- ✅ RAG sistemi (FAISS + SentenceTransformer)
- ✅ Modern React arayüzü
- ✅ MongoDB veritabanı
- ✅ Session tabanlı chat sistemi
- ✅ Responsive tasarım
- ✅ Türkçe dil desteği

### Gelecek Sürümler İçin Planlar
- 📄 PDF doküman desteği
- 📊 Excel dosya işleme
- 🔍 Gelişmiş arama filtreleri
- 📈 Kullanım analytics
- 🔐 Kullanıcı yetkilendirme sistemi
- 🌍 Çoklu dil desteği

---

## ⚖️ Lisans ve Güvenlik

### Güvenlik Önlemleri

```bash
# Firewall konfigürasyonu:
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8001/tcp  # Backend portunu dışarıya kapatın
sudo ufw deny 27017/tcp # MongoDB portunu dışarıya kapatın

# SSL/TLS ayarları (nginx):
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
ssl_prefer_server_ciphers off;
```

### API Key Güvenliği

```bash
# Environment variables güvenliği:
chmod 600 backend/.env
chown www-data:www-data backend/.env

# API key rotation:
# Gemini API anahtarınızı düzenli olarak yenileyin
```

Bu dokümantasyon Kurumsal Prosedür Asistanı (KPA) projesinin production ortamına kurulumu için hazırlanmıştır. Herhangi bir sorun yaşarsanız log dosyalarını kontrol edin ve gerekirse destek isteyin.