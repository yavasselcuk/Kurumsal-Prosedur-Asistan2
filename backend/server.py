from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import asyncio
import json
import aiofiles
from docx import Document
import docx2txt
import textract
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pickle
from emergentintegrations.llm.chat import LlmChat, UserMessage
import tempfile
import io
import mimetypes
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader
from PIL import Image
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Embedding model initialization
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# FAISS index for vector search (will be initialized dynamically)
faiss_index = None
document_chunks = []

# Create the main app without a prefix
app = FastAPI(title="Kurumsal Prosedür Asistanı", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class DocumentGroup(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    color: Optional[str] = "#3b82f6"  # Default blue color
    created_at: datetime = Field(default_factory=datetime.utcnow)
    document_count: int = 0

class DocumentUpload(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_type: str  # .doc, .docx
    file_size: int  # bytes
    content: str
    chunks: List[str]
    chunk_count: int
    embeddings_created: bool = False
    upload_status: str = "processing"  # processing, completed, failed
    error_message: Optional[str] = None
    group_id: Optional[str] = None  # Grup ID'si
    group_name: Optional[str] = None  # Grup adı (cache için)
    tags: List[str] = []  # Etiketler
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None

class DocumentInfo(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    embeddings_created: bool
    upload_status: str
    error_message: Optional[str] = None
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    tags: List[str] = []
    created_at: datetime
    processed_at: Optional[datetime] = None

class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    group_filter: Optional[str] = None  # Sadece belirli gruptan arama

class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    question: str
    answer: str
    context_chunks: List[str]
    source_documents: List[str]  # Kaynak doküman adları
    source_groups: List[str] = []  # Kaynak grup adları
    created_at: datetime = Field(default_factory=datetime.utcnow)

class FavoriteQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    answer: str  # İlk verilen cevap
    original_session_id: str  # Orijinal session ID
    source_documents: List[str] = []  # Kaynak dokümanlar
    tags: List[str] = []  # Kullanıcı etiketleri
    category: Optional[str] = None  # Kategori (İK, Finans, vb.)
    notes: Optional[str] = None  # Kullanıcı notları
    favorite_count: int = 1  # Kaç kez favorilendi
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: Optional[datetime] = None

class FavoriteQuestionInfo(BaseModel):
    id: str
    question: str
    answer_preview: str  # İlk 200 karakter
    original_session_id: str
    source_documents: List[str]
    tags: List[str]
    category: Optional[str]
    notes: Optional[str]
    favorite_count: int
    created_at: datetime
    last_accessed: Optional[datetime]

class SystemStatus(BaseModel):
    total_documents: int
    total_chunks: int
    embedding_model_loaded: bool
    faiss_index_ready: bool
    supported_formats: List[str]
    processing_queue: int
    total_groups: int

class DocumentDeleteResponse(BaseModel):
    message: str
    document_id: str
    deleted_chunks: int

class GroupCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = "#3b82f6"

class DocumentMoveRequest(BaseModel):
    document_ids: List[str]
    group_id: Optional[str] = None  # None = "Gruplandırılmamış"

class FavoriteQuestionRequest(BaseModel):
    session_id: str
    question: str
    answer: str
    source_documents: List[str] = []
    category: Optional[str] = None
    tags: List[str] = []
    notes: Optional[str] = None

class FavoriteQuestionUpdateRequest(BaseModel):
    category: Optional[str] = None
    tags: List[str] = []
    notes: Optional[str] = None

class FAQItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    answer: str
    category: Optional[str] = None
    frequency: int = 1  # Kaç kez soruldu
    similar_questions: List[str] = []  # Benzer sorular
    source_sessions: List[str] = []  # Bu soruyu içeren session'lar
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    manual_override: bool = False  # Manuel olarak eklendi mi?

class FAQGenerateRequest(BaseModel):
    min_frequency: int = 2  # En az kaç kez sorulmuş olmalı
    similarity_threshold: float = 0.7  # Benzer sorular için eşik
    max_faq_items: int = 50  # Maksimum FAQ sayısı
    categories: List[str] = []  # Belirli kategorilerle sınırla

# Helper functions
async def extract_text_from_document(file_content: bytes, filename: str) -> str:
    """Word dokümanından metin çıkarma (.doc ve .docx desteği) - Improved"""
    try:
        file_extension = Path(filename).suffix.lower()
        
        # Geçici dosya oluştur
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        extracted_text = ""
        
        if file_extension == '.docx':
            # DOCX dosyaları için
            try:
                # Method 1: python-docx ile
                doc = Document(temp_file_path)
                text_content = []
                
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        text_content.append(paragraph.text.strip())
                
                # Tablolardan da metin çıkar
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            if cell.text.strip():
                                text_content.append(cell.text.strip())
                
                extracted_text = '\n'.join(text_content)
                
                # Eğer python-docx ile metin çıkarılamazsa, docx2txt kullan
                if not extracted_text.strip():
                    extracted_text = docx2txt.process(temp_file_path)
                    
            except Exception as e:
                logging.warning(f"python-docx failed for {filename}, trying docx2txt: {str(e)}")
                try:
                    extracted_text = docx2txt.process(temp_file_path)
                except Exception as e2:
                    logging.error(f"docx2txt also failed for {filename}: {str(e2)}")
                    raise HTTPException(status_code=400, detail=f"DOCX işleme hatası: {str(e2)}")
        
        elif file_extension == '.doc':
            # DOC dosyaları için - Improved error handling
            try:
                # Method 1: antiword ile (en güvenilir)
                import subprocess
                result = subprocess.run(
                    ['antiword', temp_file_path], 
                    capture_output=True, 
                    text=True, 
                    check=True,
                    timeout=30  # Timeout eklendi
                )
                extracted_text = result.stdout
                
                if not extracted_text.strip():
                    raise Exception("antiword returned empty content")
                
                logging.info(f"Successfully processed {filename} with antiword")
                
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                logging.warning(f"antiword failed for {filename}: {str(e)}, trying textract")
                try:
                    # Method 2: textract ile (fallback)
                    extracted_text = textract.process(temp_file_path, method='antiword').decode('utf-8')
                    
                    if not extracted_text.strip():
                        # Method 3: textract default method
                        extracted_text = textract.process(temp_file_path).decode('utf-8')
                    
                    logging.info(f"Successfully processed {filename} with textract")
                    
                except Exception as e2:
                    logging.error(f"textract also failed for {filename}: {str(e2)}")
                    try:
                        # Method 4: Son çare - olabildiğince basit işleme
                        with open(temp_file_path, 'rb') as f:
                            raw_content = f.read()
                            # Basit metin çıkarma denemesi
                            extracted_text = raw_content.decode('utf-8', errors='ignore')
                            # Binary karakterleri temizle
                            import re
                            extracted_text = re.sub(r'[^\x20-\x7E\n\r\t]', ' ', extracted_text)
                            extracted_text = re.sub(r'\s+', ' ', extracted_text).strip()
                            
                        if len(extracted_text) < 10:  # Çok kısa ise başarısız sayılır
                            raise Exception("Could not extract meaningful text")
                        
                        logging.warning(f"Used fallback text extraction for {filename}")
                        
                    except Exception as e3:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"DOC dosyası işlenemedi. Dosya bozuk olabilir veya desteklenmeyen bir format içeriyor. Lütfen dosyayı DOCX formatında kaydedin ve tekrar deneyin. Hata detayı: {str(e3)}"
                        )
        
        else:
            raise HTTPException(status_code=400, detail=f"Desteklenmeyen dosya formatı: {file_extension}")
        
        # Geçici dosyayı sil
        os.unlink(temp_file_path)
        
        # Metin kontrolü
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Doküman boş veya metin çıkarılamadı")
        
        # Metin temizleme
        cleaned_text = extracted_text.strip()
        # Çok fazla boşluk varsa temizle
        import re
        cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text)  # Çoklu newline'ları düzelt
        cleaned_text = re.sub(r' +', ' ', cleaned_text)  # Çoklu space'leri düzelt
        
        return cleaned_text
        
    except HTTPException:
        raise
    except Exception as e:
        # Geçici dosyayı temizle
        try:
            os.unlink(temp_file_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Doküman işleme hatası: {str(e)}")

def get_file_size_human_readable(size_bytes: int) -> str:
    """Dosya boyutunu human-readable formatta döndür"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"

def validate_file_type(filename: str) -> bool:
    """Dosya tipini validate et"""
    allowed_extensions = {'.doc', '.docx'}
    file_extension = Path(filename).suffix.lower()
    return file_extension in allowed_extensions

def split_text_into_chunks(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Metni parçalara ayırma"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk.strip())
    
    return chunks

async def create_embeddings(chunks: List[str]) -> np.ndarray:
    """Metin parçaları için embedding oluşturma"""
    try:
        embeddings = embedding_model.encode(chunks)
        return embeddings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding oluşturulurken hata: {str(e)}")

async def update_faiss_index():
    """FAISS indeksini güncelleme"""
    global faiss_index, document_chunks
    
    try:
        # Tüm dokümanları veritabanından al
        documents = await db.documents.find({"embeddings_created": True}).to_list(1000)
        
        if not documents:
            return
        
        all_chunks = []
        all_embeddings = []
        
        for doc in documents:
            chunks = doc.get('chunks', [])
            all_chunks.extend(chunks)
            
            # Her chunk için embedding oluştur
            if chunks:
                embeddings = await create_embeddings(chunks)
                all_embeddings.extend(embeddings)
        
        if all_embeddings:
            # FAISS indeksi oluştur
            dimension = len(all_embeddings[0])
            faiss_index = faiss.IndexFlatIP(dimension)  # Inner product for similarity
            
            embeddings_array = np.array(all_embeddings).astype('float32')
            faiss.normalize_L2(embeddings_array)  # Normalize for cosine similarity
            faiss_index.add(embeddings_array)
            
            document_chunks = all_chunks
            
        logging.info(f"FAISS indeksi güncellendi. Toplam chunk sayısı: {len(all_chunks)}")
        
    except Exception as e:
        logging.error(f"FAISS indeksi güncellenirken hata: {str(e)}")

async def search_similar_chunks(query: str, top_k: int = 5) -> List[str]:
    """Sorguya benzer metin parçalarını bulma"""
    global faiss_index, document_chunks
    
    if faiss_index is None or not document_chunks:
        return []
    
    try:
        # Sorgu için embedding oluştur
        query_embedding = embedding_model.encode([query])
        query_embedding = query_embedding.astype('float32')
        faiss.normalize_L2(query_embedding)
        
        # Benzer parçaları ara
        scores, indices = faiss_index.search(query_embedding, top_k)
        
        similar_chunks = []
        for idx in indices[0]:
            if idx < len(document_chunks):
                similar_chunks.append(document_chunks[idx])
        
        return similar_chunks
        
    except Exception as e:
        logging.error(f"Benzer chunk arama hatası: {str(e)}")
        return []

async def search_similar_questions(query: str, min_similarity: float = 0.6, top_k: int = 5) -> List[dict]:
    """Geçmiş sorular arasından semantik olarak benzer olanları bul"""
    try:
        if not query.strip():
            return []
        
        # Geçmiş soruları al (son 100 soru)
        recent_questions = await db.chat_sessions.find(
            {},
            {"question": 1, "created_at": 1, "session_id": 1, "_id": 0}
        ).sort("created_at", -1).limit(100).to_list(100)
        
        if not recent_questions:
            return []
        
        # Query ve geçmiş sorular için embedding oluştur
        query_embedding = embedding_model.encode([query])
        query_embedding = query_embedding.astype('float32')
        
        questions_text = [q["question"] for q in recent_questions]
        questions_embeddings = embedding_model.encode(questions_text)
        questions_embeddings = questions_embeddings.astype('float32')
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(query_embedding)
        faiss.normalize_L2(questions_embeddings)
        
        # Cosine similarity hesapla
        similarities = np.dot(questions_embeddings, query_embedding.T).flatten()
        
        # Benzer soruları filtrele ve sırala
        similar_questions = []
        for i, similarity in enumerate(similarities):
            if similarity >= min_similarity and recent_questions[i]["question"].lower() != query.lower():
                similar_questions.append({
                    "question": recent_questions[i]["question"],
                    "similarity": float(similarity),
                    "session_id": recent_questions[i]["session_id"],
                    "created_at": recent_questions[i]["created_at"]
                })
        
        # Similarity'ye göre sırala ve top_k al
        similar_questions.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_questions[:top_k]
        
    except Exception as e:
        logging.error(f"Benzer soru arama hatası: {str(e)}")
        return []

async def generate_question_suggestions(partial_query: str, limit: int = 5) -> List[dict]:
    """Kısmi sorgu için akıllı soru önerileri üret"""
    try:
        if len(partial_query.strip()) < 3:  # Çok kısa sorgular için öneri yapma
            return []
        
        suggestions = []
        
        # 1. Benzer geçmiş sorular
        similar_questions = await search_similar_questions(partial_query, min_similarity=0.4, top_k=3)
        for sq in similar_questions:
            suggestions.append({
                "type": "similar",
                "text": sq["question"],
                "similarity": sq["similarity"],
                "icon": "🔄"
            })
        
        # 2. Kısmi metin içerikli geçmiş sorular (contains search)
        if len(suggestions) < limit:
            partial_matches = await db.chat_sessions.find(
                {"question": {"$regex": partial_query, "$options": "i"}},
                {"question": 1, "_id": 0}
            ).limit(limit - len(suggestions)).to_list(limit - len(suggestions))
            
            for match in partial_matches:
                if match["question"] not in [s["text"] for s in suggestions]:
                    suggestions.append({
                        "type": "partial",
                        "text": match["question"],
                        "similarity": 0.8,  # Fixed similarity for partial matches
                        "icon": "💭"
                    })
        
        # 3. Doküman içeriği tabanlı öneri (chunk'lar içinde arama)
        if len(suggestions) < limit:
            similar_chunks = await search_similar_chunks(partial_query, top_k=2)
            if similar_chunks:
                # Bu chunk'lara dayalı sorular üret
                chunk_based_questions = [
                    f"Bu konu hakkında detaylı bilgi verir misin?",
                    f"'{partial_query}' ile ilgili prosedürler neler?",
                    f"Bu konudaki adımları açıklar mısın?"
                ]
                
                for i, question in enumerate(chunk_based_questions):
                    if len(suggestions) < limit:
                        suggestions.append({
                            "type": "generated",
                            "text": f"{partial_query.title()} {question[len(partial_query):].lower()}",
                            "similarity": 0.7 - (i * 0.1),
                            "icon": "💡"
                        })
        
        # Similarity'ye göre sırala
        suggestions.sort(key=lambda x: x["similarity"], reverse=True)
        return suggestions[:limit]
        
    except Exception as e:
        logging.error(f"Soru önerisi üretme hatası: {str(e)}")
        return []

async def analyze_question_frequency():
    """Chat geçmişindeki soruların frekans analizini yap"""
    try:
        # Tüm chat session'larını al
        all_sessions = await db.chat_sessions.find(
            {},
            {"question": 1, "session_id": 1, "created_at": 1, "_id": 0}
        ).to_list(1000)
        
        if not all_sessions:
            return {}
        
        # Soruları normalize et ve frekanslarını say
        question_frequencies = {}
        session_mapping = {}
        
        for session in all_sessions:
            question = session["question"].lower().strip()
            
            # Normalizasyon (noktalama işaretlerini kaldır, fazla boşlukları düzelt)
            normalized_question = ' '.join(question.split())
            normalized_question = normalized_question.replace('?', '').replace('.', '').replace(',', '')
            
            if normalized_question not in question_frequencies:
                question_frequencies[normalized_question] = {
                    "count": 0,
                    "original_questions": [],
                    "sessions": []
                }
            
            question_frequencies[normalized_question]["count"] += 1
            question_frequencies[normalized_question]["original_questions"].append(session["question"])
            question_frequencies[normalized_question]["sessions"].append(session["session_id"])
        
        return question_frequencies
        
    except Exception as e:
        logging.error(f"Soru frekansı analizi hatası: {str(e)}")
        return {}

async def generate_faq_from_analytics(min_frequency: int = 2, similarity_threshold: float = 0.7, max_items: int = 50):
    """Analytics verilerinden FAQ oluştur"""
    try:
        # Frekans analizini al
        frequencies = await analyze_question_frequency()
        
        if not frequencies:
            return []
        
        # Minimum frekansı geçen soruları filtrele
        frequent_questions = [
            {
                "question": q,
                "frequency": data["count"],
                "original_questions": data["original_questions"],
                "sessions": data["sessions"]
            }
            for q, data in frequencies.items()
            if data["count"] >= min_frequency
        ]
        
        # Frekansa göre sırala
        frequent_questions.sort(key=lambda x: x["frequency"], reverse=True)
        
        # En fazla max_items kadar al
        frequent_questions = frequent_questions[:max_items]
        
        # Her soru için cevap bul (ilk session'dan)
        faq_items = []
        
        for fq in frequent_questions:
            # İlk session'ı bul ve cevabını al
            first_session_id = fq["sessions"][0]
            session_data = await db.chat_sessions.find_one({"session_id": first_session_id})
            
            if session_data:
                # Benzer soruları bul (semantic similarity kullanarak)
                similar_questions = []
                for other_q in fq["original_questions"][:5]:  # En fazla 5 benzer soru
                    if other_q != fq["question"] and other_q not in similar_questions:
                        similar_questions.append(other_q)
                
                # Kategori belirleme (basit keyword matching)
                category = determine_category_from_question(fq["question"])
                
                faq_item = {
                    "question": fq["original_questions"][0],  # En iyi orijinal soruyu kullan
                    "answer": session_data.get("answer", ""),
                    "category": category,
                    "frequency": fq["frequency"],
                    "similar_questions": similar_questions,
                    "source_sessions": fq["sessions"],
                    "is_active": True,
                    "manual_override": False
                }
                
                faq_items.append(faq_item)
        
        return faq_items
        
    except Exception as e:
        logging.error(f"FAQ oluşturma hatası: {str(e)}")
        return []

def determine_category_from_question(question: str) -> str:
    """Sorudan kategori belirleme (keyword-based)"""
    question_lower = question.lower()
    
    # Keyword mapping
    categories = {
        "İnsan Kaynakları": ["insan kaynakları", "personel", "çalışan", "işe alım", "maaş", "izin", "özlük"],
        "Finans": ["finans", "muhasebe", "bütçe", "ödeme", "fatura", "harcama", "gelir"],
        "İT": ["bilgi işlem", "sistem", "yazılım", "donanım", "network", "güvenlik", "siber"],
        "Operasyon": ["operasyon", "süreç", "prosedür", "iş akışı", "kalite", "üretim"],
        "Hukuk": ["hukuk", "yasal", "sözleşme", "compliance", "mevzuat", "düzenleme"],
        "Satış": ["satış", "müşteri", "pazarlama", "teklif", "sözleşme", "gelir"],
        "Genel": ["genel", "şirket", "kurumsal", "politika", "prosedür", "rehber"]
    }
    
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in question_lower:
                return category
    
    return "Genel"  # Default kategori

async def update_faq_database():
    """FAQ veritabanını otomatik güncelle"""
    try:
        # Yeni FAQ'ları oluştur
        new_faq_items = await generate_faq_from_analytics()
        
        updated_count = 0
        new_count = 0
        
        for item in new_faq_items:
            # Aynı soru zaten var mı kontrol et
            existing = await db.faq_items.find_one({
                "question": item["question"]
            })
            
            if existing:
                # Varsa frekansı güncelle
                await db.faq_items.update_one(
                    {"id": existing["id"]},
                    {
                        "$set": {
                            "frequency": item["frequency"],
                            "source_sessions": item["source_sessions"],
                            "last_updated": datetime.utcnow()
                        }
                    }
                )
                updated_count += 1
            else:
                # Yoksa yeni ekle
                faq_item = FAQItem(**item)
                await db.faq_items.insert_one(faq_item.dict())
                new_count += 1
        
        return {
            "status": "success",
            "updated_items": updated_count,
            "new_items": new_count,
            "total_processed": len(new_faq_items)
        }
        
    except Exception as e:
        logging.error(f"FAQ veritabanı güncelleme hatası: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

async def convert_docx_to_pdf(docx_content: bytes, filename: str) -> bytes:
    """DOCX içeriğini PDF'e dönüştür"""
    try:
        # Geçici dosya oluştur
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            # ReportLab ile PDF oluştur
            doc = SimpleDocTemplate(tmp_pdf.name, pagesize=A4)
            
            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=14,
                spaceAfter=12,
                textColor='black',
                fontName='Helvetica-Bold'
            )
            normal_style = ParagraphStyle(
                'CustomNormal', 
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6,
                textColor='black',
                fontName='Helvetica'
            )
            
            # Content listesi
            story = []
            
            # Başlık ekle
            title = Paragraph(f"<b>{filename}</b>", title_style)
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Doküman içeriğini veritabanından direkt kullan
            try:
                # İlk olarak docx_content'in tipini kontrol et
                if isinstance(docx_content, str):
                    # String ise base64 decode edilmiş olabilir
                    try:
                        docx_content = base64.b64decode(docx_content)
                    except:
                        docx_content = docx_content.encode('utf-8')
                
                # Geçici DOCX dosyası oluştur
                with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_docx:
                    tmp_docx.write(docx_content)
                    tmp_docx.flush()
                    
                    # python-docx ile oku
                    try:
                        from docx import Document as DocxDocument
                        docx_doc = DocxDocument(tmp_docx.name)
                        
                        paragraph_count = 0
                        for paragraph in docx_doc.paragraphs:
                            if paragraph.text.strip():
                                # HTML karakterlerini escape et
                                text = paragraph.text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                                p = Paragraph(text, normal_style)
                                story.append(p)
                                story.append(Spacer(1, 6))
                                paragraph_count += 1
                        
                        if paragraph_count == 0:
                            # Eğer hiç paragraf yoksa, raw content'i göster
                            story.append(Paragraph("Doküman içeriği metin formatında görüntülenemiyor.", normal_style))
                        
                    except Exception as docx_parse_error:
                        logging.error(f"DOCX parsing error: {str(docx_parse_error)}")
                        # DOCX parse edilemezse temel bilgi göster
                        error_text = f"Doküman parse edilemedi: {str(docx_parse_error)}"
                        story.append(Paragraph(error_text, normal_style))
                        story.append(Spacer(1, 12))
                        story.append(Paragraph("Doküman mevcut ancak içeriği görüntülenemiyor.", normal_style))
                    
                    # Geçici DOCX dosyasını sil
                    try:
                        os.unlink(tmp_docx.name)
                    except:
                        pass
                    
            except Exception as content_error:
                logging.error(f"Content processing error: {str(content_error)}")
                # Content işlenemezse genel hata göster
                error_text = f"İçerik işleme hatası: {str(content_error)}"
                story.append(Paragraph(error_text, normal_style))
            
            # PDF oluştur
            doc.build(story)
            
            # PDF içeriğini oku
            with open(tmp_pdf.name, 'rb') as pdf_file:
                pdf_content = pdf_file.read()
            
            # Geçici PDF dosyasını sil
            try:
                os.unlink(tmp_pdf.name)
            except:
                pass
            
            return pdf_content
            
    except Exception as e:
        logging.error(f"DOCX to PDF conversion error: {str(e)}")
        # Hata durumunda basit PDF oluştur
        return create_error_pdf(filename, str(e))

def create_error_pdf(filename: str, error_message: str) -> bytes:
    """Hata durumunda basit PDF oluştur"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            c = canvas.Canvas(tmp_pdf.name, pagesize=A4)
            width, height = A4
            
            # Başlık
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 50, f"Doküman: {filename}")
            
            # Hata mesajı
            c.setFont("Helvetica", 12)
            c.drawString(50, height - 100, "PDF Dönüştürme Hatası:")
            c.drawString(50, height - 120, error_message)
            
            c.save()
            
            with open(tmp_pdf.name, 'rb') as pdf_file:
                pdf_content = pdf_file.read()
            
            os.unlink(tmp_pdf.name)
            return pdf_content
            
    except Exception as e:
        logging.error(f"Error PDF creation failed: {str(e)}")
        return b""  # Boş bytes döndür

async def get_pdf_metadata(pdf_content: bytes) -> dict:
    """PDF metadata bilgilerini çıkar"""
    try:
        # PDF'yi geçici dosyaya yaz
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            tmp_pdf.write(pdf_content)
            tmp_pdf.flush()
            
            # pypdf ile metadata oku
            with open(tmp_pdf.name, 'rb') as pdf_file:
                pdf_reader = PdfReader(pdf_file)
                
                metadata = {
                    "page_count": len(pdf_reader.pages),
                    "file_size": len(pdf_content),
                    "file_size_human": format_file_size(len(pdf_content))
                }
                
                # PDF info varsa ekle
                if pdf_reader.metadata:
                    if pdf_reader.metadata.title:
                        metadata["title"] = pdf_reader.metadata.title
                    if pdf_reader.metadata.author:
                        metadata["author"] = pdf_reader.metadata.author
                    if pdf_reader.metadata.creator:
                        metadata["creator"] = pdf_reader.metadata.creator
                    if pdf_reader.metadata.producer:
                        metadata["producer"] = pdf_reader.metadata.producer
                
            os.unlink(tmp_pdf.name)
            return metadata
            
    except Exception as e:
        logging.error(f"PDF metadata extraction error: {str(e)}")
        return {
            "page_count": 1,
            "file_size": len(pdf_content),
            "file_size_human": format_file_size(len(pdf_content)),
            "error": str(e)
        }

def format_file_size(size_bytes: int) -> str:
    """Dosya boyutunu human readable formata çevir"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

async def generate_answer_with_gemini(question: str, context_chunks: List[str], session_id: str) -> tuple[str, List[str]]:
    """Gemini ile cevap üretme - kaynak dokümanlarla birlikte"""
    try:
        # Kontekst oluştur
        context = "\n\n".join(context_chunks)
        
        # Kaynak dokümanları bul
        source_documents = []
        if context_chunks:
            for chunk in context_chunks:
                # Her chunk için hangi dokümanlardan geldiğini bul
                docs = await db.documents.find(
                    {"chunks": {"$in": [chunk]}}, 
                    {"filename": 1, "id": 1, "group_name": 1}
                ).to_list(100)
                for doc in docs:
                    doc_info = {
                        "filename": doc["filename"],
                        "id": doc["id"],
                        "group_name": doc.get("group_name", "Gruplandırılmamış")
                    }
                    if doc_info not in source_documents:
                        source_documents.append(doc_info)
        
        # System message - Türkçe prompt with enhanced rules
        system_message = """Sen kurumsal prosedür dokümanlarına dayalı bir asistansın. Sadece verilen doküman içeriğini kullanarak Türkçe cevap ver.

ÖNEMLİ KURALLAR:
1. Sadece verilen kontekst bilgilerini kullan
2. Kontekstde bulunmayan bilgileri asla uydurma
3. Eğer sorunun cevabı kontekstte yoksa "Bu bilgi mevcut dokümanlarımda bulunmamaktadır." de
4. Cevaplarını net, anlaşılır ve profesyonel şekilde ver
5. Mümkün olduğunca detaylı ve yapılandırılmış cevaplar ver

FORMAT KURALLARI:
- Başlıkları **kalın** yaparak vurgula
- Önemli terimleri ve anahtar kelimeleri **kalın** yaz
- Madde listelerini • ile başlat
- Numaralı listeler kullanırken 1., 2., 3. formatını kullan
- Cevabını paragraflar halinde organize et
- Bahsettiğin form adlarını, prosedür kodlarını ve doküman adlarını **kalın** yaz
- Cevabın sonunda KAYNAK bölümü EKLEME (bu sistem tarafından otomatik eklenecek)"""

        # Gemini chat oluştur
        chat = LlmChat(
            api_key=os.environ['GEMINI_API_KEY'],
            session_id=session_id,
            system_message=system_message
        ).with_model("gemini", "gemini-2.0-flash").with_max_tokens(4096)
        
        # Form ve doküman adlarını vurgulama için ek talimat
        enhanced_context = f"""Kontekst Bilgileri:
{context}

NOT: Cevabında form adları, prosedür kodları (örn: IK-P01, IK-F02 gibi) ve doküman isimlerini **kalın** olarak yaz."""
        
        # Kullanıcı mesajı oluştur
        user_message = UserMessage(
            text=f"""{enhanced_context}

Soru: {question}

Lütfen sadece yukarıdaki kontekst bilgilerini kullanarak soruyu cevapla."""
        )
        
        # Cevap al
        response = await chat.send_message(user_message)
        
        # Response ve kaynak dokümanları döndür
        return response, source_documents
        
    except Exception as e:
        logging.error(f"Gemini cevap üretme hatası: {str(e)}")
        return "Üzgünüm, şu anda sorunuzu cevaplayamıyorum. Lütfen daha sonra tekrar deneyin.", []

# API Endpoints
@api_router.get("/")
async def root():
    return {"message": "Kurumsal Prosedür Asistanı API'sine hoş geldiniz!"}

@api_router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Sistem durumunu getir"""
    try:
        doc_count = await db.documents.count_documents({})
        group_count = await db.document_groups.count_documents({})
        chunk_count = len(document_chunks)
        
        return SystemStatus(
            total_documents=doc_count,
            total_chunks=chunk_count,
            embedding_model_loaded=embedding_model is not None,
            faiss_index_ready=faiss_index is not None,
            supported_formats=['.doc', '.docx'],
            processing_queue=0,
            total_groups=group_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sistem durumu alınırken hata: {str(e)}")

# Grup yönetimi endpoint'leri
@api_router.get("/groups")
async def get_groups():
    """Tüm grupları listele"""
    try:
        groups = await db.document_groups.find({}, {"_id": 0}).sort("name", 1).to_list(100)
        
        # Her grup için doküman sayısını hesapla
        for group in groups:
            doc_count = await db.documents.count_documents({"group_id": group["id"]})
            group["document_count"] = doc_count
        
        return {
            "groups": groups,
            "total_count": len(groups)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gruplar alınırken hata: {str(e)}")

@api_router.post("/groups")
async def create_group(request: GroupCreateRequest):
    """Yeni grup oluştur"""
    try:
        # Grup adı benzersizliği kontrolü
        existing = await db.document_groups.find_one({"name": request.name})
        if existing:
            raise HTTPException(status_code=400, detail="Bu isimde bir grup zaten mevcut")
        
        group = DocumentGroup(
            name=request.name,
            description=request.description,
            color=request.color
        )
        
        await db.document_groups.insert_one(group.dict())
        
        return {
            "message": f"'{request.name}' grubu başarıyla oluşturuldu",
            "group": group.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Grup oluşturulurken hata: {str(e)}")

@api_router.put("/groups/{group_id}")
async def update_group(group_id: str, request: GroupCreateRequest):
    """Grup güncelle"""
    try:
        # Grup adı benzersizliği kontrolü (kendi ID'si hariç)
        existing = await db.document_groups.find_one({
            "name": request.name,
            "id": {"$ne": group_id}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Bu isimde bir grup zaten mevcut")
        
        result = await db.document_groups.update_one(
            {"id": group_id},
            {
                "$set": {
                    "name": request.name,
                    "description": request.description,
                    "color": request.color
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Grup bulunamadı")
        
        # İlgili dokümanların group_name'ini güncelle
        await db.documents.update_many(
            {"group_id": group_id},
            {"$set": {"group_name": request.name}}
        )
        
        return {"message": f"'{request.name}' grubu başarıyla güncellendi"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Grup güncellenirken hata: {str(e)}")

@api_router.delete("/groups/{group_id}")
async def delete_group(group_id: str, move_documents: bool = False):
    """Grup sil"""
    try:
        # Grup bilgilerini al
        group = await db.document_groups.find_one({"id": group_id})
        if not group:
            raise HTTPException(status_code=404, detail="Grup bulunamadı")
        
        # Gruptaki doküman sayısını kontrol et
        doc_count = await db.documents.count_documents({"group_id": group_id})
        
        if doc_count > 0 and not move_documents:
            raise HTTPException(
                status_code=400, 
                detail=f"Bu grupta {doc_count} doküman var. Önce dokümanları başka gruba taşıyın veya move_documents=true parametresi kullanın."
            )
        
        if move_documents:
            # Dokümanları "Gruplandırılmamış" duruma getir
            await db.documents.update_many(
                {"group_id": group_id},
                {
                    "$unset": {"group_id": "", "group_name": ""}
                }
            )
        
        # Grubu sil
        result = await db.document_groups.delete_one({"id": group_id})
        
        return {
            "message": f"'{group['name']}' grubu başarıyla silindi",
            "moved_documents": doc_count if move_documents else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Grup silinirken hata: {str(e)}")

@api_router.post("/documents/move")
async def move_documents(request: DocumentMoveRequest):
    """Dokümanları gruba taşı"""
    try:
        if request.group_id:
            # Grup var mı kontrol et
            group = await db.document_groups.find_one({"id": request.group_id})
            if not group:
                raise HTTPException(status_code=404, detail="Hedef grup bulunamadı")
            
            # Dokümanları gruba taşı
            result = await db.documents.update_many(
                {"id": {"$in": request.document_ids}},
                {
                    "$set": {
                        "group_id": request.group_id,
                        "group_name": group["name"]
                    }
                }
            )
            
            message = f"{result.modified_count} doküman '{group['name']}' grubuna taşındı"
        else:
            # Gruplandırılmamış duruma getir
            result = await db.documents.update_many(
                {"id": {"$in": request.document_ids}},
                {
                    "$unset": {"group_id": "", "group_name": ""}
                }
            )
            
            message = f"{result.modified_count} doküman gruplandırılmamış duruma getirildi"
        
        return {
            "message": message,
            "modified_count": result.modified_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dokümanlar taşınırken hata: {str(e)}")

@api_router.post("/upload-document")
async def upload_document(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    group_id: Optional[str] = None
):
    """Word dokümanı yükleme (.doc ve .docx desteği + gruplandırma)"""
    try:
        # Dosya tipini kontrol et
        if not validate_file_type(file.filename):
            raise HTTPException(status_code=400, detail="Sadece .doc ve .docx formatındaki dosyalar desteklenir")
        
        # Dosya boyutunu kontrol et (10MB limit)
        file_content = await file.read()
        file_size = len(file_content)
        max_size = 10 * 1024 * 1024  # 10MB
        
        if file_size > max_size:
            raise HTTPException(
                status_code=400, 
                detail=f"Dosya boyutu çok büyük. Maksimum {get_file_size_human_readable(max_size)} olmalıdır."
            )
        
        # Grup bilgilerini al (eğer belirtilmişse)
        group_name = None
        if group_id:
            group = await db.document_groups.find_one({"id": group_id})
            if not group:
                raise HTTPException(status_code=404, detail="Belirtilen grup bulunamadı")
            group_name = group["name"]
        
        # Word dokümanından metin çıkar
        text_content = await extract_text_from_document(file_content, file.filename)
        
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="Doküman boş veya okunamıyor")
        
        # Metni parçalara ayır
        chunks = split_text_into_chunks(text_content)
        
        # Dokümanı veritabanına kaydet
        document = DocumentUpload(
            filename=file.filename,
            file_type=Path(file.filename).suffix.lower(),
            file_size=file_size,
            content=text_content,
            chunks=chunks,
            chunk_count=len(chunks),
            embeddings_created=False,
            upload_status="processing",
            group_id=group_id,
            group_name=group_name
        )
        
        await db.documents.insert_one(document.dict())
        
        # Embedding oluşturma işlemini background'a at
        background_tasks.add_task(process_document_embeddings, document.id)
        
        response_data = {
            "message": f"Doküman başarıyla yüklendi: {file.filename}",
            "document_id": document.id,
            "file_type": document.file_type,
            "file_size": get_file_size_human_readable(file_size),
            "chunk_count": len(chunks),
            "processing": "Embedding oluşturma işlemi başlatıldı"
        }
        
        if group_name:
            response_data["group"] = {
                "id": group_id,
                "name": group_name
            }
            response_data["message"] += f" ('{group_name}' grubuna eklendi)"
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Doküman yüklenirken hata: {str(e)}")

async def process_document_embeddings(document_id: str):
    """Doküman embedding işleme (background task)"""
    try:
        # Dokümanı bul
        document = await db.documents.find_one({"id": document_id})
        if not document:
            return
        
        # Embedding oluşturma işlemini tamamla
        await db.documents.update_one(
            {"id": document_id},
            {"$set": {"embeddings_created": True}}
        )
        
        # FAISS indeksini güncelle
        await update_faiss_index()
        
        logging.info(f"Doküman işleme tamamlandı: {document_id}")
        
    except Exception as e:
        logging.error(f"Doküman embedding işleme hatası: {str(e)}")

@api_router.post("/ask-question")
async def ask_question(request: QuestionRequest):
    """Soru sorma endpoint'i"""
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Soru boş olamaz")
        
        # Session ID oluştur
        session_id = request.session_id or str(uuid.uuid4())
        
        # Benzer metin parçalarını bul
        similar_chunks = await search_similar_chunks(request.question, top_k=5)
        
        if not similar_chunks:
            return {
                "question": request.question,
                "answer": "Üzgünüm, sorunuzla ilgili bilgi mevcut dokümanlarımda bulunmamaktadır. Lütfen farklı kelimelerle tekrar deneyin.",
                "session_id": session_id,
                "context_found": False
            }
        
        # Gemini ile cevap üret
        answer, source_docs_info = await generate_answer_with_gemini(
            request.question, 
            similar_chunks, 
            session_id
        )
        
        # Kaynak doküman bilgilerini formatla
        source_documents = [doc["filename"] for doc in source_docs_info]
        
        # Cevaba kaynak bilgilerini ekle
        if source_docs_info:
            sources_section = "\n\n---\n\n**📚 Kaynak Dokümanlar:**\n"
            for i, doc_info in enumerate(source_docs_info, 1):
                group_info = f" ({doc_info['group_name']})" if doc_info['group_name'] != "Gruplandırılmamış" else ""
                # Doküman görüntüleme linki oluştur
                doc_link = f"/api/documents/{doc_info['id']}"
                sources_section += f"{i}. **{doc_info['filename']}**{group_info}\n   📎 [Dokümanı Görüntüle]({doc_link})\n\n"
            
            # Cevabın sonuna kaynak bilgilerini ekle
            answer_with_sources = answer + sources_section
        else:
            answer_with_sources = answer
        
        # Chat geçmişini kaydet
        chat_session = ChatSession(
            session_id=session_id,
            question=request.question,
            answer=answer_with_sources,
            context_chunks=similar_chunks,
            source_documents=source_documents
        )
        
        await db.chat_sessions.insert_one(chat_session.dict())
        
        return {
            "question": request.question,
            "answer": answer_with_sources,
            "session_id": session_id,
            "context_found": True,
            "context_chunks_count": len(similar_chunks),
            "source_documents": source_docs_info  # Detaylı kaynak bilgileri
        }
        
    except Exception as e:
        logging.error(f"Soru cevaplama hatası: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Soru cevaplanırken hata: {str(e)}")

@api_router.get("/chat-history/{session_id}")
async def get_chat_history(session_id: str):
    """Chat geçmişini getir"""
    try:
        chat_history = await db.chat_sessions.find(
            {"session_id": session_id}
        ).sort("created_at", 1).to_list(100)
        
        return {
            "session_id": session_id,
            "chat_history": chat_history,
            "message_count": len(chat_history)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat geçmişi alınırken hata: {str(e)}")

@api_router.get("/chat-sessions")
async def get_all_chat_sessions(limit: int = 50, skip: int = 0):
    """Tüm chat session'larını listele (soru geçmişi için)"""
    try:
        # Session'ları gruplandır ve en son mesajı al
        pipeline = [
            {
                "$sort": {"created_at": -1}
            },
            {
                "$group": {
                    "_id": "$session_id",
                    "latest_question": {"$first": "$question"},
                    "latest_answer": {"$first": "$answer"},
                    "latest_created_at": {"$first": "$created_at"},
                    "message_count": {"$sum": 1},
                    "source_documents": {"$first": "$source_documents"},
                    "context_chunks": {"$first": "$context_chunks"}
                }
            },
            {
                "$sort": {"latest_created_at": -1}
            },
            {
                "$skip": skip
            },
            {
                "$limit": limit
            },
            {
                "$project": {
                    "session_id": "$_id",
                    "latest_question": 1,
                    "latest_answer": {"$substr": ["$latest_answer", 0, 200]},  # İlk 200 karakter
                    "latest_created_at": 1,
                    "message_count": 1,
                    "source_documents": 1,
                    "has_sources": {"$gt": [{"$size": {"$ifNull": ["$source_documents", []]}}, 0]},
                    "_id": 0
                }
            }
        ]
        
        chat_sessions = await db.chat_sessions.aggregate(pipeline).to_list(limit)
        
        # Toplam session sayısını al
        total_sessions_pipeline = [
            {"$group": {"_id": "$session_id"}},
            {"$count": "total"}
        ]
        total_result = await db.chat_sessions.aggregate(total_sessions_pipeline).to_list(1)
        total_sessions = total_result[0]["total"] if total_result else 0
        
        return {
            "sessions": chat_sessions,
            "total_sessions": total_sessions,
            "limit": limit,
            "skip": skip,
            "returned_count": len(chat_sessions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat session'ları alınırken hata: {str(e)}")

@api_router.get("/recent-questions")
async def get_recent_questions(limit: int = 10):
    """Son sorulan soruları getir"""
    try:
        recent_questions = await db.chat_sessions.find(
            {},
            {
                "question": 1,
                "created_at": 1,
                "session_id": 1,
                "source_documents": 1,
                "_id": 0
            }
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return {
            "recent_questions": recent_questions,
            "count": len(recent_questions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Son sorular alınırken hata: {str(e)}")

@api_router.post("/replay-question")
async def replay_question(request: dict):
    """Geçmiş bir soruyu tekrar çalıştır"""
    try:
        session_id = request.get("session_id")
        original_question = request.get("question")
        
        if not session_id or not original_question:
            raise HTTPException(status_code=400, detail="session_id ve question alanları gerekli")
        
        # Yeni session ID oluştur
        new_session_id = str(uuid.uuid4())
        
        # Soruyu tekrar çalıştır
        question_request = QuestionRequest(
            question=original_question,
            session_id=new_session_id
        )
        
        # ask_question endpoint'ini kullan
        result = await ask_question(question_request)
        
        return {
            "message": "Soru başarıyla tekrar çalıştırıldı",
            "original_session_id": session_id,
            "new_session_id": new_session_id,
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Soru tekrar çalıştırılırken hata: {str(e)}")

@api_router.get("/suggest-questions")
async def suggest_questions(q: str, limit: int = 5):
    """Kısmi sorgu için akıllı soru önerileri"""
    try:
        if not q or len(q.strip()) < 2:
            return {
                "suggestions": [],
                "query": q,
                "count": 0
            }
        
        suggestions = await generate_question_suggestions(q.strip(), limit=limit)
        
        return {
            "suggestions": suggestions,
            "query": q,
            "count": len(suggestions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Soru önerisi alınırken hata: {str(e)}")

@api_router.get("/similar-questions")
async def get_similar_questions(q: str, similarity: float = 0.6, limit: int = 5):
    """Sorguya semantik olarak benzer geçmiş soruları bul"""
    try:
        if not q or len(q.strip()) < 3:
            return {
                "similar_questions": [],
                "query": q,
                "count": 0
            }
        
        similar_questions = await search_similar_questions(
            q.strip(), 
            min_similarity=similarity, 
            top_k=limit
        )
        
        return {
            "similar_questions": similar_questions,
            "query": q,
            "min_similarity": similarity,
            "count": len(similar_questions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Benzer sorular aranırken hata: {str(e)}")

@api_router.post("/favorites")
async def add_to_favorites(request: FavoriteQuestionRequest):
    """Soruyu favorilere ekle"""
    try:
        # Aynı soru zaten favorilerde mi kontrol et
        existing = await db.favorite_questions.find_one({
            "question": request.question,
            "original_session_id": request.session_id
        })
        
        if existing:
            # Varsa favorite_count'u artır ve last_accessed'i güncelle
            await db.favorite_questions.update_one(
                {"id": existing["id"]},
                {
                    "$inc": {"favorite_count": 1},
                    "$set": {"last_accessed": datetime.utcnow()}
                }
            )
            
            return {
                "message": "Soru zaten favorilerde. Favori sayısı artırıldı.",
                "favorite_id": existing["id"],
                "favorite_count": existing.get("favorite_count", 1) + 1,
                "already_exists": True
            }
        
        # Yeni favori oluştur
        favorite = FavoriteQuestion(
            question=request.question,
            answer=request.answer,
            original_session_id=request.session_id,
            source_documents=request.source_documents,
            category=request.category,
            tags=request.tags,
            notes=request.notes,
            last_accessed=datetime.utcnow()
        )
        
        await db.favorite_questions.insert_one(favorite.dict())
        
        return {
            "message": "Soru favorilere başarıyla eklendi",
            "favorite_id": favorite.id,
            "favorite_count": 1,
            "already_exists": False
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Favori eklenirken hata: {str(e)}")

@api_router.get("/favorites")
async def get_favorites(category: Optional[str] = None, tag: Optional[str] = None, limit: int = 50):
    """Favori soruları listele"""
    try:
        # Filtre oluştur
        filter_query = {}
        if category:
            filter_query["category"] = category
        if tag:
            filter_query["tags"] = {"$in": [tag]}
        
        # Favorileri getir
        favorites = await db.favorite_questions.find(filter_query).sort("last_accessed", -1).limit(limit).to_list(limit)
        
        # FavoriteQuestionInfo formatına çevir
        favorite_list = []
        for fav in favorites:
            answer_preview = fav.get("answer", "")
            if len(answer_preview) > 200:
                answer_preview = answer_preview[:200] + "..."
            
            favorite_info = {
                "id": fav.get("id"),
                "question": fav.get("question"),
                "answer_preview": answer_preview,
                "original_session_id": fav.get("original_session_id"),
                "source_documents": fav.get("source_documents", []),
                "tags": fav.get("tags", []),
                "category": fav.get("category"),
                "notes": fav.get("notes"),
                "favorite_count": fav.get("favorite_count", 1),
                "created_at": fav.get("created_at"),
                "last_accessed": fav.get("last_accessed")
            }
            favorite_list.append(favorite_info)
        
        # İstatistikler
        total_favorites = await db.favorite_questions.count_documents({})
        categories = await db.favorite_questions.distinct("category")
        tags = await db.favorite_questions.distinct("tags")
        
        return {
            "favorites": favorite_list,
            "statistics": {
                "total_favorites": total_favorites,
                "returned_count": len(favorite_list),
                "unique_categories": len([c for c in categories if c]),
                "unique_tags": len(tags),
                "available_categories": [c for c in categories if c],
                "available_tags": tags
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Favoriler alınırken hata: {str(e)}")

@api_router.get("/favorites/{favorite_id}")
async def get_favorite_detail(favorite_id: str):
    """Favori sorunun detayını getir"""
    try:
        favorite = await db.favorite_questions.find_one({"id": favorite_id}, {"_id": 0})
        
        if not favorite:
            raise HTTPException(status_code=404, detail="Favori soru bulunamadı")
        
        # Last accessed'i güncelle
        await db.favorite_questions.update_one(
            {"id": favorite_id},
            {"$set": {"last_accessed": datetime.utcnow()}}
        )
        
        return favorite
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Favori detayı alınırken hata: {str(e)}")

@api_router.put("/favorites/{favorite_id}")
async def update_favorite(favorite_id: str, request: FavoriteQuestionUpdateRequest):
    """Favori soru bilgilerini güncelle"""
    try:
        update_data = {}
        if request.category is not None:
            update_data["category"] = request.category
        if request.tags:
            update_data["tags"] = request.tags
        if request.notes is not None:
            update_data["notes"] = request.notes
        
        if not update_data:
            raise HTTPException(status_code=400, detail="Güncellenecek alan belirtilmedi")
        
        result = await db.favorite_questions.update_one(
            {"id": favorite_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Favori soru bulunamadı")
        
        return {"message": "Favori soru başarıyla güncellendi"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Favori güncellenirken hata: {str(e)}")

@api_router.delete("/favorites/{favorite_id}")
async def delete_favorite(favorite_id: str):
    """Favori soruyu sil"""
    try:
        result = await db.favorite_questions.delete_one({"id": favorite_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Favori soru bulunamadı")
        
        return {"message": "Favori soru başarıyla silindi"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Favori silinirken hata: {str(e)}")

@api_router.post("/favorites/{favorite_id}/replay")
async def replay_favorite_question(favorite_id: str):
    """Favori soruyu tekrar çalıştır"""
    try:
        # Favori soruyu bul
        favorite = await db.favorite_questions.find_one({"id": favorite_id})
        
        if not favorite:
            raise HTTPException(status_code=404, detail="Favori soru bulunamadı")
        
        # Yeni session ID oluştur
        new_session_id = str(uuid.uuid4())
        
        # Soruyu tekrar çalıştır
        question_request = QuestionRequest(
            question=favorite["question"],
            session_id=new_session_id
        )
        
        result = await ask_question(question_request)
        
        # Last accessed'i güncelle
        await db.favorite_questions.update_one(
            {"id": favorite_id},
            {"$set": {"last_accessed": datetime.utcnow()}}
        )
        
        return {
            "message": "Favori soru başarıyla tekrar çalıştırıldı",
            "favorite_id": favorite_id,
            "original_session_id": favorite["original_session_id"],
            "new_session_id": new_session_id,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Favori soru tekrar çalıştırılırken hata: {str(e)}")

@api_router.get("/faq")
async def get_faq_items(category: Optional[str] = None, active_only: bool = True, limit: int = 50):
    """FAQ listesini getir"""
    try:
        # Filtre oluştur
        filter_query = {}
        if category:
            filter_query["category"] = category
        if active_only:
            filter_query["is_active"] = True
        
        # FAQ'ları getir (frekansa göre sıralı)
        faq_items = await db.faq_items.find(filter_query, {"_id": 0}).sort("frequency", -1).limit(limit).to_list(limit)
        
        # İstatistikler
        total_faqs = await db.faq_items.count_documents({})
        active_faqs = await db.faq_items.count_documents({"is_active": True})
        categories = await db.faq_items.distinct("category")
        
        # Toplam soru sayısı
        total_frequency = sum(item.get("frequency", 0) for item in faq_items)
        
        return {
            "faq_items": faq_items,
            "statistics": {
                "total_faqs": total_faqs,
                "active_faqs": active_faqs,
                "returned_count": len(faq_items),
                "available_categories": categories,
                "total_frequency": total_frequency
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FAQ listesi alınırken hata: {str(e)}")

@api_router.post("/faq/generate")
async def generate_faq(request: FAQGenerateRequest):
    """Chat geçmişinden otomatik FAQ oluştur"""
    try:
        # FAQ'ları oluştur
        faq_items = await generate_faq_from_analytics(
            min_frequency=request.min_frequency,
            similarity_threshold=request.similarity_threshold,
            max_items=request.max_faq_items
        )
        
        if not faq_items:
            return {
                "message": "Yeterli veri bulunamadı. FAQ oluşturulamadı.",
                "generated_count": 0,
                "faq_items": []
            }
        
        # Veritabanını güncelle
        update_result = await update_faq_database()
        
        return {
            "message": f"FAQ başarıyla oluşturuldu. {update_result['new_items']} yeni, {update_result['updated_items']} güncellenmiş öğe.",
            "generated_count": len(faq_items),
            "new_items": update_result['new_items'],
            "updated_items": update_result['updated_items'],
            "faq_items": faq_items[:10]  # İlk 10'unu göster
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FAQ oluşturulurken hata: {str(e)}")

@api_router.get("/faq/analytics")
async def get_faq_analytics():
    """FAQ analytics ve istatistikleri"""
    try:
        # Soru frekansı analizi
        frequencies = await analyze_question_frequency()
        
        # En sık sorulan 10 soru
        top_questions = sorted(
            [(q, data["count"]) for q, data in frequencies.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Kategori dağılımı
        category_stats = {}
        faq_items = await db.faq_items.find({}).to_list(1000)
        
        for item in faq_items:
            category = item.get("category", "Genel")
            if category not in category_stats:
                category_stats[category] = {"count": 0, "total_frequency": 0}
            category_stats[category]["count"] += 1
            category_stats[category]["total_frequency"] += item.get("frequency", 0)
        
        # Toplam chat session sayısı
        total_sessions = await db.chat_sessions.count_documents({})
        
        return {
            "total_questions_analyzed": len(frequencies),
            "total_chat_sessions": total_sessions,
            "top_questions": top_questions,
            "category_distribution": category_stats,
            "faq_recommendations": {
                "should_generate": len(top_questions) > 5,
                "recommended_min_frequency": 2,
                "potential_faq_count": len([q for q, c in top_questions if c >= 2])
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FAQ analytics alınırken hata: {str(e)}")

@api_router.post("/faq/{faq_id}/ask")
async def ask_faq_question(faq_id: str):
    """FAQ sorusunu tekrar sor (yeni session ile)"""
    try:
        # FAQ öğesini bul
        faq_item = await db.faq_items.find_one({"id": faq_id})
        
        if not faq_item:
            raise HTTPException(status_code=404, detail="FAQ öğesi bulunamadı")
        
        # Yeni session ID oluştur
        new_session_id = str(uuid.uuid4())
        
        # Soruyu tekrar çalıştır
        question_request = QuestionRequest(
            question=faq_item["question"],
            session_id=new_session_id
        )
        
        result = await ask_question(question_request)
        
        return {
            "message": "FAQ sorusu başarıyla çalıştırıldı",
            "faq_id": faq_id,
            "original_question": faq_item["question"],
            "new_session_id": new_session_id,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FAQ sorusu çalıştırılırken hata: {str(e)}")

@api_router.put("/faq/{faq_id}")
async def update_faq_item(faq_id: str, updates: dict):
    """FAQ öğesini güncelle"""
    try:
        # Güncellenebilir alanları filtrele
        allowed_fields = ["question", "answer", "category", "is_active", "manual_override"]
        update_data = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="Güncellenecek geçerli alan bulunamadı")
        
        update_data["last_updated"] = datetime.utcnow()
        
        result = await db.faq_items.update_one(
            {"id": faq_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="FAQ öğesi bulunamadı")
        
        return {"message": "FAQ öğesi başarıyla güncellendi"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FAQ güncellenirken hata: {str(e)}")

@api_router.delete("/faq/{faq_id}")
async def delete_faq_item(faq_id: str):
    """FAQ öğesini sil"""
    try:
        result = await db.faq_items.delete_one({"id": faq_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="FAQ öğesi bulunamadı")
        
        return {"message": "FAQ öğesi başarıyla silindi"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FAQ silinirken hata: {str(e)}")

@api_router.get("/documents/{document_id}/pdf")
async def serve_document_as_pdf(document_id: str):
    """Dokümanı PDF formatında serve et"""
    try:
        # Dokümanı bul
        document = await db.documents.find_one({"id": document_id})
        
        if not document:
            raise HTTPException(status_code=404, detail="Doküman bulunamadı")
        
        filename = document.get("filename", "document")
        file_content = document.get("content", b"")
        
        if not file_content:
            raise HTTPException(status_code=404, detail="Doküman içeriği bulunamadı")
        
        # Content bytes'a çevir
        if isinstance(file_content, str):
            file_content = file_content.encode('utf-8')
        
        # DOCX/DOC dosyalarını PDF'e çevir
        file_extension = os.path.splitext(filename.lower())[1]
        
        if file_extension in ['.docx', '.doc']:
            # DOCX/DOC'u PDF'e çevir
            pdf_content = await convert_docx_to_pdf(file_content, filename)
        else:
            # Desteklenmeyen format için hata PDF'i oluştur
            pdf_content = create_error_pdf(filename, f"Desteklenmeyen dosya formatı: {file_extension}")
        
        if not pdf_content:
            raise HTTPException(status_code=500, detail="PDF oluşturulamadı")
        
        # PDF metadata'sını al
        metadata = await get_pdf_metadata(pdf_content)
        
        # PDF'i serve et
        response = Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=\"{os.path.splitext(filename)[0]}.pdf\"",
                "Content-Length": str(len(pdf_content)),
                "X-PDF-Pages": str(metadata.get("page_count", 1)),
                "X-Original-Filename": filename
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF serve edilirken hata: {str(e)}")

@api_router.get("/documents/{document_id}/pdf/metadata")
async def get_document_pdf_metadata(document_id: str):
    """Dokümanın PDF metadata bilgilerini al"""
    try:
        # Dokümanı bul
        document = await db.documents.find_one({"id": document_id})
        
        if not document:
            raise HTTPException(status_code=404, detail="Doküman bulunamadı")
        
        filename = document.get("filename", "document")
        file_content = document.get("content", b"")
        
        if not file_content:
            raise HTTPException(status_code=404, detail="Doküman içeriği bulunamadı")
        
        # Content bytes'a çevir
        if isinstance(file_content, str):
            file_content = file_content.encode('utf-8')
        
        # PDF'e çevir
        file_extension = os.path.splitext(filename.lower())[1]
        
        if file_extension in ['.docx', '.doc']:
            pdf_content = await convert_docx_to_pdf(file_content, filename)
        else:
            pdf_content = create_error_pdf(filename, f"Desteklenmeyen dosya formatı: {file_extension}")
        
        if not pdf_content:
            raise HTTPException(status_code=500, detail="PDF metadata alınamadı")
        
        # PDF metadata'sını al
        metadata = await get_pdf_metadata(pdf_content)
        
        # Ek bilgiler ekle
        metadata.update({
            "original_filename": filename,
            "original_format": file_extension,
            "document_id": document_id,
            "pdf_available": True
        })
        
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF metadata alınırken hata: {str(e)}")

@api_router.get("/documents/{document_id}/download")
async def download_document_pdf(document_id: str):
    """Dokümanı PDF olarak download et"""
    try:
        # Dokümanı bul
        document = await db.documents.find_one({"id": document_id})
        
        if not document:
            raise HTTPException(status_code=404, detail="Doküman bulunamadı")
        
        filename = document.get("filename", "document")
        file_content = document.get("content", b"")
        
        if not file_content:
            raise HTTPException(status_code=404, detail="Doküman içeriği bulunamadı")
        
        # Content bytes'a çevir
        if isinstance(file_content, str):
            file_content = file_content.encode('utf-8')
        
        # PDF'e çevir
        file_extension = os.path.splitext(filename.lower())[1]
        
        if file_extension in ['.docx', '.doc']:
            pdf_content = await convert_docx_to_pdf(file_content, filename)
        else:
            pdf_content = create_error_pdf(filename, f"Desteklenmeyen dosya formatı: {file_extension}")
        
        if not pdf_content:
            raise HTTPException(status_code=500, detail="PDF oluşturulamadı")
        
        # PDF'i download olarak serve et
        pdf_filename = f"{os.path.splitext(filename)[0]}.pdf"
        
        response = Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=\"{pdf_filename}\"",
                "Content-Length": str(len(pdf_content)),
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF download edilirken hata: {str(e)}")

@api_router.get("/documents")
async def get_documents(group_id: Optional[str] = None):
    """Yüklenmiş dokümanları listele (gelişmiş + gruplandırma)"""
    try:
        # Filtre oluştur
        filter_query = {}
        if group_id:
            if group_id == "ungrouped":
                filter_query["$or"] = [
                    {"group_id": {"$exists": False}},
                    {"group_id": None}
                ]
            else:
                filter_query["group_id"] = group_id
        
        # Dokümanları getir (içerik hariç)
        documents = await db.documents.find(filter_query, {
            "content": 0,  # İçeriği dahil etme (çok büyük olabilir)
            "chunks": 0    # Chunk'ları dahil etme
        }).sort("created_at", -1).to_list(100)
        
        # Her doküman için ek bilgiler hesapla
        processed_documents = []
        for doc in documents:
            doc_info = {
                "id": doc.get("id"),
                "filename": doc.get("filename"),
                "file_type": doc.get("file_type", "Unknown"),
                "file_size": doc.get("file_size", 0),
                "file_size_human": get_file_size_human_readable(doc.get("file_size", 0)),
                "chunk_count": doc.get("chunk_count", len(doc.get("chunks", []))),
                "embeddings_created": doc.get("embeddings_created", False),
                "upload_status": doc.get("upload_status", "unknown"),
                "error_message": doc.get("error_message"),
                "group_id": doc.get("group_id"),
                "group_name": doc.get("group_name"),
                "tags": doc.get("tags", []),
                "created_at": doc.get("created_at"),
                "processed_at": doc.get("processed_at"),
                "processing_time": None
            }
            
            # Processing time hesapla
            if doc_info["processed_at"] and doc_info["created_at"]:
                try:
                    processing_time = (doc_info["processed_at"] - doc_info["created_at"]).total_seconds()
                    doc_info["processing_time"] = f"{processing_time:.1f}s"
                except:
                    pass
            
            processed_documents.append(doc_info)
        
        # İstatistikler (grup bazında)
        total_count = len(processed_documents)
        completed_count = len([d for d in processed_documents if d["embeddings_created"]])
        processing_count = len([d for d in processed_documents if d["upload_status"] == "processing"])
        failed_count = len([d for d in processed_documents if d["upload_status"] == "failed"])
        total_size = sum(d["file_size"] for d in processed_documents)
        
        # Grup dağılımı
        grouped_documents = {}
        ungrouped_documents = []
        
        for doc in processed_documents:
            if doc["group_id"]:
                group_name = doc["group_name"] or "Bilinmeyen Grup"
                if group_name not in grouped_documents:
                    grouped_documents[group_name] = {
                        "group_id": doc["group_id"],
                        "group_name": group_name,
                        "documents": [],
                        "count": 0
                    }
                grouped_documents[group_name]["documents"].append(doc)
                grouped_documents[group_name]["count"] += 1
            else:
                ungrouped_documents.append(doc)
        
        return {
            "documents": processed_documents,
            "grouped_documents": grouped_documents,
            "ungrouped_documents": ungrouped_documents,
            "statistics": {
                "total_count": total_count,
                "completed_count": completed_count,
                "processing_count": processing_count,
                "failed_count": failed_count,
                "total_size": total_size,
                "total_size_human": get_file_size_human_readable(total_size),
                "group_count": len(grouped_documents),
                "ungrouped_count": len(ungrouped_documents)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dokümanlar alınırken hata: {str(e)}")

@api_router.get("/documents/{document_id}")
async def get_document_details(document_id: str):
    """Tek dokümanın detaylarını getir"""
    try:
        document = await db.documents.find_one({"id": document_id})
        
        if not document:
            raise HTTPException(status_code=404, detail="Doküman bulunamadı")
        
        # Chat geçmişinde bu dokümanın ne kadar kullanıldığını bul
        usage_count = await db.chat_sessions.count_documents({
            "context_chunks": {"$in": document.get("chunks", [])}
        })
        
        return {
            "id": document.get("id"),
            "filename": document.get("filename"),
            "file_type": document.get("file_type"),
            "file_size": document.get("file_size"),
            "file_size_human": get_file_size_human_readable(document.get("file_size", 0)),
            "chunk_count": document.get("chunk_count", len(document.get("chunks", []))),
            "embeddings_created": document.get("embeddings_created", False),
            "upload_status": document.get("upload_status"),
            "error_message": document.get("error_message"),
            "created_at": document.get("created_at"),
            "processed_at": document.get("processed_at"),
            "usage_count": usage_count,
            "content_preview": document.get("content", "")[:500] + "..." if len(document.get("content", "")) > 500 else document.get("content", "")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Doküman detayları alınırken hata: {str(e)}")

@api_router.delete("/documents/{document_id}")
async def delete_document(document_id: str, background_tasks: BackgroundTasks):
    """Doküman silme (gelişmiş)"""
    try:
        # Önce dokümanı bul
        document = await db.documents.find_one({"id": document_id})
        
        if not document:
            raise HTTPException(status_code=404, detail="Doküman bulunamadı")
        
        filename = document.get("filename", "Bilinmeyen dosya")
        chunk_count = document.get("chunk_count", len(document.get("chunks", [])))
        
        # Dokümanı sil
        result = await db.documents.delete_one({"id": document_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Doküman silinemedi")
        
        # Bu dokümanla ilgili chat geçmişini temizle (opsiyonel)
        chat_cleanup_result = await db.chat_sessions.delete_many({
            "context_chunks": {"$in": document.get("chunks", [])}
        })
        
        # FAISS indeksini güncelle (background'da)
        background_tasks.add_task(update_faiss_index)
        
        return DocumentDeleteResponse(
            message=f"'{filename}' dokümanı başarıyla silindi",
            document_id=document_id,
            deleted_chunks=chunk_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Doküman silinirken hata: {str(e)}")

@api_router.delete("/documents")
async def delete_all_documents(background_tasks: BackgroundTasks, confirm: bool = False):
    """Tüm dokümanları sil (tehlikeli işlem)"""
    try:
        if not confirm:
            raise HTTPException(
                status_code=400, 
                detail="Tüm dokümanları silmek için confirm=true parametresi gerekli"
            )
        
        # Tüm dokümanları say
        total_docs = await db.documents.count_documents({})
        
        if total_docs == 0:
            return {"message": "Silinecek doküman bulunamadı", "deleted_count": 0}
        
        # Tüm dokümanları sil
        delete_result = await db.documents.delete_many({})
        
        # Chat geçmişini de temizle
        chat_result = await db.chat_sessions.delete_many({})
        
        # FAISS indeksini sıfırla
        global faiss_index, document_chunks
        faiss_index = None
        document_chunks = []
        
        return {
            "message": f"{delete_result.deleted_count} doküman ve {chat_result.deleted_count} chat kaydı silindi",
            "deleted_documents": delete_result.deleted_count,
            "deleted_chats": chat_result.deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dokümanlar silinirken hata: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Uygulama başlangıcında FAISS indeksini yükle"""
    try:
        await update_faiss_index()
        logger.info("Kurumsal Prosedür Asistanı başlatıldı")
    except Exception as e:
        logger.error(f"Başlangıç hatası: {str(e)}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()