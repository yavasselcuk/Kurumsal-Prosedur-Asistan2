from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
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
    created_at: datetime
    processed_at: Optional[datetime] = None

class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    question: str
    answer: str
    context_chunks: List[str]
    source_documents: List[str]  # Kaynak doküman adları
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SystemStatus(BaseModel):
    total_documents: int
    total_chunks: int
    embedding_model_loaded: bool
    faiss_index_ready: bool
    supported_formats: List[str]
    processing_queue: int

class DocumentDeleteResponse(BaseModel):
    message: str
    document_id: str
    deleted_chunks: int

# Helper functions
async def extract_text_from_document(file_content: bytes, filename: str) -> str:
    """Word dokümanından metin çıkarma (.doc ve .docx desteği)"""
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
            # DOC dosyaları için
            try:
                # Method 1: textract ile
                extracted_text = textract.process(temp_file_path).decode('utf-8')
                
            except Exception as e:
                logging.warning(f"textract failed for {filename}: {str(e)}")
                try:
                    # Method 2: Alternatif olarak antiword (eğer sistem'de kuruluysa)
                    import subprocess
                    result = subprocess.run(['antiword', temp_file_path], 
                                          capture_output=True, text=True, check=True)
                    extracted_text = result.stdout
                    
                except (subprocess.CalledProcessError, FileNotFoundError) as e2:
                    logging.error(f"antiword also failed for {filename}: {str(e2)}")
                    raise HTTPException(status_code=400, detail=f"DOC işleme hatası. Lütfen dosyayı DOCX formatında yükleyin.")
        
        else:
            raise HTTPException(status_code=400, detail=f"Desteklenmeyen dosya formatı: {file_extension}")
        
        # Geçici dosyayı sil
        os.unlink(temp_file_path)
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Doküman boş veya metin çıkarılamadı")
        
        return extracted_text.strip()
        
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

async def generate_answer_with_gemini(question: str, context_chunks: List[str], session_id: str) -> str:
    """Gemini ile cevap üretme"""
    try:
        # Kontekst oluştur
        context = "\n\n".join(context_chunks)
        
        # System message - Türkçe prompt
        system_message = """Sen kurumsal prosedür dokümanlarına dayalı bir asistansın. Sadece verilen doküman içeriğini kullanarak Türkçe cevap ver.

ÖNEMLİ KURALLAR:
1. Sadece verilen kontekst bilgilerini kullan
2. Kontekstde bulunmayan bilgileri asla uydurma
3. Eğer sorunun cevabı kontekstte yoksa "Bu bilgi mevcut dokümanlarımda bulunmamaktadır." de
4. Cevaplarını net, anlaşılır ve profesyonel şekilde ver
5. Mümkün olduğunca detaylı ve yapılandırılmış cevaplar ver"""

        # Gemini chat oluştur
        chat = LlmChat(
            api_key=os.environ['GEMINI_API_KEY'],
            session_id=session_id,
            system_message=system_message
        ).with_model("gemini", "gemini-2.0-flash").with_max_tokens(4096)
        
        # Kullanıcı mesajı oluştur
        user_message = UserMessage(
            text=f"""Kontekst Bilgileri:
{context}

Soru: {question}

Lütfen sadece yukarıdaki kontekst bilgilerini kullanarak soruyu cevapla."""
        )
        
        # Cevap al
        response = await chat.send_message(user_message)
        return response
        
    except Exception as e:
        logging.error(f"Gemini cevap üretme hatası: {str(e)}")
        return "Üzgünüm, şu anda sorunuzu cevaplayamıyorum. Lütfen daha sonra tekrar deneyin."

# API Endpoints
@api_router.get("/")
async def root():
    return {"message": "Kurumsal Prosedür Asistanı API'sine hoş geldiniz!"}

@api_router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Sistem durumunu getir"""
    try:
        doc_count = await db.documents.count_documents({})
        chunk_count = len(document_chunks)
        
        return SystemStatus(
            total_documents=doc_count,
            total_chunks=chunk_count,
            embedding_model_loaded=embedding_model is not None,
            faiss_index_ready=faiss_index is not None,
            supported_formats=['.doc', '.docx'],
            processing_queue=0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sistem durumu alınırken hata: {str(e)}")

@api_router.post("/upload-document")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Word dokümanı yükleme (.doc ve .docx desteği)"""
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
            upload_status="processing"
        )
        
        await db.documents.insert_one(document.dict())
        
        # Embedding oluşturma işlemini background'a at
        background_tasks.add_task(process_document_embeddings, document.id)
        
        return {
            "message": f"Doküman başarıyla yüklendi: {file.filename}",
            "document_id": document.id,
            "file_type": document.file_type,
            "file_size": get_file_size_human_readable(file_size),
            "chunk_count": len(chunks),
            "processing": "Embedding oluşturma işlemi başlatıldı"
        }
        
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
        answer = await generate_answer_with_gemini(
            request.question, 
            similar_chunks, 
            session_id
        )
        
        # Chat geçmişini kaydet
        chat_session = ChatSession(
            session_id=session_id,
            question=request.question,
            answer=answer,
            context_chunks=similar_chunks
        )
        
        await db.chat_sessions.insert_one(chat_session.dict())
        
        return {
            "question": request.question,
            "answer": answer,
            "session_id": session_id,
            "context_found": True,
            "context_chunks_count": len(similar_chunks)
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

@api_router.get("/documents")
async def get_documents():
    """Yüklenmiş dokümanları listele (gelişmiş)"""
    try:
        # Dokümanları getir (içerik hariç)
        documents = await db.documents.find({}, {
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
        
        # İstatistikler
        total_count = len(processed_documents)
        completed_count = len([d for d in processed_documents if d["embeddings_created"]])
        processing_count = len([d for d in processed_documents if d["upload_status"] == "processing"])
        failed_count = len([d for d in processed_documents if d["upload_status"] == "failed"])
        total_size = sum(d["file_size"] for d in processed_documents)
        
        return {
            "documents": processed_documents,
            "statistics": {
                "total_count": total_count,
                "completed_count": completed_count,
                "processing_count": processing_count,
                "failed_count": failed_count,
                "total_size": total_size,
                "total_size_human": get_file_size_human_readable(total_size)
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