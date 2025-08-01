import React, { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [systemStatus, setSystemStatus] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState('');
  const [activeTab, setActiveTab] = useState('chat');
  const chatEndRef = useRef(null);

  const backendUrl = process.env.REACT_APP_BACKEND_URL;

  useEffect(() => {
    // Session ID oluştur
    setSessionId(generateSessionId());
    // Sistem durumunu al
    fetchSystemStatus();
    // Dokümanları al
    fetchDocuments();
  }, []);

  useEffect(() => {
    // Chat'in sonuna scroll yap
    scrollToBottom();
  }, [chatHistory]);

  const generateSessionId = () => {
    return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
  };

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchSystemStatus = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/status`);
      const data = await response.json();
      setSystemStatus(data);
    } catch (error) {
      console.error('Sistem durumu alınamadı:', error);
    }
  };

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/documents`);
      const data = await response.json();
      setDocuments(data.documents || []);
      
      // İstatistikleri de saklayabiliriz
      if (data.statistics) {
        // İstatistikleri state'e ekleyebiliriz
        console.log('Document statistics:', data.statistics);
      }
    } catch (error) {
      console.error('Dokümanlar alınamadı:', error);
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file && (file.name.endsWith('.docx') || file.name.endsWith('.doc'))) {
      // Dosya boyutu kontrolü (10MB)
      const maxSize = 10 * 1024 * 1024; // 10MB
      if (file.size > maxSize) {
        alert('Dosya boyutu çok büyük. Maksimum 10MB olmalıdır.');
        event.target.value = '';
        return;
      }
      
      setSelectedFile(file);
      setUploadProgress('');
    } else {
      alert('Lütfen sadece .doc veya .docx formatındaki dosyaları seçin.');
      event.target.value = '';
    }
  };

  const handleFileUpload = async () => {
    if (!selectedFile) {
      alert('Lütfen bir dosya seçin.');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      setUploadProgress('Doküman yükleniyor...');
      
      const response = await fetch(`${backendUrl}/api/upload-document`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        setUploadProgress(`✅ ${data.message}`);
        if (data.file_size) {
          setUploadProgress(prev => prev + ` (${data.file_size}, ${data.chunk_count} parça)`);
        }
        setSelectedFile(null);
        document.getElementById('fileInput').value = '';
        
        // Dokümanları ve sistem durumunu güncelle
        setTimeout(() => {
          fetchDocuments();
          fetchSystemStatus();
        }, 2000);
      } else {
        setUploadProgress(`❌ Hata: ${data.detail}`);
      }
    } catch (error) {
      setUploadProgress(`❌ Yükleme hatası: ${error.message}`);
    }
  };

  const handleQuestionSubmit = async (e) => {
    e.preventDefault();
    
    if (!question.trim()) {
      alert('Lütfen bir soru yazın.');
      return;
    }

    // Kullanıcının sorusunu chat geçmişine ekle
    const userMessage = {
      type: 'user',
      content: question,
      timestamp: new Date().toLocaleTimeString('tr-TR')
    };

    setChatHistory(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await fetch(`${backendUrl}/api/ask-question`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          session_id: sessionId
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // AI'ın cevabını chat geçmişine ekle
        const aiMessage = {
          type: 'ai',
          content: data.answer,
          contextFound: data.context_found,
          chunksCount: data.context_chunks_count,
          timestamp: new Date().toLocaleTimeString('tr-TR')
        };

        setChatHistory(prev => [...prev, aiMessage]);
      } else {
        throw new Error(data.detail || 'Bilinmeyen hata');
      }
    } catch (error) {
      // Hata mesajını chat geçmişine ekle
      const errorMessage = {
        type: 'error',
        content: `Hata: ${error.message}`,
        timestamp: new Date().toLocaleTimeString('tr-TR')
      };

      setChatHistory(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setQuestion('');
    }
  };

  const handleDeleteDocument = async (documentId) => {
    if (!window.confirm('Bu dokümanı silmek istediğinizden emin misiniz?')) {
      return;
    }

    try {
      const response = await fetch(`${backendUrl}/api/documents/${documentId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        fetchDocuments();
        fetchSystemStatus();
        alert('Doküman başarıyla silindi.');
      } else {
        const data = await response.json();
        alert(`Hata: ${data.detail}`);
      }
    } catch (error) {
      alert(`Silme hatası: ${error.message}`);
    }
  };

  const clearChat = () => {
    setChatHistory([]);
    setSessionId(generateSessionId());
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-white shadow-lg border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-lg">KPA</span>
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">Kurumsal Prosedür Asistanı</h1>
                  <p className="text-sm text-gray-600">AI destekli doküman soru-cevap sistemi</p>
                </div>
              </div>
            </div>
            
            {systemStatus && (
              <div className="hidden md:flex items-center space-x-4 text-sm">
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${systemStatus.faiss_index_ready ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
                  <span className="text-gray-700">{systemStatus.total_documents} Doküman</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${systemStatus.total_chunks > 0 ? 'bg-green-500' : 'bg-gray-400'}`}></div>
                  <span className="text-gray-700">{systemStatus.total_chunks} Metin Parçası</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        <div className="flex space-x-1 bg-white rounded-lg p-1 shadow-sm">
          <button
            onClick={() => setActiveTab('chat')}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'chat'
                ? 'bg-blue-500 text-white shadow-sm'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            💬 Soru-Cevap
          </button>
          <button
            onClick={() => setActiveTab('documents')}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'documents'
                ? 'bg-blue-500 text-white shadow-sm'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            📁 Doküman Yönetimi
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'chat' ? (
          /* Chat Tab */
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Chat Area */}
            <div className="lg:col-span-3">
              <div className="bg-white rounded-xl shadow-lg h-[600px] flex flex-col">
                {/* Chat Header */}
                <div className="flex justify-between items-center p-6 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">Sohbet</h2>
                  <button
                    onClick={clearChat}
                    disabled={chatHistory.length === 0}
                    className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    🗑️ Temizle
                  </button>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                  {chatHistory.length === 0 ? (
                    <div className="text-center py-12">
                      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span className="text-2xl">🤖</span>
                      </div>
                      <p className="text-gray-600 text-lg mb-2">Merhaba! Ben Kurumsal Prosedür Asistanınızım.</p>
                      <p className="text-gray-500">Yüklediğiniz dokümanlar hakkında soru sorabilirsiniz.</p>
                    </div>
                  ) : (
                    chatHistory.map((message, index) => (
                      <div key={index} className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-3xl rounded-2xl px-4 py-3 ${
                          message.type === 'user'
                            ? 'bg-blue-500 text-white'
                            : message.type === 'error'
                            ? 'bg-red-100 text-red-800 border border-red-200'
                            : 'bg-gray-100 text-gray-900'
                        }`}>
                          <p className="whitespace-pre-wrap">{message.content}</p>
                          <div className="flex justify-between items-center mt-2 text-xs opacity-70">
                            <span>{message.timestamp}</span>
                            {message.type === 'ai' && message.contextFound && (
                              <span className="bg-white bg-opacity-20 px-2 py-1 rounded">
                                {message.chunksCount} kaynak kullanıldı
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                  
                  {isLoading && (
                    <div className="flex justify-start">
                      <div className="bg-gray-100 rounded-2xl px-4 py-3 max-w-xs">
                        <div className="flex items-center space-x-2">
                          <div className="flex space-x-1">
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                          </div>
                          <span className="text-gray-600 text-sm">Cevap hazırlanıyor...</span>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  <div ref={chatEndRef} />
                </div>

                {/* Question Input */}
                <div className="border-t border-gray-200 p-6">
                  <form onSubmit={handleQuestionSubmit} className="flex space-x-4">
                    <input
                      type="text"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      placeholder="Prosedürler hakkında soru sorun..."
                      disabled={isLoading}
                      className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                    />
                    <button
                      type="submit"
                      disabled={isLoading || !question.trim()}
                      className="px-6 py-3 bg-blue-500 text-white rounded-xl hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
                    >
                      <span>Gönder</span>
                      <span>🚀</span>
                    </button>
                  </form>
                </div>
              </div>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* System Status */}
              {systemStatus && (
                <div className="bg-white rounded-xl shadow-lg p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Sistem Durumu</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">Dokümanlar</span>
                      <span className="font-semibold text-blue-600">{systemStatus.total_documents}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">Metin Parçaları</span>
                      <span className="font-semibold text-green-600">{systemStatus.total_chunks}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">AI Modeli</span>
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        systemStatus.embedding_model_loaded ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {systemStatus.embedding_model_loaded ? 'Hazır' : 'Yüklenmedi'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">Arama İndeksi</span>
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        systemStatus.faiss_index_ready ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {systemStatus.faiss_index_ready ? 'Aktif' : 'Hazırlanıyor'}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Quick Tips */}
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">💡 İpuçları</h3>
                <div className="space-y-3 text-sm text-gray-600">
                  <p>• Spesifik sorular sorun</p>
                  <p>• Doküman adlarını kullanın</p>
                  <p>• Farklı kelimelerle deneyin</p>
                  <p>• Kısa ve net cümleler kurun</p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* Documents Tab */
          <div className="space-y-6">
            {/* Upload Section */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-6">📤 Doküman Yükleme</h2>
              
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                <div className="space-y-4">
                  <div className="flex flex-col items-center space-y-3">
                    <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-2xl">📄</span>
                    </div>
                    <div>
                      <p className="text-lg font-medium text-gray-900">Word Dokümanı Yükleyin</p>
                      <p className="text-gray-600">Sadece .docx formatı desteklenir</p>
                    </div>
                  </div>
                  
                  <div className="flex flex-col sm:flex-row items-center justify-center space-y-2 sm:space-y-0 sm:space-x-4">
                    <input
                      id="fileInput"
                      type="file"
                      accept=".docx"
                      onChange={handleFileSelect}
                      className="hidden"
                    />
                    <label
                      htmlFor="fileInput"
                      className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 cursor-pointer transition-colors"
                    >
                      Dosya Seç
                    </label>
                    
                    {selectedFile && (
                      <div className="flex items-center space-x-3">
                        <span className="text-sm text-gray-600">
                          Seçilen: {selectedFile.name}
                        </span>
                        <button
                          onClick={handleFileUpload}
                          className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
                        >
                          Yükle
                        </button>
                      </div>
                    )}
                  </div>
                  
                  {uploadProgress && (
                    <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-700">{uploadProgress}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Documents List */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold text-gray-900">📁 Yüklenmiş Dokümanlar</h2>
                <button
                  onClick={fetchDocuments}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  🔄 Yenile
                </button>
              </div>

              {documents.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span className="text-2xl">📂</span>
                  </div>
                  <p className="text-gray-600">Henüz doküman yüklenmemiş.</p>
                  <p className="text-gray-500 text-sm mt-1">Yukarıdaki alandan doküman yükleyebilirsiniz.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {documents.map((doc) => (
                    <div key={doc.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-2">
                            <span className="text-lg">📄</span>
                            <h3 className="text-sm font-medium text-gray-900 truncate">
                              {doc.filename}
                            </h3>
                          </div>
                          
                          <div className="space-y-1 text-xs text-gray-600">
                            <p>Parça sayısı: {doc.chunks?.length || 0}</p>
                            <p>Yüklenme: {new Date(doc.created_at).toLocaleDateString('tr-TR')}</p>
                            <p className="flex items-center space-x-1">
                              <span className={`w-2 h-2 rounded-full ${doc.embeddings_created ? 'bg-green-500' : 'bg-yellow-500'}`}></span>
                              <span>{doc.embeddings_created ? 'İşlendi' : 'İşleniyor'}</span>
                            </p>
                          </div>
                        </div>
                        
                        <button
                          onClick={() => handleDeleteDocument(doc.id)}
                          className="ml-2 p-1 text-red-500 hover:bg-red-50 rounded transition-colors"
                          title="Sil"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;