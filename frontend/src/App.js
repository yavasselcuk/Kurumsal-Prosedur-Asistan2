import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import './App.css';

function App() {
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [systemStatus, setSystemStatus] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [groups, setGroups] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState('');
  const [activeTab, setActiveTab] = useState('chat');
  const [selectedGroup, setSelectedGroup] = useState('all'); // 'all', 'ungrouped', group_id
  const [selectedDocuments, setSelectedDocuments] = useState([]);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [showMoveModal, setShowMoveModal] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupDescription, setNewGroupDescription] = useState('');
  const [newGroupColor, setNewGroupColor] = useState('#3b82f6');
  const chatEndRef = useRef(null);

  const backendUrl = process.env.REACT_APP_BACKEND_URL;

  useEffect(() => {
    // Session ID oluştur
    setSessionId(generateSessionId());
    // Sistem durumunu al
    fetchSystemStatus();
    // Dokümanları al
    fetchDocuments();
    // Grupları al
    fetchGroups();
  }, []);

  useEffect(() => {
    // selectedGroup değiştiğinde dokümanları yeniden fetch et
    fetchDocuments();
  }, [selectedGroup]);

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
      let url = `${backendUrl}/api/documents`;
      
      // Grup filtresi ekle
      if (selectedGroup && selectedGroup !== 'all') {
        url += `?group_id=${selectedGroup}`;
      }
      
      const response = await fetch(url);
      const data = await response.json();
      
      if (response.ok) {
        setDocuments(data.documents || []);
        
        // İstatistikleri de saklayabiliriz
        if (data.statistics) {
          console.log('Document statistics:', data.statistics);
        }
      } else {
        console.error('API Error:', data);
      }
    } catch (error) {
      console.error('Dokümanlar alınamadı:', error);
    }
  };

  const fetchGroups = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/groups`);
      const data = await response.json();
      setGroups(data.groups || []);
    } catch (error) {
      console.error('Gruplar alınamadı:', error);
    }
  };

  const handleCreateGroup = async () => {
    if (!newGroupName.trim()) {
      alert('Grup adı boş olamaz.');
      return;
    }

    try {
      const response = await fetch(`${backendUrl}/api/groups`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: newGroupName,
          description: newGroupDescription,
          color: newGroupColor
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setNewGroupName('');
        setNewGroupDescription('');
        setNewGroupColor('#3b82f6');
        setShowGroupModal(false);
        fetchGroups();
        alert(data.message);
      } else {
        alert(`Hata: ${data.detail}`);
      }
    } catch (error) {
      alert(`Grup oluşturma hatası: ${error.message}`);
    }
  };

  const handleMoveDocuments = async (targetGroupId) => {
    if (selectedDocuments.length === 0) {
      alert('Lütfen taşınacak dokümanları seçin.');
      return;
    }

    try {
      const response = await fetch(`${backendUrl}/api/documents/move`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_ids: selectedDocuments,
          group_id: targetGroupId
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setSelectedDocuments([]);
        setShowMoveModal(false);
        fetchDocuments();
        fetchGroups();
        alert(data.message);
      } else {
        alert(`Hata: ${data.detail}`);
      }
    } catch (error) {
      alert(`Taşıma hatası: ${error.message}`);
    }
  };

  const handleDeleteGroup = async (groupId, groupName) => {
    if (!window.confirm(`'${groupName}' grubunu silmek istediğinizden emin misiniz? Gruptaki dokümanlar gruplandırılmamış duruma getirilecek.`)) {
      return;
    }

    try {
      console.log('Deleting group:', groupId, groupName);
      console.log('Backend URL:', backendUrl);
      
      const response = await fetch(`${backendUrl}/api/groups/${groupId}?move_documents=true`, {
        method: 'DELETE',
      });

      console.log('Group delete response status:', response.status);
      const data = await response.json();
      console.log('Group delete response data:', data);

      if (response.ok) {
        await fetchGroups();
        await fetchDocuments();
        alert(data.message || 'Grup başarıyla silindi.');
      } else {
        console.error('Group delete failed:', data);
        alert(`Hata: ${data.detail || data.message || 'Bilinmeyen hata'}`);
      }
    } catch (error) {
      console.error('Group delete error:', error);
      alert(`Grup silme hatası: ${error.message}`);
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
    
    // Grup seçildiyse ekle
    if (selectedGroup && selectedGroup !== 'all' && selectedGroup !== 'ungrouped') {
      formData.append('group_id', selectedGroup);
    }

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
          fetchGroups();
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
      console.log('Deleting document:', documentId);
      console.log('Backend URL:', backendUrl);
      
      const response = await fetch(`${backendUrl}/api/documents/${documentId}`, {
        method: 'DELETE',
      });

      console.log('Delete response status:', response.status);
      const data = await response.json();
      console.log('Delete response data:', data);

      if (response.ok) {
        await fetchDocuments();
        await fetchSystemStatus();
        alert(data.message || 'Doküman başarıyla silindi.');
      } else {
        console.error('Delete failed:', data);
        alert(`Hata: ${data.detail || data.message || 'Bilinmeyen hata'}`);
      }
    } catch (error) {
      console.error('Delete error:', error);
      alert(`Silme hatası: ${error.message}`);
    }
  };

  const handleViewDocument = async (documentId) => {
    try {
      const response = await fetch(`${backendUrl}/api/documents/${documentId}`);
      if (response.ok) {
        const doc = await response.json();
        
        // Modal veya alert ile doküman detaylarını göster
        const details = `
Dosya Adı: ${doc.filename}
Format: ${doc.file_type?.toUpperCase()}
Boyut: ${doc.file_size_human}
Parça Sayısı: ${doc.chunk_count}
Kullanım Sayısı: ${doc.usage_count || 0}
Yüklenme: ${doc.created_at ? new Date(doc.created_at).toLocaleString('tr-TR') : 'Bilinmiyor'}
Durum: ${doc.embeddings_created ? 'Hazır' : 'İşleniyor'}

İçerik Önizleme:
${doc.content_preview || 'Önizleme mevcut değil'}
        `;
        
        alert(details);
      } else {
        alert('Doküman detayları alınamadı.');
      }
    } catch (error) {
      alert(`Detaylar alınırken hata: ${error.message}`);
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
                          {message.type === 'ai' ? (
                            <div className="prose prose-sm max-w-none">
                              <ReactMarkdown
                                components={{
                                  // Başlıkları özelleştir
                                  h1: ({children}) => <h1 className="text-lg font-bold text-gray-900 mb-2">{children}</h1>,
                                  h2: ({children}) => <h2 className="text-base font-bold text-gray-900 mb-2">{children}</h2>,
                                  h3: ({children}) => <h3 className="text-sm font-bold text-gray-900 mb-1">{children}</h3>,
                                  // Kalın metinleri özelleştir
                                  strong: ({children}) => <strong className="font-bold text-gray-900">{children}</strong>,
                                  // Paragrafları özelleştir
                                  p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                                  // Listeleri özelleştir
                                  ul: ({children}) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                                  ol: ({children}) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                                  li: ({children}) => <li className="text-gray-900">{children}</li>,
                                }}
                              >
                                {message.content}
                              </ReactMarkdown>
                            </div>
                          ) : (
                            <p className="whitespace-pre-wrap">{message.content}</p>
                          )}
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
                    
                    {systemStatus.supported_formats && (
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Desteklenen Formatlar</span>
                        <span className="text-xs font-medium text-gray-700">
                          {systemStatus.supported_formats.join(', ').toUpperCase()}
                        </span>
                      </div>
                    )}
                    
                    {systemStatus.processing_queue !== undefined && (
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">İşlem Kuyruğu</span>
                        <span className={`font-semibold ${
                          systemStatus.processing_queue > 0 ? 'text-orange-600' : 'text-gray-600'
                        }`}>
                          {systemStatus.processing_queue}
                        </span>
                      </div>
                    )}
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
              
              {/* Grup Seçimi */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Yüklenecek Grup:
                </label>
                <select
                  value={selectedGroup}
                  onChange={(e) => setSelectedGroup(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="all">Grup seçmeden yükle</option>
                  {groups.map((group) => (
                    <option key={group.id} value={group.id}>
                      📁 {group.name} ({group.document_count} doküman)
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                <div className="space-y-4">
                  <div className="flex flex-col items-center space-y-3">
                    <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-2xl">📄</span>
                    </div>
                    <div>
                      <p className="text-lg font-medium text-gray-900">Word Dokümanı Yükleyin</p>
                      <p className="text-gray-600">.doc ve .docx formatları desteklenir (Maksimum 10MB)</p>
                    </div>
                  </div>
                  
                  <div className="flex flex-col sm:flex-row items-center justify-center space-y-2 sm:space-y-0 sm:space-x-4">
                    <input
                      id="fileInput"
                      type="file"
                      accept=".doc,.docx"
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

            {/* Grup Yönetimi */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold text-gray-900">📁 Grup Yönetimi</h2>
                <div className="space-x-2">
                  <button
                    onClick={() => setShowGroupModal(true)}
                    className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
                  >
                    ➕ Yeni Grup
                  </button>
                  {selectedDocuments.length > 0 && (
                    <button
                      onClick={() => setShowMoveModal(true)}
                      className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                    >
                      📂 Taşı ({selectedDocuments.length})
                    </button>
                  )}
                </div>
              </div>

              {/* Grup Filtreleri */}
              <div className="flex flex-wrap gap-2 mb-4">
                <button
                  onClick={() => {setSelectedGroup('all'); fetchDocuments();}}
                  className={`px-3 py-1 rounded-full text-sm ${
                    selectedGroup === 'all'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  📋 Tümü ({documents.length})
                </button>
                <button
                  onClick={() => {setSelectedGroup('ungrouped'); fetchDocuments();}}
                  className={`px-3 py-1 rounded-full text-sm ${
                    selectedGroup === 'ungrouped'
                      ? 'bg-gray-500 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  📄 Gruplandırılmamış
                </button>
                {groups.map((group) => (
                  <button
                    key={group.id}
                    onClick={() => {setSelectedGroup(group.id); fetchDocuments();}}
                    className={`px-3 py-1 rounded-full text-sm flex items-center space-x-1 ${
                      selectedGroup === group.id
                        ? 'text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                    style={{
                      backgroundColor: selectedGroup === group.id ? group.color : undefined
                    }}
                  >
                    <span>📁</span>
                    <span>{group.name} ({group.document_count})</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteGroup(group.id, group.name);
                      }}
                      className="ml-1 text-red-500 hover:text-red-700"
                      title="Grubu Sil"
                    >
                      ❌
                    </button>
                  </button>
                ))}
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
                        <div className="flex items-start space-x-2 flex-1 min-w-0">
                          <input
                            type="checkbox"
                            checked={selectedDocuments.includes(doc.id)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedDocuments([...selectedDocuments, doc.id]);
                              } else {
                                setSelectedDocuments(selectedDocuments.filter(id => id !== doc.id));
                              }
                            }}
                            className="mt-1 flex-shrink-0"
                          />
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start space-x-2 mb-2">
                              <span className="text-lg flex-shrink-0">
                                {doc.file_type === '.doc' ? '📄' : '📝'}
                              </span>
                              <div className="flex-1 min-w-0">
                                <h3 
                                  className="text-sm font-medium text-gray-900 leading-tight break-words"
                                  title={doc.filename}
                                  style={{
                                    display: '-webkit-box',
                                    WebkitLineClamp: 2,
                                    WebkitBoxOrient: 'vertical',
                                    overflow: 'hidden',
                                    wordBreak: 'break-word',
                                    hyphens: 'auto'
                                  }}
                                >
                                  {doc.filename}
                                </h3>
                              </div>
                            </div>
                            
                            {/* Grup Bilgisi */}
                            {doc.group_name && (
                              <div className="mb-2">
                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-50 text-blue-700 max-w-full">
                                  <span className="flex-shrink-0">📁</span>
                                  <span className="ml-1 truncate">{doc.group_name}</span>
                                </span>
                              </div>
                            )}
                            
                            <div className="space-y-1 text-xs text-gray-600">
                              <div className="flex justify-between">
                                <span className="flex-shrink-0">Format:</span>
                                <span className="font-medium">{doc.file_type?.toUpperCase()}</span>
                              </div>
                              
                              <div className="flex justify-between">
                                <span className="flex-shrink-0">Boyut:</span>
                                <span className="font-medium">{doc.file_size_human || 'Bilinmiyor'}</span>
                              </div>
                              
                              <div className="flex justify-between">
                                <span className="flex-shrink-0">Parçalar:</span>
                                <span className="font-medium">{doc.chunk_count || 0}</span>
                              </div>
                              
                              <div className="flex justify-between">
                                <span className="flex-shrink-0">Tarih:</span>
                                <span className="font-medium text-right">
                                  {doc.created_at ? new Date(doc.created_at).toLocaleDateString('tr-TR', {
                                    day: '2-digit',
                                    month: '2-digit',
                                    year: '2-digit'
                                  }) : 'Bilinmiyor'}
                                </span>
                              </div>
                              
                              <div className="flex justify-between items-center">
                                <span className="flex-shrink-0">Durum:</span>
                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                  doc.embeddings_created 
                                    ? 'bg-green-100 text-green-800' 
                                    : doc.upload_status === 'failed'
                                    ? 'bg-red-100 text-red-800'
                                    : 'bg-yellow-100 text-yellow-800'
                                }`}>
                                  {doc.embeddings_created ? '✓ Hazır' : 
                                   doc.upload_status === 'failed' ? '✗ Hata' : '⏳ İşleniyor'}
                                </span>
                              </div>
                              
                              {doc.processing_time && (
                                <div className="flex justify-between">
                                  <span className="flex-shrink-0">İşlem:</span>
                                  <span className="font-medium">{doc.processing_time}</span>
                                </div>
                              )}
                              
                              {doc.error_message && (
                                <div className="mt-2 p-2 bg-red-50 rounded text-red-700 text-xs break-words">
                                  <strong>Hata:</strong> {doc.error_message}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                        
                        <div className="ml-2 flex flex-col space-y-1 flex-shrink-0">
                          <button
                            onClick={() => handleDeleteDocument(doc.id)}
                            className="p-1 text-red-500 hover:bg-red-50 rounded transition-colors"
                            title="Dokümanı Sil"
                          >
                            🗑️
                          </button>
                          
                          <button
                            onClick={() => handleViewDocument(doc.id)}
                            className="p-1 text-blue-500 hover:bg-blue-50 rounded transition-colors"
                            title="Detayları Görüntüle"
                          >
                            👁️
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Yeni Grup Modal */}
      {showGroupModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">📁 Yeni Grup Oluştur</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Grup Adı *
                </label>
                <input
                  type="text"
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="İnsan Kaynakları, Finans, vb."
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Açıklama
                </label>
                <textarea
                  value={newGroupDescription}
                  onChange={(e) => setNewGroupDescription(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows="3"
                  placeholder="Grubun amacını açıklayın..."
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Renk
                </label>
                <input
                  type="color"
                  value={newGroupColor}
                  onChange={(e) => setNewGroupColor(e.target.value)}
                  className="w-20 h-10 border border-gray-300 rounded-lg"
                />
              </div>
            </div>
            
            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => {
                  setShowGroupModal(false);
                  setNewGroupName('');
                  setNewGroupDescription('');
                  setNewGroupColor('#3b82f6');
                }}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                İptal
              </button>
              <button
                onClick={handleCreateGroup}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                Oluştur
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Doküman Taşıma Modal */}
      {showMoveModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              📂 Dokümanları Taşı ({selectedDocuments.length} adet)
            </h3>
            
            <div className="space-y-2 max-h-60 overflow-y-auto">
              <button
                onClick={() => handleMoveDocuments(null)}
                className="w-full text-left px-3 py-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                📄 Gruplandırılmamış
              </button>
              
              {groups.map((group) => (
                <button
                  key={group.id}
                  onClick={() => handleMoveDocuments(group.id)}
                  className="w-full text-left px-3 py-2 hover:bg-gray-100 rounded-lg transition-colors flex items-center space-x-2"
                >
                  <div
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: group.color }}
                  ></div>
                  <span>📁 {group.name} ({group.document_count})</span>
                </button>
              ))}
            </div>
            
            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => {
                  setShowMoveModal(false);
                  setSelectedDocuments([]);
                }}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                İptal
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;