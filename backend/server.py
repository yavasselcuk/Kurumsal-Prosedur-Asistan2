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
    content: str
    chunks: List[str]
    embeddings_created: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    question: str
    answer: str
    context_chunks: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SystemStatus(BaseModel):
    total_documents: int
    total_chunks: int
    embedding_model_loaded: bool
    faiss_index_ready: bool

# Helper functions
async def extract_text_from_docx(file_content: bytes) -> str:
    """Word dokümanından metin çıkarma"""
    try:
        # Geçici dosya oluştur
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        # Word dokümanını oku
        doc = Document(temp_file_path)
        text_content = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_content.append(paragraph.text.strip())
        
        # Geçici dosyayı sil
        os.unlink(temp_file_path)
        
        return '\n'.join(text_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Word dokümanı işlenirken hata: {str(e)}")

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
            faiss_index_ready=faiss_index is not None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sistem durumu alınırken hata: {str(e)}")

@api_router.post("/upload-document")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Word dokümanı yükleme"""
    try:
        # Dosya tipini kontrol et
        if not file.filename.endswith('.docx'):
            raise HTTPException(status_code=400, detail="Sadece .docx formatındaki dosyalar desteklenir")
        
        # Dosya içeriğini oku
        file_content = await file.read()
        
        # Word dokümanından metin çıkar
        text_content = await extract_text_from_docx(file_content)
        
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="Doküman boş veya okunamıyor")
        
        # Metni parçalara ayır
        chunks = split_text_into_chunks(text_content)
        
        # Dokümanı veritabanına kaydet
        document = DocumentUpload(
            filename=file.filename,
            content=text_content,
            chunks=chunks,
            embeddings_created=False
        )
        
        await db.documents.insert_one(document.dict())
        
        # Embedding oluşturma işlemini background'a at
        background_tasks.add_task(process_document_embeddings, document.id)
        
        return {
            "message": f"Doküman başarıyla yüklendi: {file.filename}",
            "document_id": document.id,
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
    """Yüklenmiş dokümanları listele"""
    try:
        documents = await db.documents.find({}, {
            "content": 0,  # İçeriği dahil etme (çok büyük olabilir)
            "chunks": 0    # Chunk'ları dahil etme
        }).to_list(100)
        
        return {
            "documents": documents,
            "total_count": len(documents)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dokümanlar alınırken hata: {str(e)}")

@api_router.delete("/documents/{document_id}")
async def delete_document(document_id: str, background_tasks: BackgroundTasks):
    """Doküman silme"""
    try:
        result = await db.documents.delete_one({"id": document_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Doküman bulunamadı")
        
        # FAISS indeksini güncelle
        background_tasks.add_task(update_faiss_index)
        
        return {"message": "Doküman başarıyla silindi", "document_id": document_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Doküman silinirken hata: {str(e)}")

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