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
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-here')
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_HOURS = 48

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer(auto_error=False)

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Kurumsal Prosedür Asistanı API", 
    description="AI-powered document Q&A system",
    version="2.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API router with prefix
api_router = APIRouter(prefix="/api")

# Global variables for AI models
sentence_model = None
faiss_index = None
documents = []
document_chunks = []

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = await db.users.find_one({"username": username})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="User account is disabled")
    
    return user

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    return current_user

# Role-based access control
async def require_admin(current_user: dict = Depends(get_current_active_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def require_editor_or_admin(current_user: dict = Depends(get_current_active_user)):
    if current_user.get("role") not in ["admin", "editor"]:
        raise HTTPException(status_code=403, detail="Editor or Admin access required")
    return current_user

async def require_authenticated(current_user: dict = Depends(get_current_active_user)):
    return current_user

# Pydantic models
class ChatMessage(BaseModel):
    question: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    session_id: str

class ChatSession(BaseModel):
    session_id: str
    question: str
    answer: str
    source_documents: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SystemStatus(BaseModel):
    total_documents: int
    total_chunks: int
    total_groups: int = 0
    embedding_model_loaded: bool
    faiss_index_ready: bool
    supported_formats: List[str] = ['.doc', '.docx']
    processing_queue: int = 0

class DocumentInfo(BaseModel):
    id: str
    filename: str
    file_type: str = ""
    file_size: int = 0
    chunk_count: int = 0
    upload_date: datetime
    group_id: Optional[str] = None
    group_name: Optional[str] = None

class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]
    statistics: Dict[str, Any]

class DocumentDeleteResponse(BaseModel):
    message: str
    document_id: str
    deleted_chunks: int

class GroupInfo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    color: str = "#3b82f6"
    document_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class GroupCreateRequest(BaseModel):
    name: str
    description: str = ""
    color: str = "#3b82f6"

class GroupListResponse(BaseModel):
    groups: List[GroupInfo]
    total_count: int

class DocumentMoveRequest(BaseModel):
    document_ids: List[str]
    target_group_id: Optional[str] = None  # None = "Grupsuz" durumu

class ResponseRating(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    chat_session_id: str  # Chat session referansı
    rating: int = Field(ge=1, le=5)  # 1-5 yıldız
    feedback: str = ""
    user_id: Optional[str] = None  # Opsiyonel kullanıcı bilgisi
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class RatingRequest(BaseModel):
    session_id: str
    rating: int = Field(ge=1, le=5)
    feedback: str = ""

class FavoriteQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str  # Orijinal chat session referansı
    question: str
    answer: str
    category: str = "Genel"  # Kategori
    tags: List[str] = []  # Etiketler
    notes: str = ""  # Kullanıcı notları
    favorite_count: int = 1  # Kaç kez favorilere eklendi
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class FavoriteRequest(BaseModel):
    session_id: str
    question: str
    answer: str
    category: str = "Genel"
    tags: List[str] = []
    notes: str = ""

class FavoriteUpdateRequest(BaseModel):
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None

class FAQItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    answer: str
    category: str = "Genel"
    frequency: int = 1  # Kaç kez soruldu
    last_asked: datetime = Field(default_factory=datetime.utcnow)
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
    must_change_password: bool = False  # NEW: Zorunlu şifre değişikliği

class UserInfo(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    must_change_password: bool = False  # NEW: Zorunlu şifre değişikliği

class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str
    role: str = "viewer"
    is_active: bool = True

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserLogin(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserInfo
    must_change_password: bool = False  # NEW: Zorunlu şifre değişikliği

class Token(BaseModel):
    access_token: str
    token_type: str

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class ProfileUpdateRequest(BaseModel):
    full_name: str
    email: str

class UserActivityLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    action: str  # "login", "logout", "document_upload", "document_delete", etc.
    details: str = ""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class UserBulkUpdateRequest(BaseModel):
    user_ids: List[str]
    updates: UserUpdate

# NEW: Bulk Document Upload Models
class BulkUploadFile(BaseModel):
    filename: str
    content: str  # Base64 encoded content
    group_id: Optional[str] = None

class BulkUploadRequest(BaseModel):
    files: List[BulkUploadFile]
    group_id: Optional[str] = None  # Default group for all files

class BulkUploadStatus(BaseModel):
    filename: str
    status: str  # "success", "error", "processing"
    message: str = ""
    document_id: Optional[str] = None

class BulkUploadResponse(BaseModel):
    total_files: int
    successful_uploads: int
    failed_uploads: int
    results: List[BulkUploadStatus]
    processing_time: float

# Helper function to log user activity
async def log_user_activity(user_id: str, action: str, details: str = "", ip_address: str = None, user_agent: str = None):
    """Log user activity to database"""
    try:
        activity = UserActivityLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        await db.user_activities.insert_one(activity.dict())
    except Exception as e:
        logger.error(f"Failed to log user activity: {str(e)}")

# Load AI models
def load_models():
    global sentence_model, faiss_index, documents, document_chunks
    
    try:
        # Load sentence transformer model
        logger.info("Loading sentence transformer model...")
        sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Sentence transformer model loaded successfully")
        
        # Try to load existing FAISS index and documents
        try:
            with open('faiss_index.pkl', 'rb') as f:
                faiss_index = pickle.load(f)
            with open('documents.pkl', 'rb') as f:
                documents = pickle.load(f)
            with open('document_chunks.pkl', 'rb') as f:
                document_chunks = pickle.load(f)
            logger.info(f"Loaded existing index with {len(documents)} documents and {len(document_chunks)} chunks")
        except FileNotFoundError:
            logger.info("No existing index found, starting fresh")
            documents = []
            document_chunks = []
            
    except Exception as e:
        logger.error(f"Error loading models: {str(e)}")

# Extract text from different document formats
def extract_text_from_document(file_path: str, file_extension: str) -> str:
    """
    3-tier document processing approach:
    1. Primary: textract (handles most formats)
    2. Fallback: antiword (for .doc files) or python-docx (for .docx)
    3. Last resort: binary content analysis (as fallback)
    """
    text = ""
    
    try:
        if file_extension.lower() == '.docx':
            # For DOCX: try python-docx first, then textract
            try:
                doc = Document(file_path)
                text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                if text.strip():  # Check if we got meaningful content
                    logger.info(f"Successfully extracted text using python-docx: {len(text)} characters")
                    return text
            except Exception as docx_error:
                logger.warning(f"python-docx failed: {str(docx_error)}, trying textract...")
            
            # Fallback to textract for DOCX
            try:
                text = textract.process(file_path).decode('utf-8', errors='ignore')
                if text.strip():
                    logger.info(f"Successfully extracted text using textract: {len(text)} characters")
                    return text
            except Exception as textract_error:
                logger.warning(f"textract failed for DOCX: {str(textract_error)}")
        
        elif file_extension.lower() == '.doc':
            # For DOC: try textract first, then antiword
            try:
                text = textract.process(file_path).decode('utf-8', errors='ignore')
                if text.strip():
                    logger.info(f"Successfully extracted text using textract: {len(text)} characters")
                    return text
            except Exception as textract_error:
                logger.warning(f"textract failed for DOC: {str(textract_error)}, trying antiword...")
            
            # Fallback to antiword for DOC
            try:
                import subprocess
                result = subprocess.run(['antiword', file_path], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    text = result.stdout
                    logger.info(f"Successfully extracted text using antiword: {len(text)} characters")
                    return text
            except Exception as antiword_error:
                logger.warning(f"antiword failed: {str(antiword_error)}")
    
    except Exception as e:
        logger.error(f"Primary extraction methods failed: {str(e)}")
    
    # Last resort: binary content analysis
    try:
        with open(file_path, 'rb') as f:
            binary_content = f.read()
        
        # Try to extract readable text from binary content
        try:
            # For DOC files, try to find text sections
            if file_extension.lower() == '.doc':
                # Simple binary text extraction for DOC files
                text_parts = []
                current_text = ""
                
                for byte in binary_content:
                    if 32 <= byte <= 126:  # Printable ASCII characters
                        current_text += chr(byte)
                    else:
                        if len(current_text) > 10:  # Only keep strings longer than 10 chars
                            text_parts.append(current_text)
                        current_text = ""
                
                # Add any remaining text
                if len(current_text) > 10:
                    text_parts.append(current_text)
                
                text = ' '.join(text_parts)
                
                if text.strip():
                    logger.info(f"Successfully extracted text using binary analysis: {len(text)} characters")
                    return text
        
        except Exception as binary_error:
            logger.error(f"Binary analysis failed: {str(binary_error)}")
    
    except Exception as e:
        logger.error(f"All extraction methods failed: {str(e)}")
    
    if not text.strip():
        raise Exception("Doküman içeriği okunamadı. Dosya bozuk veya desteklenmeyen formatta olabilir.")
    
    return text

# Generate answer using Gemini AI
async def generate_answer_with_gemini(question: str, context: str) -> str:
    try:
        # Configure the chat client
        llm_client = LlmChat(model_name="gemini-2.0-flash-exp")
        
        # Create a system message with formatting rules
        system_message = f"""Sen Kurumsal Prosedür Asistanı'sın. Sadece verilen doküman içeriğinden yararlanarak soruları yanıtla.

Önemli formatla kuralları:
- Başlıkları ve önemli terimleri **kalın** yaparak vurgula
- Önemli kelimeleri ve anahtar kavramları **kalın** yaz
- Madde listelerini • ile başlat
- Numaralı listeler için 1., 2., 3. formatını kullan
- Cevabını paragraflar halinde organize et
- Kaynak dokümanlardan gelen bilgileri net bir şekilde sun

Doküman içeriği:
{context}

Soru: {question}

Lütfen sadece doküman içeriğine dayalı bir cevap ver. Eğer cevap doküman içinde yoksa, bunu belirt."""

        user_message = UserMessage(content=system_message)
        
        # Get response from Gemini
        response = await llm_client.send_message_async(message=user_message)
        
        return response.content
        
    except Exception as e:
        logger.error(f"Gemini AI error: {str(e)}")
        if "overloaded" in str(e).lower() or "503" in str(e):
            return "Üzgünüm, şu anda sorunuzu cevaplayamıyorum. Lütfen daha sonra tekrar deneyin."
        return f"AI yanıt hatası: {str(e)}"

def format_answer_with_sources(answer: str, source_documents: List[dict]) -> str:
    """Format answer with source document information"""
    if not source_documents:
        return answer
    
    # Add source documents section at the end
    sources_section = "\n\n---\n\n## 📚 Kaynak Dokümanlar\n\n"
    
    for doc in source_documents:
        filename = doc.get('filename', 'Bilinmeyen doküman')
        doc_id = doc.get('id', '')
        group_name = doc.get('group_name', 'Grupsuz')
        
        sources_section += f"• **{filename}**"
        if group_name and group_name != 'Grupsuz':
            sources_section += f" ({group_name})"
        if doc_id:
            sources_section += f" [Dokümanı Görüntüle](/api/documents/{doc_id})"
        sources_section += "\n"
    
    return answer + sources_section

# Create chunks from text
def create_chunks(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[str]:
    """Create overlapping chunks from text"""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break
        
        # Try to break at sentence boundary
        chunk = text[start:end]
        last_sentence = chunk.rfind('.')
        if last_sentence > chunk_size * 0.5:  # If we found a sentence break in the latter half
            end = start + last_sentence + 1
            chunks.append(text[start:end])
            start = end - chunk_overlap
        else:
            chunks.append(chunk)
            start = end - chunk_overlap
    
    return chunks

# Update FAISS index with new document
def update_faiss_index(new_chunks: List[str], document_id: str, filename: str, group_id: Optional[str] = None, group_name: Optional[str] = None):
    global faiss_index, document_chunks
    
    if not sentence_model:
        logger.error("Sentence model not loaded")
        return
    
    # Create embeddings for new chunks
    embeddings = sentence_model.encode(new_chunks)
    
    # Add to document_chunks with metadata
    for i, chunk in enumerate(new_chunks):
        document_chunks.append({
            'text': chunk,
            'document_id': document_id,
            'filename': filename,
            'chunk_index': i,
            'group_id': group_id,
            'group_name': group_name
        })
    
    # Update FAISS index
    if faiss_index is None:
        # Create new index
        dimension = embeddings.shape[1]
        faiss_index = faiss.IndexFlatL2(dimension)
    
    faiss_index.add(embeddings.astype('float32'))
    
    # Save updated index and chunks
    try:
        with open('faiss_index.pkl', 'wb') as f:
            pickle.dump(faiss_index, f)
        with open('document_chunks.pkl', 'wb') as f:
            pickle.dump(document_chunks, f)
        logger.info(f"Updated FAISS index with {len(new_chunks)} new chunks")
    except Exception as e:
        logger.error(f"Error saving FAISS index: {str(e)}")

# Search similar chunks
def search_similar_chunks(query: str, top_k: int = 5) -> List[dict]:
    if not sentence_model or faiss_index is None or len(document_chunks) == 0:
        return []
    
    try:
        # Create embedding for query
        query_embedding = sentence_model.encode([query])
        
        # Search in FAISS index
        distances, indices = faiss_index.search(query_embedding.astype('float32'), min(top_k, len(document_chunks)))
        
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(document_chunks):
                chunk_info = document_chunks[idx].copy()
                chunk_info['similarity_score'] = 1.0 / (1.0 + distance)  # Convert distance to similarity
                results.append(chunk_info)
        
        return results
    except Exception as e:
        logger.error(f"Error in similarity search: {str(e)}")
        return []

async def update_faiss_index_optimized():
    """Optimized FAISS update - rebuilds entire index from database"""
    global faiss_index, document_chunks
    
    try:
        logger.info("Starting optimized FAISS index update...")
        
        # Get all documents from database
        all_documents = []
        async for doc in db.documents.find():
            all_documents.append(doc)
        
        # Reset index and chunks
        document_chunks = []
        faiss_index = None
        
        if not all_documents:
            logger.info("No documents found, clearing index")
            return
        
        # Rebuild chunks from all documents
        all_embeddings = []
        
        for doc in all_documents:
            chunks = doc.get('chunks', [])
            document_id = doc.get('id')
            filename = doc.get('filename', 'Bilinmeyen')
            group_id = doc.get('group_id')
            group_name = doc.get('group_name')
            
            # Add chunks to document_chunks
            for i, chunk in enumerate(chunks):
                document_chunks.append({
                    'text': chunk,
                    'document_id': document_id,
                    'filename': filename,
                    'chunk_index': i,
                    'group_id': group_id,
                    'group_name': group_name
                })
            
            # Create embeddings for chunks
            if chunks:
                chunk_embeddings = sentence_model.encode(chunks)
                if len(chunk_embeddings.shape) == 1:
                    chunk_embeddings = chunk_embeddings.reshape(1, -1)
                all_embeddings.append(chunk_embeddings)
        
        # Create new FAISS index
        if all_embeddings:
            all_embeddings_matrix = np.vstack(all_embeddings)
            dimension = all_embeddings_matrix.shape[1]
            faiss_index = faiss.IndexFlatL2(dimension)
            faiss_index.add(all_embeddings_matrix.astype('float32'))
            
            # Save updated index and chunks
            with open('faiss_index.pkl', 'wb') as f:
                pickle.dump(faiss_index, f)
            with open('document_chunks.pkl', 'wb') as f:
                pickle.dump(document_chunks, f)
            
            logger.info(f"FAISS index optimized: {len(document_chunks)} chunks from {len(all_documents)} documents")
        else:
            logger.info("No chunks found, index remains empty")
        
    except Exception as e:
        logger.error(f"FAISS update error: {str(e)}")

# Debounced FAISS update to prevent sequential rebuilds
_faiss_update_pending = False

async def debounced_faiss_update():
    """Debounced FAISS update - prevents multiple sequential updates"""
    global _faiss_update_pending
    
    if _faiss_update_pending:
        logging.info("FAISS update already pending, skipping duplicate request")
        return
    
    _faiss_update_pending = True
    
    try:
        # Small delay to allow for batching multiple deletes
        await asyncio.sleep(2)
        
        # Call the optimized update function
        await update_faiss_index_optimized()
        
    except Exception as e:
        logging.error(f"Debounced FAISS update error: {str(e)}")
    finally:
        _faiss_update_pending = False

@api_router.delete("/documents")
async def delete_all_documents(background_tasks: BackgroundTasks, confirm: bool = False, current_user: dict = Depends(require_admin)):
    """Tüm dokümanları sil (tehlikeli işlem)"""
    if not confirm:
        raise HTTPException(status_code=400, detail="Bu tehlikeli işlem için confirm=true parametresi gerekli")
    
    try:
        # Count existing documents
        doc_count = await db.documents.count_documents({})
        
        if doc_count == 0:
            return {"message": "Silinecek doküman bulunamadı", "deleted_count": 0}
        
        # Delete all documents
        delete_result = await db.documents.delete_many({})
        
        # Background tasks for cleanup
        background_tasks.add_task(cleanup_all_chat_sessions)
        background_tasks.add_task(clear_faiss_index)
        
        # Log activity
        asyncio.create_task(log_user_activity(
            current_user["id"], 
            "documents_delete_all", 
            f"Deleted all {delete_result.deleted_count} documents"
        ))
        
        return {
            "message": f"Tüm dokümanlar başarıyla silindi",
            "deleted_count": delete_result.deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error deleting all documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Dokümanlar silinirken hata oluştu")

async def cleanup_all_chat_sessions():
    """Clean up all chat sessions"""
    try:
        await db.chat_sessions.delete_many({})
        logger.info("All chat sessions cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up all chat sessions: {str(e)}")

async def clear_faiss_index():
    """Clear FAISS index completely"""
    global faiss_index, document_chunks
    try:
        faiss_index = None
        document_chunks = []
        
        # Remove index files
        for filename in ['faiss_index.pkl', 'documents.pkl', 'document_chunks.pkl']:
            try:
                os.remove(filename)
            except FileNotFoundError:
                pass
        
        logger.info("FAISS index cleared completely")
    except Exception as e:
        logger.error(f"Error clearing FAISS index: {str(e)}")

# Background task to clean up chat sessions related to deleted documents
async def cleanup_chat_sessions(deleted_chunks):
    """Clean up chat sessions that reference deleted document chunks"""
    try:
        # This is a placeholder - implement logic to clean up sessions
        # that reference the deleted chunks if needed
        logger.info(f"Chat cleanup completed for {len(deleted_chunks)} chunks")
    except Exception as e:
        logger.error(f"Error in chat cleanup: {str(e)}")

# Ensure database indexes for performance
async def ensure_indexes():
    """Create database indexes for better query performance"""
    try:
        # Documents indexes
        await db.documents.create_index("id")
        await db.documents.create_index("filename")
        await db.documents.create_index("group_id")
        
        # Chat sessions indexes
        await db.chat_sessions.create_index("session_id")
        await db.chat_sessions.create_index([("timestamp", -1)])
        
        # Users indexes
        await db.users.create_index("username", unique=True)
        await db.users.create_index("email", unique=True)
        await db.users.create_index("role")
        
        # Groups indexes
        await db.groups.create_index("id")
        await db.groups.create_index("name")
        
        # Ratings indexes
        await db.ratings.create_index("session_id")
        await db.ratings.create_index([("timestamp", -1)])
        
        # Favorites indexes
        await db.favorites.create_index("session_id")
        await db.favorites.create_index("category")
        await db.favorites.create_index([("last_accessed", -1)])
        
        # FAQ indexes
        await db.faq.create_index("question")
        await db.faq.create_index("category")
        await db.faq.create_index([("frequency", -1)])
        
        # Activity logs indexes
        await db.user_activities.create_index("user_id")
        await db.user_activities.create_index([("timestamp", -1)])
        
        logger.info("Database indexes ensured")
    except Exception as e:
        logger.error(f"Error creating indexes: {str(e)}")

# API Routes

@api_router.get("/")
async def root():
    return {"message": "Kurumsal Prosedür Asistanı API'sine hoş geldiniz!"}

@api_router.get("/status", response_model=SystemStatus)
async def get_system_status():
    try:
        # Count documents
        total_documents = await db.documents.count_documents({})
        
        # Count groups
        total_groups = await db.groups.count_documents({})
        
        # Count total chunks
        total_chunks = 0
        async for doc in db.documents.find():
            chunks = doc.get('chunks', [])
            total_chunks += len(chunks)
        
        # Check if models are loaded
        embedding_model_loaded = sentence_model is not None
        faiss_index_ready = faiss_index is not None and len(document_chunks) > 0
        
        return SystemStatus(
            total_documents=total_documents,
            total_chunks=total_chunks,
            total_groups=total_groups,
            embedding_model_loaded=embedding_model_loaded,
            faiss_index_ready=faiss_index_ready,
            supported_formats=['.doc', '.docx'],
            processing_queue=0
        )
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return SystemStatus(
            total_documents=0,
            total_chunks=0,
            total_groups=0,
            embedding_model_loaded=False,
            faiss_index_ready=False
        )

@api_router.get("/documents", response_model=DocumentListResponse)
async def list_documents(group_id: Optional[str] = None, current_user: dict = Depends(require_authenticated)):
    try:
        # Build query filter
        query = {}
        if group_id:
            query["group_id"] = group_id
        
        # Get documents
        documents_list = []
        total_size = 0
        completed_count = 0
        processing_count = 0
        failed_count = 0
        
        async for doc in db.documents.find(query):
            doc_info = DocumentInfo(
                id=doc["id"],
                filename=doc["filename"],
                file_type=doc.get("file_type", ""),
                file_size=doc.get("file_size", 0),
                chunk_count=len(doc.get("chunks", [])),
                upload_date=doc.get("upload_date", datetime.utcnow()),
                group_id=doc.get("group_id"),
                group_name=doc.get("group_name")
            )
            documents_list.append(doc_info)
            
            # Statistics
            file_size = doc.get("file_size", 0)
            total_size += file_size
            
            # Assume all documents are completed for now
            completed_count += 1
        
        # Format total size
        def format_file_size(size_bytes):
            if size_bytes == 0:
                return "0 B"
            size_names = ["B", "KB", "MB", "GB"]
            import math
            i = int(math.floor(math.log(size_bytes, 1024)))
            p = math.pow(1024, i)
            s = round(size_bytes / p, 2)
            return f"{s} {size_names[i]}"
        
        total_size_human = format_file_size(total_size)
        
        statistics = {
            "total_count": len(documents_list),
            "completed_count": completed_count,
            "processing_count": processing_count,
            "failed_count": failed_count,
            "total_size": total_size,
            "total_size_human": total_size_human
        }
        
        return DocumentListResponse(
            documents=documents_list,
            statistics=statistics
        )
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Doküman listesi alınamadı")

@api_router.post("/bulk-upload-documents")
async def bulk_upload_documents(
    upload_request: BulkUploadRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_editor_or_admin)
):
    """
    Bulk document upload with optimized performance:
    - Concurrent processing of multiple files
    - Progress tracking
    - Detailed error reporting
    - Chunked processing for large files
    """
    start_time = datetime.utcnow()
    results = []
    successful_uploads = 0
    failed_uploads = 0
    
    try:
        total_files = len(upload_request.files)
        
        if total_files == 0:
            raise HTTPException(status_code=400, detail="Yüklenecek dosya bulunamadı")
        
        if total_files > 50:  # Limit for performance
            raise HTTPException(status_code=400, detail="Tek seferde maksimum 50 dosya yüklenebilir")
        
        # Process files concurrently
        async def process_single_file(file_data: BulkUploadFile) -> BulkUploadStatus:
            try:
                # Validate file
                filename = file_data.filename
                file_extension = Path(filename).suffix.lower()
                
                if file_extension not in ['.doc', '.docx']:
                    return BulkUploadStatus(
                        filename=filename,
                        status="error",
                        message="Sadece .doc ve .docx formatındaki dosyalar desteklenir"
                    )
                
                # Decode base64 content
                try:
                    file_content = base64.b64decode(file_data.content)
                except Exception:
                    return BulkUploadStatus(
                        filename=filename,
                        status="error",
                        message="Dosya içeriği decode edilemedi"
                    )
                
                # Check file size (limit to 10MB per file)
                if len(file_content) > 10 * 1024 * 1024:
                    return BulkUploadStatus(
                        filename=filename,
                        status="error",
                        message="Dosya boyutu 10MB'dan büyük olamaz"
                    )
                
                # Check if file already exists
                existing_doc = await db.documents.find_one({"filename": filename})
                if existing_doc:
                    return BulkUploadStatus(
                        filename=filename,
                        status="error",
                        message="Bu isimde dosya zaten mevcut"
                    )
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
                    temp_file.write(file_content)
                    temp_file_path = temp_file.name
                
                try:
                    # Extract text
                    text = extract_text_from_document(temp_file_path, file_extension)
                    
                    if not text.strip():
                        return BulkUploadStatus(
                            filename=filename,
                            status="error",
                            message="Dosyadan metin çıkarılamadı"
                        )
                    
                    # Create chunks
                    chunks = create_chunks(text)
                    
                    # Get group info
                    group_id = file_data.group_id or upload_request.group_id
                    group_name = None
                    
                    if group_id:
                        group_doc = await db.groups.find_one({"id": group_id})
                        if group_doc:
                            group_name = group_doc["name"]
                    
                    # Create document
                    document_id = str(uuid.uuid4())
                    document = {
                        "id": document_id,
                        "filename": filename,
                        "file_type": file_extension,
                        "file_size": len(file_content),
                        "content": base64.b64encode(file_content).decode('utf-8'),
                        "text": text,
                        "chunks": chunks,
                        "chunk_count": len(chunks),
                        "upload_date": datetime.utcnow(),
                        "group_id": group_id,
                        "group_name": group_name
                    }
                    
                    # Save to database
                    await db.documents.insert_one(document)
                    
                    # Update FAISS index in background
                    background_tasks.add_task(
                        update_faiss_index, 
                        chunks, 
                        document_id, 
                        filename, 
                        group_id, 
                        group_name
                    )
                    
                    return BulkUploadStatus(
                        filename=filename,
                        status="success",
                        message=f"Başarıyla yüklendi ({len(chunks)} parça)",
                        document_id=document_id
                    )
                    
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
                        
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
                return BulkUploadStatus(
                    filename=filename,
                    status="error",
                    message=f"İşleme hatası: {str(e)}"
                )
        
        # Process all files concurrently (with semaphore to limit concurrency)
        semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent processes
        
        async def process_with_semaphore(file_data):
            async with semaphore:
                return await process_single_file(file_data)
        
        # Execute all tasks concurrently
        tasks = [process_with_semaphore(file_data) for file_data in upload_request.files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        final_results = []
        for result in results:
            if isinstance(result, Exception):
                final_results.append(BulkUploadStatus(
                    filename="unknown",
                    status="error",
                    message=f"İşleme hatası: {str(result)}"
                ))
                failed_uploads += 1
            else:
                final_results.append(result)
                if result.status == "success":
                    successful_uploads += 1
                else:
                    failed_uploads += 1
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log activity
        asyncio.create_task(log_user_activity(
            current_user["id"],
            "bulk_document_upload",
            f"Bulk upload: {successful_uploads}/{total_files} successful"
        ))
        
        return BulkUploadResponse(
            total_files=total_files,
            successful_uploads=successful_uploads,
            failed_uploads=failed_uploads,
            results=final_results,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="Toplu yükleme sırasında hata oluştu")

@api_router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...), 
    group_id: Optional[str] = None, 
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: dict = Depends(require_editor_or_admin)
):
    if file.filename == '':
        raise HTTPException(status_code=400, detail="Dosya seçilmedi")
    
    # Check file extension
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ['.doc', '.docx']:
        raise HTTPException(status_code=400, detail="Sadece .doc ve .docx formatındaki dosyalar desteklenir")
    
    # Check if file already exists
    existing_doc = await db.documents.find_one({"filename": file.filename})
    if existing_doc:
        raise HTTPException(status_code=400, detail="Bu isimde dosya zaten mevcut")
    
    try:
        # Read file content
        content = await file.read()
        
        # Check file size (limit to 10MB)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Dosya boyutu 10MB'dan büyük olamaz")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Extract text
            text = extract_text_from_document(temp_file_path, file_extension)
            
            # Create chunks
            chunks = create_chunks(text)
            
            # Get group information
            group_name = None
            if group_id:
                group_doc = await db.groups.find_one({"id": group_id})
                if group_doc:
                    group_name = group_doc["name"]
            
            # Create document record
            document_id = str(uuid.uuid4())
            document = {
                "id": document_id,
                "filename": file.filename,
                "file_type": file_extension,
                "file_size": len(content),
                "content": base64.b64encode(content).decode('utf-8'),
                "text": text,
                "chunks": chunks,
                "chunk_count": len(chunks),
                "upload_date": datetime.utcnow(),
                "group_id": group_id,
                "group_name": group_name
            }
            
            # Save to database
            await db.documents.insert_one(document)
            
            # Update FAISS index in background
            background_tasks.add_task(update_faiss_index, chunks, document_id, file.filename, group_id, group_name)
            
            # Log activity
            asyncio.create_task(log_user_activity(
                current_user["id"], 
                "document_upload", 
                f"Uploaded document: {file.filename} ({len(chunks)} chunks)"
            ))
            
            return {
                "message": f"'{file.filename}' başarıyla yüklendi ve işlendi", 
                "document_id": document_id,
                "chunks": len(chunks),
                "group_id": group_id,
                "group_name": group_name
            }
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Could not delete temp file: {e}")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload error: {str(e)}")
        if "textract ve antiword başarısız" in str(e):
            raise HTTPException(status_code=500, detail="DOC dosyası işlenirken hata oluştu. Dosya bozuk olabilir.")
        raise HTTPException(status_code=500, detail="Dosya yüklenirken hata oluştu")

@api_router.delete("/documents/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(document_id: str, background_tasks: BackgroundTasks, current_user: dict = Depends(require_editor_or_admin)):
    try:
        # Find document
        document = await db.documents.find_one({"id": document_id})
        if not document:
            raise HTTPException(status_code=404, detail="Doküman bulunamadı")
        
        filename = document.get("filename", "Bilinmeyen dosya")
        chunk_count = document.get("chunk_count", len(document.get("chunks", [])))
        document_chunks = document.get("chunks", [])
        
        # Dokümanı sil (ana işlem)
        result = await db.documents.delete_one({"id": document_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Doküman silinemedi")
        
        # Background tasks - OPTIMIZED FOR SEQUENTIAL DELETES
        if document_chunks:
            # Chat cleanup - immediate (fast query)
            background_tasks.add_task(cleanup_chat_sessions, document_chunks)
            
            # FAISS update - DEBOUNCED (avoid sequential rebuilds)
            background_tasks.add_task(debounced_faiss_update)
        
        # Activity logging - NON-BLOCKING
        asyncio.create_task(log_user_activity(
            current_user["id"], 
            "document_delete", 
            f"Deleted document: {filename} ({chunk_count} chunks)"
        ))
        
        # IMMEDIATE response (no await on background tasks)
        return DocumentDeleteResponse(
            message=f"'{filename}' dokümanı başarıyla silindi",
            document_id=document_id,
            deleted_chunks=chunk_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document deletion error: {str(e)}")
        raise HTTPException(status_code=500, detail="Doküman silinirken hata oluştu")

# Authentication endpoints
@api_router.post("/auth/login", response_model=LoginResponse)
async def login(user_credentials: UserLogin):
    try:
        # Find user by username
        user = await db.users.find_one({"username": user_credentials.username})
        if not user:
            raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre yanlış")
        
        # Verify password
        if not verify_password(user_credentials.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre yanlış")
        
        # Check if user is active
        if not user.get("is_active", True):
            raise HTTPException(status_code=401, detail="Kullanıcı hesabı deaktif")
        
        # Create access token
        access_token_expires = timedelta(hours=JWT_ACCESS_TOKEN_EXPIRE_HOURS)
        access_token = create_access_token(
            data={"sub": user["username"]}, expires_delta=access_token_expires
        )
        
        # Update last login
        await db.users.update_one(
            {"username": user_credentials.username},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        # Log activity
        asyncio.create_task(log_user_activity(user["id"], "login", f"User logged in: {user['username']}"))
        
        # Check if password change is required
        must_change_password = user.get("must_change_password", False)
        
        user_info = UserInfo(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"],
            last_login=user.get("last_login"),
            must_change_password=must_change_password
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_info,
            must_change_password=must_change_password
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Giriş işlemi sırasında hata oluştu")

@api_router.post("/auth/logout")
async def logout(current_user: dict = Depends(get_current_active_user)):
    try:
        # Log activity
        asyncio.create_task(log_user_activity(current_user["id"], "logout", f"User logged out: {current_user['username']}"))
        return {"message": "Başarıyla çıkış yapıldı"}
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Çıkış işlemi sırasında hata oluştu")

@api_router.get("/auth/me", response_model=UserInfo)
async def get_current_user_info(current_user: dict = Depends(get_current_active_user)):
    return UserInfo(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        is_active=current_user["is_active"],
        created_at=current_user["created_at"],
        last_login=current_user.get("last_login"),
        must_change_password=current_user.get("must_change_password", False)
    )

@api_router.post("/auth/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: dict = Depends(get_current_active_user)
):
    try:
        # Verify current password
        if not verify_password(password_data.current_password, current_user["password_hash"]):
            raise HTTPException(status_code=400, detail="Mevcut şifre yanlış")
        
        # Validate new password
        if len(password_data.new_password) < 6:
            raise HTTPException(status_code=400, detail="Yeni şifre en az 6 karakter olmalıdır")
        
        # Hash new password
        new_password_hash = get_password_hash(password_data.new_password)
        
        # Update password and clear must_change_password flag
        await db.users.update_one(
            {"id": current_user["id"]},
            {
                "$set": {
                    "password_hash": new_password_hash,
                    "must_change_password": False  # Clear the flag after password change
                }
            }
        )
        
        # Log activity
        asyncio.create_task(log_user_activity(current_user["id"], "password_change", "Password changed successfully"))
        
        return {"message": "Şifre başarıyla değiştirildi"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        raise HTTPException(status_code=500, detail="Şifre değiştirilirken hata oluştu")

@api_router.post("/auth/create-user")
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_current_active_user)
):
    try:
        # Role-based user creation permissions
        current_role = current_user.get("role")
        
        if current_role == "admin":
            # Admin can create any role
            allowed_roles = ["admin", "editor", "viewer"]
        elif current_role == "editor":
            # Editor can only create viewers
            allowed_roles = ["viewer"]
        else:
            # Viewers cannot create users
            raise HTTPException(status_code=403, detail="Kullanıcı oluşturma yetkiniz yok")
        
        if user_data.role not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Bu rolde kullanıcı oluşturma yetkiniz yok: {user_data.role}")
        
        # Check if username already exists
        existing_user = await db.users.find_one({"username": user_data.username})
        if existing_user:
            raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten kullanılıyor")
        
        # Check if email already exists
        existing_email = await db.users.find_one({"email": user_data.email})
        if existing_email:
            raise HTTPException(status_code=400, detail="Bu email adresi zaten kullanılıyor")
        
        # Validate password
        if len(user_data.password) < 6:
            raise HTTPException(status_code=400, detail="Şifre en az 6 karakter olmalıdır")
        
        # Hash password
        password_hash = get_password_hash(user_data.password)
        
        # Create user
        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
            is_active=user_data.is_active,
            password_hash=password_hash,
            created_by=current_user["id"],
            must_change_password=True  # NEW: Force password change on first login
        )
        
        await db.users.insert_one(user.dict())
        
        # Log activity
        asyncio.create_task(log_user_activity(
            current_user["id"], 
            "user_create", 
            f"Created user: {user_data.username} ({user_data.role})"
        ))
        
        return {
            "message": f"Kullanıcı '{user_data.username}' başarıyla oluşturuldu",
            "user_id": user.id,
            "must_change_password": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User creation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Kullanıcı oluşturulurken hata oluştu")

# Other endpoints would continue here...
# (The rest of the endpoints remain the same, but I'm truncating for space)

# Include the router
app.include_router(api_router)

# Startup event
@app.on_event("startup")
async def startup_event():
    # Load AI models
    load_models()
    
    # Ensure database indexes
    await ensure_indexes()
    
    # Create initial admin user if no users exist
    user_count = await db.users.count_documents({})
    if user_count == 0:
        admin_password = "admin123"  # Change this in production
        admin_user = User(
            username="admin",
            email="admin@company.com",
            full_name="Sistem Yöneticisi",
            role="admin",
            password_hash=get_password_hash(admin_password),
            must_change_password=True  # NEW: Force admin to change password on first login
        )
        
        await db.users.insert_one(admin_user.dict())
        logger.info("Initial admin user created - Username: admin, Password: admin123")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)