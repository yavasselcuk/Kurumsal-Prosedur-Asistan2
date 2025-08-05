from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import timedelta
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

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'kurumsal-prosedur-asistani-secret-key-2025')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 48

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Security
security = HTTPBearer()

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

class DocumentSearchRequest(BaseModel):
    query: str
    document_ids: List[str] = []  # Specific documents to search in (empty = all)
    group_ids: List[str] = []  # Specific groups to search in (empty = all)
    search_type: str = "text"  # "text", "regex", "exact"
    case_sensitive: bool = False
    max_results: int = 50
    highlight_context: int = 100  # Characters around match to show

class DocumentSearchResult(BaseModel):
    document_id: str
    document_filename: str
    document_group: Optional[str]
    matches: List[dict]  # List of match objects with position, context, highlighted_text
    total_matches: int
    match_score: float  # Relevance score

# Authentication and User Management Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    full_name: str
    role: str = "viewer"  # admin, editor, viewer
    is_active: bool = True
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    created_by: Optional[str] = None  # Admin who created this user

class UserInfo(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str
    role: str = "viewer"

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_info: UserInfo

class PasswordResetRequest(BaseModel):
    email: str

class PasswordReset(BaseModel):
    reset_token: str
    new_password: str

# AI Response Rating Models
class ResponseRating(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    chat_session_id: str  # Reference to ChatSession
    rating: int  # 1-5 stars
    feedback: Optional[str] = None  # User feedback comment
    user_id: Optional[str] = None  # User who rated (if authenticated)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class RatingRequest(BaseModel):
    session_id: str
    chat_session_id: str
    rating: int = Field(ge=1, le=5)  # 1-5 stars validation
    feedback: Optional[str] = None

class RatingStats(BaseModel):
    total_ratings: int
    average_rating: float
    rating_distribution: Dict[int, int]  # {1: count, 2: count, ...}
    recent_feedback: List[dict]

# Authentication Helper Functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    user = await db.users.find_one({"username": username})
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Get current active user"""
    if not current_user.get("is_active", False):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def require_admin(current_user: dict = Depends(get_current_active_user)) -> dict:
    """Require admin role"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

async def require_editor_or_admin(current_user: dict = Depends(get_current_active_user)) -> dict:
    """Require editor or admin role"""
    if current_user.get("role") not in ["admin", "editor"]:
        raise HTTPException(status_code=403, detail="Editor or admin privileges required")
    return current_user

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

async def search_in_documents(
    query: str,
    document_ids: List[str] = None,
    group_ids: List[str] = None,
    search_type: str = "text",
    case_sensitive: bool = False,
    max_results: int = 50,
    highlight_context: int = 100
) -> List[dict]:
    """Dokümanlar içinde metin arama"""
    try:
        # Arama filtreleri oluştur
        search_filter = {}
        
        if document_ids:
            search_filter["id"] = {"$in": document_ids}
        
        if group_ids:
            search_filter["group_id"] = {"$in": group_ids}
        
        # Dokümanları getir
        documents = await db.documents.find(search_filter).to_list(1000)
        
        if not documents:
            return []
        
        search_results = []
        
        for doc in documents:
            doc_id = doc.get("id")
            filename = doc.get("filename", "Unknown")
            group_name = doc.get("group_name", "Gruplandırılmamış")
            chunks = doc.get("chunks", [])
            
            # Her dokümanda arama yap
            doc_matches = []
            
            for chunk_index, chunk in enumerate(chunks):
                if not isinstance(chunk, str):
                    continue
                
                # Arama tipine göre farklı pattern kullan
                matches = perform_search_in_text(
                    chunk, query, search_type, case_sensitive
                )
                
                for match in matches:
                    # Context oluştur (highlight_context kadar karakter)
                    start_pos = match["start"]
                    end_pos = match["end"]
                    
                    context_start = max(0, start_pos - highlight_context)
                    context_end = min(len(chunk), end_pos + highlight_context)
                    
                    context = chunk[context_start:context_end]
                    
                    # Matched text'i highlight et
                    relative_start = start_pos - context_start
                    relative_end = end_pos - context_start
                    
                    highlighted_context = (
                        context[:relative_start] + 
                        "**" + context[relative_start:relative_end] + "**" + 
                        context[relative_end:]
                    )
                    
                    doc_matches.append({
                        "chunk_index": chunk_index,
                        "position": start_pos,
                        "matched_text": match["matched_text"],
                        "context": context,
                        "highlighted_context": highlighted_context,
                        "score": calculate_match_score(query, match["matched_text"], context)
                    })
            
            if doc_matches:
                # Matches'i score'a göre sırala
                doc_matches.sort(key=lambda x: x["score"], reverse=True)
                
                # Max results'a göre limit'le
                limited_matches = doc_matches[:max_results]
                
                search_results.append({
                    "document_id": doc_id,
                    "document_filename": filename,
                    "document_group": group_name,
                    "matches": limited_matches,
                    "total_matches": len(doc_matches),
                    "match_score": sum(m["score"] for m in limited_matches) / len(limited_matches) if limited_matches else 0
                })
        
        # Sonuçları relevance score'a göre sırala
        search_results.sort(key=lambda x: x["match_score"], reverse=True)
        
        return search_results[:max_results]
        
    except Exception as e:
        logging.error(f"Document search error: {str(e)}")
        return []

def perform_search_in_text(text: str, query: str, search_type: str, case_sensitive: bool) -> List[dict]:
    """Metin içinde arama gerçekleştir - Türkçe karakter desteği ile"""
    import re
    import unicodedata
    
    matches = []
    
    try:
        if search_type == "regex":
            # Regex arama
            flags = 0 if case_sensitive else re.IGNORECASE | re.UNICODE
            pattern = re.compile(query, flags)
            
            for match in pattern.finditer(text):
                matches.append({
                    "start": match.start(),
                    "end": match.end(),
                    "matched_text": match.group()
                })
        
        elif search_type == "exact":
            # Tam eşleşme arama
            search_text = text if case_sensitive else text.lower()
            search_query = query if case_sensitive else query.lower()
            
            start_pos = 0
            while True:
                pos = search_text.find(search_query, start_pos)
                if pos == -1:
                    break
                
                matches.append({
                    "start": pos,
                    "end": pos + len(query),
                    "matched_text": text[pos:pos + len(query)]
                })
                
                start_pos = pos + 1
        
        else:
            # Normal text arama (kelime kelime) - Türkçe karakter desteği ile
            query_words = query.split()
            search_text = text if case_sensitive else text.lower()
            
            for word in query_words:
                search_word = word if case_sensitive else word.lower()
                
                # Türkçe karakterler için özel word boundary pattern
                # \b yerine custom pattern kullan
                turkish_word_chars = r'[a-zA-ZçğıöşüâîûÇĞIİÖŞÜÂÎÛ0-9_]'
                non_word_chars = r'[^a-zA-ZçğıöşüâîûÇĞIİÖŞÜÂÎÛ0-9_]'
                
                # Word boundary pattern for Turkish
                pattern = f'(?<={non_word_chars}|^){re.escape(search_word)}(?={non_word_chars}|$)'
                flags = 0 if case_sensitive else re.IGNORECASE | re.UNICODE
                
                try:
                    for match in re.finditer(pattern, search_text):
                        matches.append({
                            "start": match.start(),
                            "end": match.end(),
                            "matched_text": text[match.start():match.end()]
                        })
                except re.error:
                    # Regex hatası varsa basit text search yap
                    logging.warning(f"Regex pattern error for word: {search_word}, falling back to simple search")
                    start_pos = 0
                    while True:
                        pos = search_text.find(search_word, start_pos)
                        if pos == -1:
                            break
                        
                        # Check if it's a whole word (basic check)
                        is_start_word = pos == 0 or not search_text[pos-1].isalnum()
                        is_end_word = pos + len(search_word) >= len(search_text) or not search_text[pos + len(search_word)].isalnum()
                        
                        if is_start_word and is_end_word:
                            matches.append({
                                "start": pos,
                                "end": pos + len(search_word),
                                "matched_text": text[pos:pos + len(search_word)]
                            })
                        
                        start_pos = pos + 1
        
        return matches
        
    except Exception as e:
        logging.error(f"Text search error: {str(e)}")
        # Fallback: simple case-insensitive find
        try:
            search_text = text if case_sensitive else text.lower()
            search_query = query if case_sensitive else query.lower()
            
            start_pos = 0
            while True:
                pos = search_text.find(search_query, start_pos)
                if pos == -1:
                    break
                
                matches.append({
                    "start": pos,
                    "end": pos + len(query),
                    "matched_text": text[pos:pos + len(query)]
                })
                
                start_pos = pos + 1
                
            return matches
        except:
            return []

def calculate_match_score(query: str, matched_text: str, context: str) -> float:
    """Match kalite skorunu hesapla"""
    try:
        score = 0.0
        
        # Base score - match length vs query length
        query_len = len(query.strip())
        match_len = len(matched_text.strip())
        
        if query_len > 0:
            score += (match_len / query_len) * 0.4
        
        # Exact match bonus
        if query.lower().strip() == matched_text.lower().strip():
            score += 0.3
        
        # Context relevance (more unique words in context = higher score)
        context_words = set(context.lower().split())
        query_words = set(query.lower().split())
        common_words = context_words.intersection(query_words)
        
        if len(query_words) > 0:
            score += (len(common_words) / len(query_words)) * 0.3
        
        # Normalize score to 0-1 range
        return min(1.0, max(0.0, score))
        
    except Exception:
        return 0.5  # Default medium score

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
                    
                    # Dosya uzantısına göre farklı parser kullan
                    file_extension = os.path.splitext(filename.lower())[1]
                    parsed_content = ""
                    paragraph_count = 0
                    
                    if file_extension == '.docx':
                        # DOCX için python-docx kullan
                        try:
                            from docx import Document as DocxDocument
                            docx_doc = DocxDocument(tmp_docx.name)
                            
                            for paragraph in docx_doc.paragraphs:
                                if paragraph.text.strip():
                                    text = paragraph.text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                                    p = Paragraph(text, normal_style)
                                    story.append(p)
                                    story.append(Spacer(1, 6))
                                    paragraph_count += 1
                                    
                        except Exception as docx_parse_error:
                            logging.error(f"DOCX parsing error: {str(docx_parse_error)}")
                            parsed_content = f"DOCX parsing hatası: {str(docx_parse_error)}"
                    
                    elif file_extension == '.doc':
                        # DOC için çoklu yöntem stratejisi
                        extracted_successfully = False
                        
                        try:
                            # DOC dosyasını geçici olarak kaydet
                            doc_tmp_path = tmp_docx.name.replace('.docx', '.doc')
                            os.rename(tmp_docx.name, doc_tmp_path)
                            
                            # Yöntem 1: textract ile dene
                            try:
                                import textract
                                logging.info("Trying textract for DOC processing...")
                                extracted_text = textract.process(doc_tmp_path)
                                if isinstance(extracted_text, bytes):
                                    extracted_text = extracted_text.decode('utf-8', errors='ignore')
                                
                                if extracted_text.strip():
                                    logging.info("Textract extraction successful")
                                    # Metni paragraflara böl
                                    paragraphs = extracted_text.split('\n')
                                    for para in paragraphs:
                                        if para.strip():
                                            text = para.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                                            p = Paragraph(text, normal_style)
                                            story.append(p)
                                            story.append(Spacer(1, 6))
                                            paragraph_count += 1
                                    extracted_successfully = True
                                        
                            except Exception as textract_error:
                                logging.error(f"Textract error: {str(textract_error)}")
                            
                            # Yöntem 2: antiword fallback (sadece textract başarısızsa)
                            if not extracted_successfully:
                                try:
                                    import subprocess
                                    logging.info("Trying antiword for DOC processing...")
                                    result = subprocess.run(['antiword', doc_tmp_path], 
                                                          capture_output=True, text=True, timeout=30)
                                    if result.returncode == 0 and result.stdout.strip():
                                        logging.info("Antiword extraction successful")
                                        extracted_text = result.stdout
                                        paragraphs = extracted_text.split('\n')
                                        for para in paragraphs:
                                            if para.strip():
                                                text = para.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                                                p = Paragraph(text, normal_style)
                                                story.append(p)
                                                story.append(Spacer(1, 6))
                                                paragraph_count += 1
                                        extracted_successfully = True
                                    else:
                                        logging.error(f"Antiword failed: {result.stderr}")
                                except Exception as antiword_error:
                                    logging.error(f"Antiword error: {str(antiword_error)}")
                            
                            # Yöntem 3: Binary content analizi (son çare)
                            if not extracted_successfully:
                                logging.info("Trying binary content analysis...")
                                try:
                                    # DOC dosyasının binary içeriğini oku
                                    with open(doc_tmp_path, 'rb') as f:
                                        binary_content = f.read()
                                    
                                    # Basit text extraction - DOC files have readable text mixed with binary
                                    # Try to extract readable ASCII/UTF-8 text
                                    text_content = ""
                                    for byte_chunk in [binary_content[i:i+1000] for i in range(0, len(binary_content), 1000)]:
                                        try:
                                            # ASCII text'i çıkarmaya çalış
                                            chunk_text = ""
                                            for byte in byte_chunk:
                                                if 32 <= byte <= 126 or byte in [9, 10, 13]:  # Printable ASCII + tab/newline/carriage return
                                                    chunk_text += chr(byte)
                                                else:
                                                    if chunk_text and len(chunk_text) > 2:
                                                        text_content += chunk_text + " "
                                                    chunk_text = ""
                                            
                                            if chunk_text and len(chunk_text) > 2:
                                                text_content += chunk_text + " "
                                                
                                        except Exception:
                                            continue
                                    
                                    # Temizle ve filtrele
                                    if text_content.strip():
                                        # Çok kısa kelimeler ve binary kalıntıları filtrele
                                        words = text_content.split()
                                        clean_words = []
                                        for word in words:
                                            # Türkçe karakterli veya uzun İngilizce kelimeler kabul et
                                            if (len(word) >= 3 and 
                                                (any(c in word.lower() for c in 'çğıöşüâîû') or  # Türkçe karakterler
                                                 word.isalpha())):  # Sadece harf içeren kelimeler
                                                clean_words.append(word)
                                        
                                        if len(clean_words) >= 10:  # En az 10 anlamlı kelime varsa
                                            extracted_text = " ".join(clean_words)
                                            logging.info(f"Binary extraction found {len(clean_words)} words")
                                            
                                            # Metni paragraflara böl (yaklaşık 100 kelimelik bloklar)
                                            word_chunks = [clean_words[i:i+100] for i in range(0, len(clean_words), 100)]
                                            for chunk in word_chunks:
                                                if chunk:
                                                    text = " ".join(chunk)
                                                    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                                                    p = Paragraph(text, normal_style)
                                                    story.append(p)
                                                    story.append(Spacer(1, 6))
                                                    paragraph_count += 1
                                            
                                            extracted_successfully = True
                                            
                                except Exception as binary_error:
                                    logging.error(f"Binary analysis error: {str(binary_error)}")
                            
                            # Geçici DOC dosyasını sil
                            try:
                                os.unlink(doc_tmp_path)
                            except:
                                pass
                            
                            # Hiçbir yöntem başarılı olmazsa
                            if not extracted_successfully:
                                parsed_content = ("DOC dosyası işlenemedi. Textract, antiword ve binary analiz yöntemleri başarısız oldu. "
                                                "Doküman mevcut ancak içeriği çıkarılamadı.")
                                
                        except Exception as doc_error:
                            logging.error(f"DOC processing error: {str(doc_error)}")
                            parsed_content = f"DOC işleme hatası: {str(doc_error)}"
                    
                    else:
                        # Desteklenmeyen format
                        parsed_content = f"Desteklenmeyen dosya formatı: {file_extension}"
                    
                    # Eğer hiçbir içerik parse edilemezse
                    if paragraph_count == 0:
                        if parsed_content:
                            story.append(Paragraph(parsed_content, normal_style))
                        else:
                            story.append(Paragraph("Doküman içeriği okumaya çalışıldı ancak metin çıkarılamadı.", normal_style))
                            story.append(Spacer(1, 12))
                            story.append(Paragraph("Bu durumda doküman mevcut ancak içeriği PDF formatında görüntülenemiyor.", normal_style))
                    
                    # Geçici dosyayı sil
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

# Authentication Endpoints
@api_router.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """User login with username and password"""
    try:
        # Find user in database
        user = await db.users.find_one({"username": user_credentials.username})
        
        if not user or not verify_password(user_credentials.password, user["password_hash"]):
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.get("is_active", False):
            raise HTTPException(status_code=400, detail="Inactive user")
        
        # Update last login
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        # Create access token
        access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        access_token = create_access_token(
            data={"sub": user["username"], "role": user["role"]}, 
            expires_delta=access_token_expires
        )
        
        user_info = UserInfo(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"],
            last_login=user.get("last_login")
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,  # seconds
            user_info=user_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@api_router.post("/auth/create-user", response_model=UserInfo)
async def create_user(user_data: UserCreate, current_user: dict = Depends(require_admin)):
    """Create new user (admin only)"""
    try:
        # Check if username or email already exists
        existing_username = await db.users.find_one({"username": user_data.username})
        if existing_username:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        existing_email = await db.users.find_one({"email": user_data.email})
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")
        
        # Validate role
        if user_data.role not in ["admin", "editor", "viewer"]:
            raise HTTPException(status_code=400, detail="Invalid role. Must be admin, editor, or viewer")
        
        # Create new user
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
            password_hash=get_password_hash(user_data.password),
            created_by=current_user["id"]
        )
        
        # Insert into database
        await db.users.insert_one(new_user.dict())
        
        return UserInfo(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            full_name=new_user.full_name,
            role=new_user.role,
            is_active=new_user.is_active,
            created_at=new_user.created_at,
            last_login=new_user.last_login
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"User creation error: {str(e)}")

@api_router.get("/auth/me", response_model=UserInfo)
async def get_current_user_info(current_user: dict = Depends(get_current_active_user)):
    """Get current user information"""
    return UserInfo(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        is_active=current_user["is_active"],
        created_at=current_user["created_at"],
        last_login=current_user.get("last_login")
    )

@api_router.get("/auth/users")
async def get_all_users(current_user: dict = Depends(require_admin)):
    """Get all users (admin only)"""
    try:
        users = await db.users.find({}, {"password_hash": 0, "_id": 0}).to_list(None)
        return {"users": users, "total_count": len(users)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")

@api_router.post("/auth/password-reset-request")
async def request_password_reset(request: PasswordResetRequest):
    """Request password reset (send reset token to email)"""
    try:
        user = await db.users.find_one({"email": request.email})
        if not user:
            # Don't reveal if email exists for security
            return {"message": "If the email exists, a reset token has been sent"}
        
        # Create reset token (expires in 1 hour)
        reset_token = create_access_token(
            data={"sub": user["username"], "type": "password_reset"},
            expires_delta=timedelta(hours=1)
        )
        
        # In production, send email with reset token
        # For now, just log it (in production, remove this)
        logging.info(f"Password reset token for {request.email}: {reset_token}")
        
        return {"message": "If the email exists, a reset token has been sent"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Password reset request error: {str(e)}")

@api_router.post("/auth/password-reset")
async def reset_password(reset_data: PasswordReset):
    """Reset password with token"""
    try:
        # Verify reset token
        payload = jwt.decode(reset_data.reset_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        token_type = payload.get("type")
        
        if not username or token_type != "password_reset":
            raise HTTPException(status_code=400, detail="Invalid reset token")
        
        # Update password
        new_password_hash = get_password_hash(reset_data.new_password)
        result = await db.users.update_one(
            {"username": username},
            {"$set": {"password_hash": new_password_hash}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": "Password reset successfully"}
        
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Password reset error: {str(e)}")

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
async def get_groups(current_user: dict = Depends(get_current_active_user)):
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
async def create_group(request: GroupCreateRequest, current_user: dict = Depends(require_editor_or_admin)):
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
async def update_group(group_id: str, request: GroupCreateRequest, current_user: dict = Depends(require_editor_or_admin)):
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
async def delete_group(group_id: str, move_documents: bool = False, current_user: dict = Depends(require_editor_or_admin)):
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
async def move_documents(request: DocumentMoveRequest, current_user: dict = Depends(require_editor_or_admin)):
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
    group_id: Optional[str] = None,
    current_user: dict = Depends(require_editor_or_admin)
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
async def ask_question(request: QuestionRequest, current_user: dict = Depends(get_current_active_user)):
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
        
        # Content handling - veritabanından gelen content çeşitli formatlarda olabilir
        try:
            if isinstance(file_content, str):
                # String ise base64 decode edilmiş olabilir veya binary olabilir
                try:
                    # Base64 decode dene
                    file_content = base64.b64decode(file_content)
                except:
                    # Base64 değilse UTF-8 encode et
                    file_content = file_content.encode('utf-8')
            elif isinstance(file_content, dict) and 'data' in file_content:
                # MongoDB'dan gelen binary data format
                file_content = file_content['data']
        except Exception as content_error:
            logging.error(f"Content conversion error: {str(content_error)}")
            # Content convert edilemezse hata PDF'i oluştur
            error_msg = f"Doküman içeriği işlenemiyor: {str(content_error)}"
            pdf_content = create_error_pdf(filename, error_msg)
            
            response = Response(
                content=pdf_content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename=\"{os.path.splitext(filename)[0]}_error.pdf\"",
                    "Content-Length": str(len(pdf_content)),
                    "X-PDF-Pages": "1",
                    "X-Original-Filename": filename,
                    "X-Error": "Content processing error"
                }
            )
            return response
        
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

@api_router.get("/documents/{document_id}/download-original")
async def download_original_document(document_id: str):
    """Orijinal dokümanı (Word formatında) download et"""
    try:
        # Dokümanı bul
        document = await db.documents.find_one({"id": document_id})
        
        if not document:
            raise HTTPException(status_code=404, detail="Doküman bulunamadı")
        
        filename = document.get("filename", "document")
        file_content = document.get("content", b"")
        
        if not file_content:
            raise HTTPException(status_code=404, detail="Doküman içeriği bulunamadı")
        
        # Content handling - veritabanından gelen content çeşitli formatlarda olabilir
        try:
            if isinstance(file_content, str):
                # String ise base64 decode edilmiş olabilir
                try:
                    file_content = base64.b64decode(file_content)
                except:
                    file_content = file_content.encode('utf-8')
            elif isinstance(file_content, dict) and 'data' in file_content:
                # MongoDB'dan gelen binary data format
                file_content = file_content['data']
        except Exception as content_error:
            logging.error(f"Content conversion error: {str(content_error)}")
            raise HTTPException(status_code=500, detail=f"Doküman içeriği işlenemiyor: {str(content_error)}")
        
        # Dosya uzantısına göre MIME type belirle
        file_extension = os.path.splitext(filename.lower())[1]
        
        if file_extension == '.docx':
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif file_extension == '.doc':
            mime_type = "application/msword"
        else:
            mime_type = "application/octet-stream"
        
        # Orijinal dosyayı download olarak serve et
        response = Response(
            content=file_content,
            media_type=mime_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"",
                "Content-Length": str(len(file_content)),
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Orijinal doküman download edilirken hata: {str(e)}")

@api_router.post("/search-in-documents")
async def search_documents(request: DocumentSearchRequest):
    """Dokümanlar içinde metin arama"""
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Arama sorgusu boş olamaz")
        
        # Arama gerçekleştir
        search_results = await search_in_documents(
            query=request.query,
            document_ids=request.document_ids if request.document_ids else None,
            group_ids=request.group_ids if request.group_ids else None,
            search_type=request.search_type,
            case_sensitive=request.case_sensitive,
            max_results=request.max_results,
            highlight_context=request.highlight_context
        )
        
        # İstatistikleri hesapla
        total_documents_searched = len(search_results)
        total_matches = sum(result["total_matches"] for result in search_results)
        
        return {
            "query": request.query,
            "search_type": request.search_type,
            "case_sensitive": request.case_sensitive,
            "results": search_results,
            "statistics": {
                "total_documents_searched": total_documents_searched,
                "total_matches": total_matches,
                "documents_with_matches": len([r for r in search_results if r["total_matches"] > 0]),
                "average_match_score": sum(r["match_score"] for r in search_results) / len(search_results) if search_results else 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Doküman aramasında hata: {str(e)}")

@api_router.get("/search-suggestions")
async def get_search_suggestions(q: str, limit: int = 10):
    """Arama önerileri - önceki aramalar ve popüler terimler"""
    try:
        if not q or len(q.strip()) < 2:
            return {
                "suggestions": [],
                "query": q,
                "count": 0
            }
        
        suggestions = []
        
        # Doküman içeriklerinden yaygın terimleri çıkar
        all_docs = await db.documents.find({}).to_list(100)
        
        # Term frequency analysis
        term_frequency = {}
        query_lower = q.lower()
        
        for doc in all_docs:
            chunks = doc.get("chunks", [])
            for chunk in chunks:
                if isinstance(chunk, str):
                    words = chunk.lower().split()
                    for word in words:
                        # Query ile başlayan veya içeren kelimeleri bul
                        if (len(word) >= 3 and 
                            (word.startswith(query_lower) or query_lower in word) and
                            word != query_lower):
                            
                            if word not in term_frequency:
                                term_frequency[word] = 0
                            term_frequency[word] += 1
        
        # En sık kullanılan terimleri al
        sorted_terms = sorted(term_frequency.items(), key=lambda x: x[1], reverse=True)
        
        for term, frequency in sorted_terms[:limit]:
            suggestions.append({
                "text": term,
                "type": "term",
                "frequency": frequency,
                "icon": "🔍"
            })
        
        return {
            "suggestions": suggestions,
            "query": q,
            "count": len(suggestions)
        }
        
    except Exception as e:
        logging.error(f"Search suggestions error: {str(e)}")
        return {
            "suggestions": [],
            "query": q,
            "count": 0
        }

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
async def delete_document(document_id: str, background_tasks: BackgroundTasks, current_user: dict = Depends(require_editor_or_admin)):
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

# AI Response Rating Endpoints
@api_router.post("/ratings")
async def add_rating(rating_request: RatingRequest, current_user: dict = Depends(get_current_active_user)):
    """Add rating and feedback for an AI response"""
    try:
        # Verify chat session exists
        chat_session = await db.chat_sessions.find_one({"id": rating_request.chat_session_id})
        if not chat_session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Check if user already rated this session
        existing_rating = await db.response_ratings.find_one({
            "chat_session_id": rating_request.chat_session_id,
            "user_id": current_user["id"]
        })
        
        if existing_rating:
            # Update existing rating
            await db.response_ratings.update_one(
                {"id": existing_rating["id"]},
                {
                    "$set": {
                        "rating": rating_request.rating,
                        "feedback": rating_request.feedback,
                        "created_at": datetime.utcnow()
                    }
                }
            )
            return {"message": "Rating updated successfully", "rating_id": existing_rating["id"]}
        else:
            # Create new rating
            new_rating = ResponseRating(
                session_id=rating_request.session_id,
                chat_session_id=rating_request.chat_session_id,
                rating=rating_request.rating,
                feedback=rating_request.feedback,
                user_id=current_user["id"]
            )
            
            await db.response_ratings.insert_one(new_rating.dict())
            return {"message": "Rating added successfully", "rating_id": new_rating.id}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rating error: {str(e)}")

@api_router.get("/ratings/stats", response_model=RatingStats)
async def get_rating_stats(current_user: dict = Depends(require_admin)):
    """Get rating statistics (admin only)"""
    try:
        # Get all ratings
        ratings = await db.response_ratings.find({}).to_list(None)
        
        if not ratings:
            return RatingStats(
                total_ratings=0,
                average_rating=0.0,
                rating_distribution={1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                recent_feedback=[]
            )
        
        # Calculate statistics
        total_ratings = len(ratings)
        total_score = sum(r["rating"] for r in ratings)
        average_rating = total_score / total_ratings if total_ratings > 0 else 0.0
        
        # Rating distribution
        rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for rating in ratings:
            rating_distribution[rating["rating"]] += 1
        
        # Recent feedback (last 10 with feedback)
        recent_feedback = []
        feedback_ratings = [r for r in ratings if r.get("feedback")]
        feedback_ratings.sort(key=lambda x: x["created_at"], reverse=True)
        
        for rating in feedback_ratings[:10]:
            # Get user info
            user = await db.users.find_one({"id": rating["user_id"]})
            # Get chat session info
            chat_session = await db.chat_sessions.find_one({"id": rating["chat_session_id"]})
            
            recent_feedback.append({
                "rating": rating["rating"],
                "feedback": rating["feedback"],
                "created_at": rating["created_at"],
                "user_name": user["full_name"] if user else "Unknown User",
                "question_preview": chat_session["question"][:100] + "..." if chat_session and len(chat_session["question"]) > 100 else chat_session["question"] if chat_session else "Unknown Question"
            })
        
        return RatingStats(
            total_ratings=total_ratings,
            average_rating=round(average_rating, 2),
            rating_distribution=rating_distribution,
            recent_feedback=recent_feedback
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rating stats error: {str(e)}")

@api_router.get("/ratings/low-rated")
async def get_low_rated_responses(current_user: dict = Depends(require_admin), threshold: int = 2):
    """Get low-rated responses for analysis (admin only)"""
    try:
        # Get ratings below threshold
        low_ratings = await db.response_ratings.find({"rating": {"$lte": threshold}}).to_list(None)
        
        low_rated_responses = []
        for rating in low_ratings:
            # Get chat session details
            chat_session = await db.chat_sessions.find_one({"id": rating["chat_session_id"]})
            if chat_session:
                # Get user info
                user = await db.users.find_one({"id": rating["user_id"]})
                
                low_rated_responses.append({
                    "rating_id": rating["id"],
                    "rating": rating["rating"],
                    "feedback": rating.get("feedback"),
                    "created_at": rating["created_at"],
                    "user_name": user["full_name"] if user else "Unknown User",
                    "question": chat_session["question"],
                    "answer_preview": chat_session["answer"][:200] + "..." if len(chat_session["answer"]) > 200 else chat_session["answer"],
                    "source_documents": chat_session["source_documents"]
                })
        
        # Sort by rating (lowest first) then by date (newest first)
        low_rated_responses.sort(key=lambda x: (x["rating"], x["created_at"]), reverse=True)
        
        return {
            "low_rated_responses": low_rated_responses,
            "total_count": len(low_rated_responses),
            "threshold": threshold
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Low rated responses error: {str(e)}")

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
    """Uygulama başlangıcında FAISS indeksini yükle ve admin kullanıcıyı oluştur"""
    try:
        await update_faiss_index()
        
        # İlk admin kullanıcıyı oluştur (eğer yoksa)
        admin_exists = await db.users.find_one({"role": "admin"})
        if not admin_exists:
            admin_user = User(
                username="admin",
                email="admin@kpa.com",
                full_name="System Administrator",
                role="admin",
                password_hash=get_password_hash("admin123")
            )
            await db.users.insert_one(admin_user.dict())
            logger.info("İlk admin kullanıcı oluşturuldu: username=admin, password=admin123")
        
        logger.info("Kurumsal Prosedür Asistanı başlatıldı")
    except Exception as e:
        logger.error(f"Başlangıç hatası: {str(e)}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()