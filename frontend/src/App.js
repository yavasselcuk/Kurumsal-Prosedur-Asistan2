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
  
  // Soru geçmişi için yeni state'ler
  const [chatSessions, setChatSessions] = useState([]);
  const [recentQuestions, setRecentQuestions] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [selectedSession, setSelectedSession] = useState(null);
  
  // Soru önerisi için yeni state'ler
  const [questionSuggestions, setQuestionSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  
  // Favori sorular için yeni state'ler
  const [favoriteQuestions, setFavoriteQuestions] = useState([]);
  const [loadingFavorites, setLoadingFavorites] = useState(false);
  const [favoriteCategories, setFavoriteCategories] = useState([]);
  const [favoriteTags, setFavoriteTags] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedTag, setSelectedTag] = useState('all');
  
  // FAQ için yeni state'ler
  const [faqItems, setFaqItems] = useState([]);
  const [loadingFaq, setLoadingFaq] = useState(false);
  const [faqCategories, setFaqCategories] = useState([]);
  const [selectedFaqCategory, setSelectedFaqCategory] = useState('all');
  const [faqAnalytics, setFaqAnalytics] = useState(null);
  const [generatingFaq, setGeneratingFaq] = useState(false);
  
  // PDF Viewer için yeni state'ler
  const [showPdfModal, setShowPdfModal] = useState(false);
  const [currentPdfDocument, setCurrentPdfDocument] = useState(null);
  const [pdfMetadata, setPdfMetadata] = useState(null);
  const [loadingPdf, setLoadingPdf] = useState(false);
  const [pdfError, setPdfError] = useState(null);
  
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
    // Soru geçmişini al
    fetchChatSessions();
    // Son soruları al
    fetchRecentQuestions();
    // Favori soruları al
    fetchFavoriteQuestions();
    // FAQ'ları al
    fetchFaqItems();
    // FAQ analytics'i al
    fetchFaqAnalytics();
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

  // Soru geçmişi fonksiyonları
  const fetchChatSessions = async () => {
    setLoadingHistory(true);
    try {
      const response = await fetch(`${backendUrl}/api/chat-sessions?limit=20`);
      const data = await response.json();
      setChatSessions(data.sessions || []);
    } catch (error) {
      console.error('Chat geçmişi alınamadı:', error);
    } finally {
      setLoadingHistory(false);
    }
  };

  const fetchRecentQuestions = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/recent-questions?limit=10`);
      const data = await response.json();
      setRecentQuestions(data.recent_questions || []);
    } catch (error) {
      console.error('Son sorular alınamadı:', error);
    }
  };

  const handleReplayQuestion = async (sessionId, question) => {
    try {
      setIsLoading(true);
      
      const response = await fetch(`${backendUrl}/api/replay-question`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          question: question
        })
      });

      const data = await response.json();

      if (response.ok) {
        // Yeni cevabı chat geçmişine ekle
        const userMessage = {
          type: 'user',
          content: question,
          timestamp: new Date().toLocaleTimeString('tr-TR')
        };

        const aiMessage = {
          type: 'ai',
          content: data.result.answer,
          contextFound: data.result.context_found,
          chunksCount: data.result.context_chunks_count,
          timestamp: new Date().toLocaleTimeString('tr-TR')
        };

        setChatHistory([userMessage, aiMessage]);
        setActiveTab('chat'); // Chat tab'ına geç
        
        // Session'ı güncelle
        setSessionId(data.result.session_id);
        
        // Geçmişi yenile
        fetchChatSessions();
        
      } else {
        alert(`Hata: ${data.detail || 'Bilinmeyen hata'}`);
      }
    } catch (error) {
      alert(`Soru tekrar çalıştırılırken hata: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const viewSessionHistory = async (sessionId) => {
    try {
      const response = await fetch(`${backendUrl}/api/chat-history/${sessionId}`);
      const data = await response.json();
      
      if (response.ok) {
        // Session geçmişini chat formatına çevir
        const sessionChat = [];
        data.chat_history.forEach(chat => {
          sessionChat.push({
            type: 'user',
            content: chat.question,
            timestamp: new Date(chat.created_at).toLocaleTimeString('tr-TR')
          });
          sessionChat.push({
            type: 'ai',
            content: chat.answer,
            contextFound: true,
            chunksCount: chat.context_chunks?.length || 0,
            timestamp: new Date(chat.created_at).toLocaleTimeString('tr-TR')
          });
        });
        
        setChatHistory(sessionChat);
        setSelectedSession(sessionId);
        setActiveTab('chat'); // Chat tab'ına geç
      } else {
        alert('Session geçmişi alınamadı.');
      }
    } catch (error) {
      alert(`Geçmiş görüntülenirken hata: ${error.message}`);
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

  // Soru önerisi fonksiyonları
  const fetchQuestionSuggestions = async (query) => {
    if (!query || query.length < 3) {
      setQuestionSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    setLoadingSuggestions(true);
    try {
      const response = await fetch(`${backendUrl}/api/suggest-questions?q=${encodeURIComponent(query)}&limit=5`);
      const data = await response.json();
      
      if (response.ok) {
        setQuestionSuggestions(data.suggestions || []);
        setShowSuggestions(data.suggestions.length > 0);
      } else {
        setQuestionSuggestions([]);
        setShowSuggestions(false);
      }
    } catch (error) {
      console.error('Soru önerisi alınamadı:', error);
      setQuestionSuggestions([]);
      setShowSuggestions(false);
    } finally {
      setLoadingSuggestions(false);
    }
  };

  // Debounced suggestion fetching
  const debouncedFetchSuggestions = React.useCallback(
    (() => {
      let timeoutId;
      return (query) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
          fetchQuestionSuggestions(query);
        }, 300); // 300ms delay
      };
    })(),
    []
  );

  const handleQuestionChange = (e) => {
    const value = e.target.value;
    setQuestion(value);
    
    // Soru önerilerini getir (debounced)
    debouncedFetchSuggestions(value);
  };

  const handleSuggestionSelect = (suggestion) => {
    setQuestion(suggestion.text);
    setShowSuggestions(false);
    setQuestionSuggestions([]);
    
    // Optional: Soruyu otomatik gönder
    // handleQuestionSubmit(new Event('submit'));
  };

  const hideSuggestions = () => {
    // Biraz gecikme ile gizle (click event'ini kaçırmamak için)
    setTimeout(() => {
      setShowSuggestions(false);
    }, 150);
  };

  // Favori sorular fonksiyonları
  const fetchFavoriteQuestions = async () => {
    setLoadingFavorites(true);
    try {
      let url = `${backendUrl}/api/favorites?limit=50`;
      if (selectedCategory && selectedCategory !== 'all') {
        url += `&category=${encodeURIComponent(selectedCategory)}`;
      }
      if (selectedTag && selectedTag !== 'all') {
        url += `&tag=${encodeURIComponent(selectedTag)}`;
      }

      const response = await fetch(url);
      const data = await response.json();
      
      if (response.ok) {
        setFavoriteQuestions(data.favorites || []);
        setFavoriteCategories(data.statistics?.available_categories || []);
        setFavoriteTags(data.statistics?.available_tags || []);
      } else {
        console.error('Favoriler alınamadı:', data);
      }
    } catch (error) {
      console.error('Favoriler alınamadı:', error);
    } finally {
      setLoadingFavorites(false);
    }
  };

  const addToFavorites = async (message) => {
    try {
      const response = await fetch(`${backendUrl}/api/favorites`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          question: message.originalQuestion || message.content,
          answer: message.content,
          source_documents: message.sourceDocuments || []
        })
      });

      const data = await response.json();

      if (response.ok) {
        alert(data.message);
        if (!data.already_exists) {
          // Favoriler listesini yenile
          fetchFavoriteQuestions();
        }
      } else {
        alert(`Hata: ${data.detail || 'Bilinmeyen hata'}`);
      }
    } catch (error) {
      alert(`Favoriye eklenirken hata: ${error.message}`);
    }
  };

  const replayFavoriteQuestion = async (favoriteId, question) => {
    try {
      setIsLoading(true);
      
      const response = await fetch(`${backendUrl}/api/favorites/${favoriteId}/replay`, {
        method: 'POST'
      });

      const data = await response.json();

      if (response.ok) {
        // Yeni cevabı chat geçmişine ekle
        const userMessage = {
          type: 'user',
          content: question,
          timestamp: new Date().toLocaleTimeString('tr-TR')
        };

        const aiMessage = {
          type: 'ai',
          content: data.result.answer,
          contextFound: data.result.context_found,
          chunksCount: data.result.context_chunks_count,
          timestamp: new Date().toLocaleTimeString('tr-TR')
        };

        setChatHistory([userMessage, aiMessage]);
        setActiveTab('chat'); // Chat tab'ına geç
        
        // Session'ı güncelle
        setSessionId(data.result.session_id);
        
      } else {
        alert(`Hata: ${data.detail || 'Bilinmeyen hata'}`);
      }
    } catch (error) {
      alert(`Favori soru tekrar çalıştırılırken hata: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const deleteFavorite = async (favoriteId) => {
    if (!window.confirm('Bu favori soruyu silmek istediğinizden emin misiniz?')) {
      return;
    }

    try {
      const response = await fetch(`${backendUrl}/api/favorites/${favoriteId}`, {
        method: 'DELETE'
      });

      const data = await response.json();

      if (response.ok) {
        alert(data.message);
        fetchFavoriteQuestions(); // Listeyi yenile
      } else {
        alert(`Hata: ${data.detail || 'Bilinmeyen hata'}`);
      }
    } catch (error) {
      alert(`Favori silinirken hata: ${error.message}`);
    }
  };

  // FAQ fonksiyonları
  const fetchFaqItems = async () => {
    setLoadingFaq(true);
    try {
      let url = `${backendUrl}/api/faq?limit=50`;
      if (selectedFaqCategory && selectedFaqCategory !== 'all') {
        url += `&category=${encodeURIComponent(selectedFaqCategory)}`;
      }

      const response = await fetch(url);
      const data = await response.json();
      
      if (response.ok) {
        setFaqItems(data.faq_items || []);
        setFaqCategories(data.statistics?.available_categories || []);
      } else {
        console.error('FAQ alınamadı:', data);
      }
    } catch (error) {
      console.error('FAQ alınamadı:', error);
    } finally {
      setLoadingFaq(false);
    }
  };

  const fetchFaqAnalytics = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/faq/analytics`);
      const data = await response.json();
      
      if (response.ok) {
        setFaqAnalytics(data);
      } else {
        console.error('FAQ analytics alınamadı:', data);
      }
    } catch (error) {
      console.error('FAQ analytics alınamadı:', error);
    }
  };

  const generateFaq = async () => {
    if (!window.confirm('Mevcut chat geçmişinden otomatik FAQ oluşturulsun mu? Bu işlem biraz sürebilir.')) {
      return;
    }

    setGeneratingFaq(true);
    try {
      const response = await fetch(`${backendUrl}/api/faq/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          min_frequency: 2,
          similarity_threshold: 0.7,
          max_faq_items: 50
        })
      });

      const data = await response.json();

      if (response.ok) {
        alert(data.message);
        fetchFaqItems(); // FAQ listesini yenile
        fetchFaqAnalytics(); // Analytics'i yenile
      } else {
        alert(`Hata: ${data.detail || 'Bilinmeyen hata'}`);
      }
    } catch (error) {
      alert(`FAQ oluşturulurken hata: ${error.message}`);
    } finally {
      setGeneratingFaq(false);
    }
  };

  const askFaqQuestion = async (faqId, question) => {
    try {
      setIsLoading(true);
      
      const response = await fetch(`${backendUrl}/api/faq/${faqId}/ask`, {
        method: 'POST'
      });

      const data = await response.json();

      if (response.ok) {
        // Yeni cevabı chat geçmişine ekle
        const userMessage = {
          type: 'user',
          content: question,
          timestamp: new Date().toLocaleTimeString('tr-TR')
        };

        const aiMessage = {
          type: 'ai',
          content: data.result.answer,
          contextFound: data.result.context_found,
          chunksCount: data.result.context_chunks_count,
          timestamp: new Date().toLocaleTimeString('tr-TR')
        };

        setChatHistory([userMessage, aiMessage]);
        setActiveTab('chat'); // Chat tab'ına geç
        
        // Session'ı güncelle
        setSessionId(data.result.session_id);
        
      } else {
        alert(`Hata: ${data.detail || 'Bilinmeyen hata'}`);
      }
    } catch (error) {
      alert(`FAQ sorusu sorulurken hata: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
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
            onClick={() => {
              setActiveTab('history');
              fetchChatSessions(); // Geçmişi yenile
            }}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'history'
                ? 'bg-blue-500 text-white shadow-sm'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            📜 Soru Geçmişi
          </button>
          <button
            onClick={() => {
              setActiveTab('favorites');
              fetchFavoriteQuestions(); // Favorileri yenile
            }}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'favorites'
                ? 'bg-blue-500 text-white shadow-sm'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            ⭐ Favorilerim
          </button>
          <button
            onClick={() => {
              setActiveTab('faq');
              fetchFaqItems(); // FAQ'ları yenile
              fetchFaqAnalytics(); // Analytics'i yenile
            }}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'faq'
                ? 'bg-blue-500 text-white shadow-sm'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            ❓ Sık Sorular
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
                                  // Linkleri özelleştir
                                  a: ({href, children}) => {
                                    // API linklerini özel işle
                                    if (href && href.startsWith('/api/documents/')) {
                                      return (
                                        <button
                                          onClick={() => {
                                            const docId = href.replace('/api/documents/', '');
                                            handleViewDocument(docId);
                                          }}
                                          className="text-blue-600 hover:text-blue-800 underline font-medium cursor-pointer"
                                        >
                                          {children}
                                        </button>
                                      );
                                    }
                                    // Normal linkler
                                    return (
                                      <a 
                                        href={href} 
                                        target="_blank" 
                                        rel="noopener noreferrer"
                                        className="text-blue-600 hover:text-blue-800 underline"
                                      >
                                        {children}
                                      </a>
                                    );
                                  },
                                  // Horizontal rule için
                                  hr: () => <hr className="my-4 border-gray-300" />
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
                            <div className="flex items-center space-x-2">
                              {message.type === 'ai' && message.contextFound && (
                                <span className="bg-white bg-opacity-20 px-2 py-1 rounded">
                                  {message.chunksCount} kaynak kullanıldı
                                </span>
                              )}
                              {message.type === 'ai' && (
                                <button
                                  onClick={() => {
                                    // Önceki kullanıcı sorusunu bul
                                    const currentIndex = chatHistory.indexOf(message);
                                    const previousMessage = currentIndex > 0 ? chatHistory[currentIndex - 1] : null;
                                    const originalQuestion = previousMessage && previousMessage.type === 'user' 
                                      ? previousMessage.content 
                                      : 'Bilinmeyen soru';
                                    
                                    // Mesaja ek bilgi ekle
                                    const messageWithQuestion = {
                                      ...message,
                                      originalQuestion: originalQuestion
                                    };
                                    
                                    addToFavorites(messageWithQuestion);
                                  }}
                                  className="bg-white bg-opacity-20 hover:bg-opacity-30 px-2 py-1 rounded transition-colors"
                                  title="Favoriye Ekle"
                                >
                                  ⭐
                                </button>
                              )}
                            </div>
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
                  <form onSubmit={handleQuestionSubmit} className="relative">
                    <div className="flex space-x-4">
                      <div className="flex-1 relative">
                        <input
                          type="text"
                          value={question}
                          onChange={handleQuestionChange}
                          onFocus={() => {
                            if (questionSuggestions.length > 0) {
                              setShowSuggestions(true);
                            }
                          }}
                          onBlur={hideSuggestions}
                          placeholder="Prosedürler hakkında soru sorun..."
                          disabled={isLoading}
                          className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                        />
                        
                        {/* Soru Önerileri Dropdown */}
                        {showSuggestions && (questionSuggestions.length > 0 || loadingSuggestions) && (
                          <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
                            {loadingSuggestions ? (
                              <div className="p-3 text-center text-gray-500">
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500 mx-auto mb-2"></div>
                                Öneriler yükleniyor...
                              </div>
                            ) : (
                              <div className="py-1">
                                <div className="px-3 py-2 text-xs font-medium text-gray-500 bg-gray-50 border-b">
                                  💡 Soru Önerileri
                                </div>
                                {questionSuggestions.map((suggestion, index) => (
                                  <button
                                    key={index}
                                    type="button"
                                    onClick={() => handleSuggestionSelect(suggestion)}
                                    className="w-full text-left px-3 py-2 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
                                  >
                                    <div className="flex items-start space-x-2">
                                      <span className="text-sm mt-0.5">{suggestion.icon}</span>
                                      <div className="flex-1 min-w-0">
                                        <p className="text-sm text-gray-900 line-clamp-2">
                                          {suggestion.text}
                                        </p>
                                        <div className="flex items-center space-x-2 mt-1">
                                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs ${
                                            suggestion.type === 'similar' ? 'bg-blue-100 text-blue-800' :
                                            suggestion.type === 'partial' ? 'bg-green-100 text-green-800' :
                                            'bg-purple-100 text-purple-800'
                                          }`}>
                                            {suggestion.type === 'similar' ? 'Benzer' :
                                             suggestion.type === 'partial' ? 'Kısmi' : 'Önerilen'}
                                          </span>
                                          <span className="text-xs text-gray-500">
                                            {Math.round(suggestion.similarity * 100)}% uyumlu
                                          </span>
                                        </div>
                                      </div>
                                    </div>
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      <button
                        type="submit"
                        disabled={isLoading || !question.trim()}
                        className="px-6 py-3 bg-blue-500 text-white rounded-xl hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
                      >
                        <span>Gönder</span>
                        <span>🚀</span>
                      </button>
                    </div>
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
        ) : activeTab === 'history' ? (
          /* History Tab */
          <div className="space-y-6">
            {/* Soru Geçmişi Header */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold text-gray-900">📜 Soru Geçmişi</h2>
                <button
                  onClick={fetchChatSessions}
                  disabled={loadingHistory}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 transition-colors"
                >
                  🔄 {loadingHistory ? 'Yükleniyor...' : 'Yenile'}
                </button>
              </div>

              {/* Son Sorular Hızlı Erişim */}
              {recentQuestions.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-3">⚡ Son Sorularım</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {recentQuestions.slice(0, 6).map((question, index) => (
                      <div
                        key={index}
                        className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors"
                        onClick={() => handleReplayQuestion(question.session_id, question.question)}
                      >
                        <p className="text-sm text-gray-900 line-clamp-2">{question.question}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(question.created_at).toLocaleDateString('tr-TR')}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Chat Sessions Listesi */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">📋 Tüm Konuşmalarım</h3>
              
              {loadingHistory ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                  <p className="text-gray-600">Geçmiş yükleniyor...</p>
                </div>
              ) : chatSessions.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span className="text-2xl">📜</span>
                  </div>
                  <p className="text-gray-600">Henüz soru geçmişiniz bulunmuyor.</p>
                  <p className="text-gray-500 text-sm mt-1">Sorular sordukça burada görünecek.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {chatSessions.map((session, index) => (
                    <div
                      key={session.session_id}
                      className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1">
                          <h4 className="font-medium text-gray-900 mb-1">
                            {session.latest_question}
                          </h4>
                          <p className="text-sm text-gray-600 line-clamp-2">
                            {session.latest_answer}...
                          </p>
                        </div>
                        <div className="flex flex-col items-end space-y-2 ml-4">
                          <span className="text-xs text-gray-500">
                            {new Date(session.latest_created_at).toLocaleDateString('tr-TR')}
                          </span>
                          {session.has_sources && (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">
                              📚 Kaynaklı
                            </span>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex justify-between items-center">
                        <div className="flex items-center space-x-4 text-sm text-gray-500">
                          <span>💬 {session.message_count} mesaj</span>
                          {session.source_documents && session.source_documents.length > 0 && (
                            <span>📄 {session.source_documents.length} kaynak</span>
                          )}
                        </div>
                        
                        <div className="flex space-x-2">
                          <button
                            onClick={() => handleReplayQuestion(session.session_id, session.latest_question)}
                            className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
                          >
                            🔄 Tekrar Sor
                          </button>
                          <button
                            onClick={() => viewSessionHistory(session.session_id)}
                            className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
                          >
                            👁️ Görüntüle
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : activeTab === 'favorites' ? (
          /* Favorites Tab */
          <div className="space-y-6">
            {/* Favoriler Header */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold text-gray-900">⭐ Favori Sorularım</h2>
                <div className="flex space-x-2">
                  <button
                    onClick={fetchFavoriteQuestions}
                    disabled={loadingFavorites}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 transition-colors"
                  >
                    🔄 {loadingFavorites ? 'Yükleniyor...' : 'Yenile'}
                  </button>
                </div>
              </div>

              {/* Filtreler */}
              <div className="flex flex-wrap gap-4 mb-6">
                {/* Kategori Filtresi */}
                <div className="flex-1 min-w-48">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Kategori</label>
                  <select
                    value={selectedCategory}
                    onChange={(e) => {
                      setSelectedCategory(e.target.value);
                      // Yeni filtre ile favorileri yenile
                      setTimeout(() => fetchFavoriteQuestions(), 100);
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="all">Tüm Kategoriler</option>
                    {favoriteCategories.map((category, index) => (
                      <option key={index} value={category}>{category}</option>
                    ))}
                  </select>
                </div>

                {/* Etiket Filtresi */}
                <div className="flex-1 min-w-48">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Etiket</label>
                  <select
                    value={selectedTag}
                    onChange={(e) => {
                      setSelectedTag(e.target.value);
                      // Yeni filtre ile favorileri yenile
                      setTimeout(() => fetchFavoriteQuestions(), 100);
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="all">Tüm Etiketler</option>
                    {favoriteTags.map((tag, index) => (
                      <option key={index} value={tag}>{tag}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Favori Sorular Listesi */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">💝 Kayıtlı Favorilerim</h3>
              
              {loadingFavorites ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                  <p className="text-gray-600">Favoriler yükleniyor...</p>
                </div>
              ) : favoriteQuestions.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span className="text-2xl">⭐</span>
                  </div>
                  <p className="text-gray-600">Henüz favori sorunuz bulunmuyor.</p>
                  <p className="text-gray-500 text-sm mt-1">Beğendiğiniz cevapları favorilere ekleyerek burada kolayca erişebilirsiniz.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {favoriteQuestions.map((favorite, index) => (
                    <div
                      key={favorite.id}
                      className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1">
                          <h4 className="font-medium text-gray-900 mb-1">
                            {favorite.question}
                          </h4>
                          <p className="text-sm text-gray-600 line-clamp-2 mb-2">
                            {favorite.answer_preview}
                          </p>
                          
                          {/* Etiketler ve Kategori */}
                          <div className="flex flex-wrap gap-2 mb-2">
                            {favorite.category && (
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800">
                                📁 {favorite.category}
                              </span>
                            )}
                            {favorite.tags && favorite.tags.map((tag, tagIndex) => (
                              <span 
                                key={tagIndex}
                                className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-purple-100 text-purple-800"
                              >
                                🏷️ {tag}
                              </span>
                            ))}
                            {favorite.source_documents && favorite.source_documents.length > 0 && (
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">
                                📚 {favorite.source_documents.length} kaynak
                              </span>
                            )}
                          </div>
                        </div>
                        
                        <div className="flex flex-col items-end space-y-2 ml-4">
                          <span className="text-xs text-gray-500">
                            {new Date(favorite.created_at).toLocaleDateString('tr-TR')}
                          </span>
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-yellow-100 text-yellow-800">
                            ⭐ {favorite.favorite_count}
                          </span>
                        </div>
                      </div>
                      
                      {/* Notlar */}
                      {favorite.notes && (
                        <div className="mb-3 p-2 bg-yellow-50 rounded border-l-4 border-yellow-200">
                          <p className="text-sm text-gray-700">
                            <span className="font-medium">📝 Not:</span> {favorite.notes}
                          </p>
                        </div>
                      )}
                      
                      <div className="flex justify-between items-center">
                        <div className="flex items-center space-x-4 text-sm text-gray-500">
                          {favorite.last_accessed && (
                            <span>👁️ Son erişim: {new Date(favorite.last_accessed).toLocaleDateString('tr-TR')}</span>
                          )}
                        </div>
                        
                        <div className="flex space-x-2">
                          <button
                            onClick={() => replayFavoriteQuestion(favorite.id, favorite.question)}
                            className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
                          >
                            🔄 Tekrar Sor
                          </button>
                          <button
                            onClick={() => deleteFavorite(favorite.id)}
                            className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
                          >
                            🗑️ Sil
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : activeTab === 'faq' ? (
          /* FAQ Tab */
          <div className="space-y-6">
            {/* FAQ Header ve Analytics */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold text-gray-900">❓ Sık Sorulan Sorular</h2>
                <div className="flex space-x-2">
                  <button
                    onClick={generateFaq}
                    disabled={generatingFaq}
                    className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 transition-colors"
                  >
                    🤖 {generatingFaq ? 'Oluşturuluyor...' : 'Otomatik FAQ Oluştur'}
                  </button>
                  <button
                    onClick={() => {
                      fetchFaqItems();
                      fetchFaqAnalytics();
                    }}
                    disabled={loadingFaq}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 transition-colors"
                  >
                    🔄 {loadingFaq ? 'Yükleniyor...' : 'Yenile'}
                  </button>
                </div>
              </div>

              {/* FAQ Analytics */}
              {faqAnalytics && (
                <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                  <h3 className="text-lg font-medium text-gray-900 mb-3">📊 FAQ Analytics</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-600">{faqAnalytics.total_questions_analyzed}</div>
                      <div className="text-sm text-gray-600">Toplam Soru</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">{faqAnalytics.total_chat_sessions}</div>
                      <div className="text-sm text-gray-600">Chat Session</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-600">{faqAnalytics.faq_recommendations?.potential_faq_count}</div>
                      <div className="text-sm text-gray-600">Potansiyel FAQ</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-orange-600">{Object.keys(faqAnalytics.category_distribution || {}).length}</div>
                      <div className="text-sm text-gray-600">Kategori</div>
                    </div>
                  </div>
                  
                  {/* Top Questions Preview */}
                  {faqAnalytics.top_questions && faqAnalytics.top_questions.length > 0 && (
                    <div className="mt-4">
                      <h4 className="font-medium text-gray-900 mb-2">🔥 En Sık Sorulananlar:</h4>
                      <div className="space-y-1">
                        {faqAnalytics.top_questions.slice(0, 3).map((question, index) => (
                          <div key={index} className="flex justify-between items-center text-sm">
                            <span className="text-gray-700 line-clamp-1">{question[0]}</span>
                            <span className="text-blue-600 font-medium">{question[1]}x</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Kategori Filtresi */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">Kategori Filtresi</label>
                <select
                  value={selectedFaqCategory}
                  onChange={(e) => {
                    setSelectedFaqCategory(e.target.value);
                    // Filtreyi uygula
                    setTimeout(() => fetchFaqItems(), 100);
                  }}
                  className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="all">Tüm Kategoriler</option>
                  {faqCategories.map((category, index) => (
                    <option key={index} value={category}>{category}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* FAQ Listesi */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">📋 FAQ Listesi</h3>
              
              {loadingFaq ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                  <p className="text-gray-600">FAQ yükleniyor...</p>
                </div>
              ) : faqItems.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span className="text-2xl">❓</span>
                  </div>
                  <p className="text-gray-600">Henüz FAQ bulunmuyor.</p>
                  <p className="text-gray-500 text-sm mt-1">
                    Otomatik FAQ oluşturmak için yukarıdaki "🤖 Otomatik FAQ Oluştur" butonunu kullanın.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {faqItems.map((faq, index) => (
                    <div
                      key={faq.id}
                      className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1">
                          <h4 className="font-medium text-gray-900 mb-2">
                            {faq.question}
                          </h4>
                          <div className="prose prose-sm max-w-none text-gray-600 mb-3">
                            {faq.answer && (
                              <p className="line-clamp-3">
                                {faq.answer.length > 300 ? faq.answer.substring(0, 300) + '...' : faq.answer}
                              </p>
                            )}
                          </div>
                          
                          {/* Benzer Sorular */}
                          {faq.similar_questions && faq.similar_questions.length > 0 && (
                            <div className="mb-3">
                              <h5 className="text-sm font-medium text-gray-700 mb-1">🔗 Benzer Sorular:</h5>
                              <div className="flex flex-wrap gap-2">
                                {faq.similar_questions.slice(0, 3).map((simQ, simIndex) => (
                                  <span 
                                    key={simIndex}
                                    className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded"
                                  >
                                    {simQ.length > 50 ? simQ.substring(0, 50) + '...' : simQ}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                          
                          {/* Meta Bilgiler */}
                          <div className="flex flex-wrap gap-2 mb-2">
                            {faq.category && (
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800">
                                📁 {faq.category}
                              </span>
                            )}
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">
                              🔥 {faq.frequency} kez soruldu
                            </span>
                            {faq.manual_override && (
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-purple-100 text-purple-800">
                                ✋ Manuel
                              </span>
                            )}
                          </div>
                        </div>
                        
                        <div className="flex flex-col items-end space-y-2 ml-4">
                          <span className="text-xs text-gray-500">
                            {new Date(faq.created_at).toLocaleDateString('tr-TR')}
                          </span>
                        </div>
                      </div>
                      
                      <div className="flex justify-between items-center pt-3 border-t border-gray-100">
                        <div className="flex items-center space-x-4 text-sm text-gray-500">
                          {faq.last_updated && (
                            <span>🕒 Son güncelleme: {new Date(faq.last_updated).toLocaleDateString('tr-TR')}</span>
                          )}
                        </div>
                        
                        <div className="flex space-x-2">
                          <button
                            onClick={() => askFaqQuestion(faq.id, faq.question)}
                            className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
                          >
                            💭 Bu Soruyu Sor
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
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