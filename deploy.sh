#!/bin/bash

# Kurumsal Prosedür Asistanı (KPA) Deployment Script
# Bu script projeyi production ortamına deploy etmek için kullanılır

set -e  # Exit on any error

echo "🚀 KPA Deployment Script Başlatılıyor..."

# Renk kodları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker kurulu değil. Lütfen Docker'ı kurun."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose kurulu değil. Lütfen Docker Compose'u kurun."
        exit 1
    fi
    
    print_success "Docker ve Docker Compose kurulu."
}

# Check environment file
check_env() {
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            print_warning ".env dosyası bulunamadı. .env.example'dan kopyalanıyor..."
            cp .env.example .env
            print_warning "Lütfen .env dosyasını düzenleyin ve API anahtarlarınızı ekleyin!"
            read -p "Devam etmek için Enter'a basın..."
        else
            print_error ".env dosyası bulunamadı ve .env.example da mevcut değil."
            exit 1
        fi
    fi
    
    # Check required variables
    if ! grep -q "GEMINI_API_KEY=your-gemini-api-key-here" .env; then
        print_success "Environment variables yapılandırılmış görünüyor."
    else
        print_warning "GEMINI_API_KEY henüz yapılandırılmamış. Lütfen .env dosyasını düzenleyin."
        read -p "Devam etmek istiyor musunuz? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Build and start services
deploy() {
    print_info "Docker images build ediliyor..."
    docker-compose build --no-cache
    
    print_info "Servisler başlatılıyor..."
    docker-compose up -d
    
    print_info "Servislerin başlaması bekleniyor..."
    sleep 30
    
    # Health checks
    print_info "Health check yapılıyor..."
    
    # Backend health check
    if curl -f http://localhost:8001/api/status > /dev/null 2>&1; then
        print_success "Backend servisi çalışıyor."
    else
        print_error "Backend servisi çalışmıyor!"
        docker-compose logs backend
        exit 1
    fi
    
    # Frontend health check
    if curl -f http://localhost/ > /dev/null 2>&1; then
        print_success "Frontend servisi çalışıyor."
    else
        print_error "Frontend servisi çalışmıyor!"
        docker-compose logs frontend
        exit 1
    fi
    
    # MongoDB health check
    if docker-compose exec -T mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
        print_success "MongoDB servisi çalışıyor."
    else
        print_error "MongoDB servisi çalışmıyor!"
        docker-compose logs mongodb
        exit 1
    fi
}

# Show deployment info
show_info() {
    echo
    echo "🎉 Deployment başarıyla tamamlandı!"
    echo
    echo "📋 Servis Bilgileri:"
    echo "   • Frontend: http://localhost"
    echo "   • Backend API: http://localhost:8001/api"
    echo "   • MongoDB: localhost:27017"
    echo
    echo "🔧 Yönetim Komutları:"
    echo "   • Servisleri durdur: docker-compose down"
    echo "   • Logları izle: docker-compose logs -f"
    echo "   • Servisleri yeniden başlat: docker-compose restart"
    echo "   • Durumu kontrol et: docker-compose ps"
    echo
    echo "📊 Monitoring:"
    echo "   • Sistem durumu: curl http://localhost:8001/api/status"
    echo "   • Health check: curl http://localhost/health"
    echo
}

# Backup function
backup() {
    print_info "Backup oluşturuluyor..."
    BACKUP_DIR="backup/$(date +%Y%m%d_%H%M%S)"
    mkdir -p $BACKUP_DIR
    
    # MongoDB backup
    docker-compose exec -T mongodb mongodump --uri="mongodb://admin:kpa_admin_2024@localhost:27017/kpa_production?authSource=admin" --out=/tmp/backup
    docker cp $(docker-compose ps -q mongodb):/tmp/backup $BACKUP_DIR/mongodb
    
    # Configuration backup
    cp -r backend frontend docker-compose.yml .env $BACKUP_DIR/
    
    print_success "Backup oluşturuldu: $BACKUP_DIR"
}

# Main script
main() {
    echo "🤖 Kurumsal Prosedür Asistanı (KPA) Deployment"
    echo "============================================="
    echo
    
    # Parse arguments
    case "${1:-deploy}" in
        "deploy")
            check_docker
            check_env
            deploy
            show_info
            ;;
        "backup")
            backup
            ;;
        "stop")
            print_info "Servisler durduruluyor..."
            docker-compose down
            print_success "Servisler durduruldu."
            ;;
        "restart")
            print_info "Servisler yeniden başlatılıyor..."
            docker-compose restart
            print_success "Servisler yeniden başlatıldı."
            ;;
        "logs")
            docker-compose logs -f
            ;;
        "status")
            docker-compose ps
            echo
            echo "Health Checks:"
            curl -s http://localhost:8001/api/status | jq . || echo "Backend erişilemez"
            curl -s http://localhost/health || echo "Frontend erişilemez"
            ;;
        "clean")
            print_warning "Tüm konteynerler ve veriler silinecek!"
            read -p "Emin misiniz? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                docker-compose down -v --remove-orphans
                docker system prune -f
                print_success "Temizlik tamamlandı."
            fi
            ;;
        "help"|"-h"|"--help")
            echo "Kullanım: $0 [komut]"
            echo
            echo "Komutlar:"
            echo "  deploy   - Uygulamayı deploy et (varsayılan)"
            echo "  backup   - Veritabanı backup'ı al"
            echo "  stop     - Servisleri durdur"
            echo "  restart  - Servisleri yeniden başlat"
            echo "  logs     - Logları izle"
            echo "  status   - Servis durumunu kontrol et"
            echo "  clean    - Tüm konteyner ve verileri sil"
            echo "  help     - Bu yardım mesajını göster"
            ;;
        *)
            print_error "Bilinmeyen komut: $1"
            echo "Yardım için: $0 help"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"