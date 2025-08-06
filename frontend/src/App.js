import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Swal from 'sweetalert2';
import SearchTab from './components/SearchTab';
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
  
  // Authentication için yeni state'ler
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [authToken, setAuthToken] = useState(localStorage.getItem('auth_token'));
  const [showLogin, setShowLogin] = useState(false);
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [loginLoading, setLoginLoading] = useState(false);
  
  // Rating için yeni state'ler  
  const [messageRatings, setMessageRatings] = useState({});
  const [ratingStats, setRatingStats] = useState(null);
  
  // Admin Dashboard için yeni state'ler
  const [userStats, setUserStats] = useState(null);
  const [allUsers, setAllUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [showEditUser, setShowEditUser] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [newUser, setNewUser] = useState({
    username: '', email: '', full_name: '', password: '', role: 'viewer'
  });
  const [userForm, setUserForm] = useState({
    full_name: '', email: '', role: '', is_active: true
  });
  
  // Profile Management için yeni state'ler
  const [showProfileDropdown, setShowProfileDropdown] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [showPasswordChangeModal, setShowPasswordChangeModal] = useState(false);
  const [profileForm, setProfileForm] = useState({
    full_name: '', email: ''
  });
  const [passwordForm, setPasswordForm] = useState({
    current_password: '', new_password: '', confirm_password: ''
  });
  const [passwordLoading, setPasswordLoading] = useState(false);
  
  // Doküman arama için yeni state'ler
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [searchType, setSearchType] = useState('text'); // text, regex, exact
  const [caseSensitive, setCaseSensitive] = useState(false);
  const [searchSuggestions, setSearchSuggestions] = useState([]);
  const [showSearchSuggestions, setShowSearchSuggestions] = useState(false);
  const [searchStatistics, setSearchStatistics] = useState(null);
  
  const chatEndRef = useRef(null);

  const backendUrl = process.env.REACT_APP_BACKEND_URL;

  useEffect(() => {
    // Session ID oluştur
    setSessionId(generateSessionId());
    // Authentication'ı kontrol et
    checkAuthentication();
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
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
    }
  }, [isAuthenticated]);

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showProfileDropdown && !event.target.closest('.relative')) {
        setShowProfileDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showProfileDropdown]);

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

  // Authentication functions
  const checkAuthentication = async () => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      setIsAuthenticated(false);
      setCurrentUser(null);
      return;
    }

    try {
      const response = await fetch(`${backendUrl}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const userData = await response.json();
        setCurrentUser(userData);
        setIsAuthenticated(true);
        setAuthToken(token);
      } else {
        // Token expired or invalid
        localStorage.removeItem('auth_token');
        setIsAuthenticated(false);
        setCurrentUser(null);
        setAuthToken(null);
      }
    } catch (error) {
      console.error('Authentication check failed:', error);
      localStorage.removeItem('auth_token');
      setIsAuthenticated(false);
      setCurrentUser(null);
      setAuthToken(null);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginLoading(true);

    try {
      const response = await fetch(`${backendUrl}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(loginForm)
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('auth_token', data.access_token);
        setAuthToken(data.access_token);
        setCurrentUser(data.user_info);
        setIsAuthenticated(true);
        setShowLogin(false);
        setLoginForm({ username: '', password: '' });
      } else {
        alert('Giriş başarısız: ' + (data.detail || 'Bilinmeyen hata'));
      }
    } catch (error) {
      console.error('Login error:', error);
      alert('Giriş hatası: ' + error.message);
    }

    setLoginLoading(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    setAuthToken(null);
    setCurrentUser(null);
    setIsAuthenticated(false);
    setChatHistory([]);
    setDocuments([]);
    setGroups([]);
    setFavoriteQuestions([]);
    setFaqItems([]);
  };

  // Rating functions
  const addRating = async (sessionId, chatSessionId, rating, feedback = '') => {
    if (!isAuthenticated || !authToken) {
      alert('Oylama yapabilmek için giriş yapmanız gerekir');
      return;
    }

    try {
      const response = await fetch(`${backendUrl}/api/ratings`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId,
          chat_session_id: chatSessionId,
          rating: rating,
          feedback: feedback
        })
      });

      const data = await response.json();

      if (response.ok) {
        // Update local rating state
        setMessageRatings(prev => ({
          ...prev,
          [sessionId]: { rating, feedback, ratingId: data.rating_id }
        }));
        return data;
      } else {
        throw new Error(data.detail || 'Rating error');
      }
    } catch (error) {
      console.error('Rating error:', error);
      alert('Oylama hatası: ' + error.message);
    }
  };

  const fetchRatingStats = async () => {
    if (!isAuthenticated || !authToken || currentUser?.role !== 'admin') {
      return;
    }

    try {
      const response = await fetch(`${backendUrl}/api/ratings/stats`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setRatingStats(data);
      }
    } catch (error) {
      console.error('Rating stats error:', error);
    }
  };

  // Profile Management Functions
  const updateProfile = async () => {
    if (!isAuthenticated || !authToken) return;
    
    try {
      const response = await fetch(`${backendUrl}/api/auth/profile`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(profileForm)
      });

      const data = await response.json();

      if (response.ok) {
        setCurrentUser(data);
        alert('Profil başarıyla güncellendi!');
        setShowProfileModal(false);
      } else {
        alert('Profil güncelleme hatası: ' + (data.detail || 'Bilinmeyen hata'));
      }
    } catch (error) {
      console.error('Profile update error:', error);
      alert('Profil güncelleme hatası: ' + error.message);
    }
  };

  const changePassword = async () => {
    if (!isAuthenticated || !authToken) return;
    
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      alert('Yeni şifreler eşleşmiyor!');
      return;
    }
    
    if (passwordForm.new_password.length < 6) {
      alert('Yeni şifre en az 6 karakter olmalıdır!');
      return;
    }
    
    setPasswordLoading(true);
    
    try {
      const response = await fetch(`${backendUrl}/api/auth/change-password`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password
        })
      });

      const data = await response.json();

      if (response.ok) {
        alert('Şifre başarıyla değiştirildi!');
        setShowPasswordChangeModal(false);
        setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
      } else {
        alert('Şifre değiştirme hatası: ' + (data.detail || 'Bilinmeyen hata'));
      }
    } catch (error) {
      console.error('Password change error:', error);
      alert('Şifre değiştirme hatası: ' + error.message);
    } finally {
      setPasswordLoading(false);
    }
  };

  // Admin Dashboard Functions
  const fetchUserStats = async () => {
    if (!isAuthenticated || !authToken || currentUser?.role !== 'admin') return;
    
    try {
      const response = await fetch(`${backendUrl}/api/auth/users/stats`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setUserStats(data);
      }
    } catch (error) {
      console.error('User stats error:', error);
    }
  };

  const fetchAllUsers = async () => {
    if (!isAuthenticated || !authToken || currentUser?.role !== 'admin') return;
    
    setLoadingUsers(true);
    try {
      const response = await fetch(`${backendUrl}/api/auth/users`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setAllUsers(data.users || []);
      }
    } catch (error) {
      console.error('Users fetch error:', error);
    } finally {
      setLoadingUsers(false);
    }
  };

  const createUser = async () => {
    if (!isAuthenticated || !authToken) return;
    
    try {
      const response = await fetch(`${backendUrl}/api/auth/create-user`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newUser)
      });

      const data = await response.json();

      if (response.ok) {
        alert('Kullanıcı başarıyla oluşturuldu!');
        setShowCreateUser(false);
        setNewUser({ username: '', email: '', full_name: '', password: '', role: 'viewer' });
        fetchAllUsers();
        fetchUserStats();
      } else {
        alert('Kullanıcı oluşturma hatası: ' + (data.detail || 'Bilinmeyen hata'));
      }
    } catch (error) {
      console.error('Create user error:', error);
      alert('Kullanıcı oluşturma hatası: ' + error.message);
    }
  };

  const updateUser = async (userId) => {
    if (!isAuthenticated || !authToken) return;
    
    try {
      const response = await fetch(`${backendUrl}/api/auth/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(userForm)
      });

      const data = await response.json();

      if (response.ok) {
        alert('Kullanıcı başarıyla güncellendi!');
        setShowEditUser(false);
        setEditingUser(null);
        setUserForm({ full_name: '', email: '', role: '', is_active: true });
        fetchAllUsers();
        fetchUserStats();
      } else {
        alert('Kullanıcı güncelleme hatası: ' + (data.detail || 'Bilinmeyen hata'));
      }
    } catch (error) {
      console.error('Update user error:', error);
      alert('Kullanıcı güncelleme hatası: ' + error.message);
    }
  };

  const deleteUser = async (userId, username) => {
    if (!isAuthenticated || !authToken) return;
    
    if (!confirm(`${username} kullanıcısını silmek istediğinizden emin misiniz?`)) return;
    
    try {
      const response = await fetch(`${backendUrl}/api/auth/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();

      if (response.ok) {
        alert('Kullanıcı başarıyla silindi!');
        fetchAllUsers();
        fetchUserStats();
      } else {
        alert('Kullanıcı silme hatası: ' + (data.detail || 'Bilinmeyen hata'));
      }
    } catch (error) {
      console.error('Delete user error:', error);
      alert('Kullanıcı silme hatası: ' + error.message);
    }
  };

  const bulkUpdateUsers = async (action, newRole = null) => {
    if (!isAuthenticated || !authToken || selectedUsers.length === 0) return;
    
    const actionText = {
      'activate': 'etkinleştir',
      'deactivate': 'devre dışı bırak',  
      'change_role': `rolünü ${newRole} olarak değiştir`,
      'delete': 'sil'
    };
    
    if (!confirm(`Seçili ${selectedUsers.length} kullanıcıyı ${actionText[action]}mek istediğinizden emin misiniz?`)) return;
    
    try {
      const response = await fetch(`${backendUrl}/api/auth/users/bulk-update`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_ids: selectedUsers,
          action: action,
          new_role: newRole
        })
      });

      const data = await response.json();

      if (response.ok) {
        alert(`Toplu işlem başarılı: ${data.affected_count} kullanıcı etkilendi`);
        setSelectedUsers([]);
        fetchAllUsers();
        fetchUserStats();
      } else {
        alert('Toplu işlem hatası: ' + (data.detail || 'Bilinmeyen hata'));
      }
    } catch (error) {
      console.error('Bulk update error:', error);
      alert('Toplu işlem hatası: ' + error.message);
    }
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
    if (!isAuthenticated || !authToken) return;
    
    try {
      let url = `${backendUrl}/api/documents`;
      
      // Grup filtresi ekle
      if (selectedGroup && selectedGroup !== 'all') {
        url += `?group_id=${selectedGroup}`;
      }
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      });
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

  // Doküman linkleri için handler (markdown'dan gelen linkler)
  const handleViewDocument = (docId) => {
    // documents listesinden dokümanı bul
    const document = documents.find(doc => doc.id === docId);
    if (document) {
      downloadOriginalDocument(docId, document.filename);
    } else {
      alert('Doküman bulunamadı');
    }
  };

  // Orijinal dokümanı indir
  const downloadOriginalDocument = async (documentId, filename) => {
    try {
      const response = await fetch(`${backendUrl}/api/documents/${documentId}/download-original`);
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        alert('Dosya indirilemedi');
      }
    } catch (error) {
      alert(`Dosya indirme hatası: ${error.message}`);
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

  // Doküman arama fonksiyonları
  const performDocumentSearch = async () => {
    if (!searchQuery.trim()) {
      alert('Lütfen aranacak metin girin');
      return;
    }

    setLoadingSearch(true);
    try {
      const response = await fetch(`${backendUrl}/api/search-in-documents`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery,
          search_type: searchType,
          case_sensitive: caseSensitive,
          max_results: 50,
          highlight_context: 200
        })
      });

      const data = await response.json();

      if (response.ok) {
        setSearchResults(data.results || []);
        setSearchStatistics(data.statistics);
      } else {
        alert(`Arama hatası: ${data.detail || 'Bilinmeyen hata'}`);
        setSearchResults([]);
        setSearchStatistics(null);
      }
    } catch (error) {
      alert(`Arama hatası: ${error.message}`);
      setSearchResults([]);
      setSearchStatistics(null);
    } finally {
      setLoadingSearch(false);
    }
  };

  const fetchSearchSuggestions = async (query) => {
    if (!query || query.length < 2) {
      setSearchSuggestions([]);
      setShowSearchSuggestions(false);
      return;
    }

    try {
      const response = await fetch(`${backendUrl}/api/search-suggestions?q=${encodeURIComponent(query)}&limit=5`);
      const data = await response.json();
      
      if (response.ok) {
        setSearchSuggestions(data.suggestions || []);
        setShowSearchSuggestions(data.suggestions.length > 0);
      } else {
        setSearchSuggestions([]);
        setShowSearchSuggestions(false);
      }
    } catch (error) {
      console.error('Arama önerisi alınamadı:', error);
      setSearchSuggestions([]);
      setShowSearchSuggestions(false);
    }
  };

  // Debounced search suggestions
  const debouncedFetchSearchSuggestions = React.useCallback(
    (() => {
      let timeoutId;
      return (query) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
          fetchSearchSuggestions(query);
        }, 300);
      };
    })(),
    []
  );

  const handleSearchQueryChange = (e) => {
    const value = e.target.value;
    setSearchQuery(value);
    
    // Arama önerilerini getir (debounced)
    debouncedFetchSearchSuggestions(value);
  };

  const handleSearchSuggestionSelect = (suggestion) => {
    setSearchQuery(suggestion.text);
    setShowSearchSuggestions(false);
    setSearchSuggestions([]);
  };

  const hideSearchSuggestions = () => {
    setTimeout(() => {
      setShowSearchSuggestions(false);
    }, 150);
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
            
            {/* Authentication Section */}
            <div className="flex items-center space-x-4">
              {isAuthenticated && currentUser ? (
                <div className="relative">
                  <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setShowProfileDropdown(!showProfileDropdown)}>
                    <div className="text-right">
                      <p className="text-sm font-medium text-gray-900">{currentUser.full_name}</p>
                      <p className="text-xs text-gray-600">{currentUser.role === 'admin' ? 'Yönetici' : currentUser.role === 'editor' ? 'Editör' : 'Görüntüleyici'}</p>
                    </div>
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold ${
                      currentUser.role === 'admin' ? 'bg-red-500' : 
                      currentUser.role === 'editor' ? 'bg-blue-500' : 'bg-green-500'
                    }`}>
                      {currentUser.full_name?.charAt(0)?.toUpperCase()}
                    </div>
                    <span className="text-gray-400">▼</span>
                  </div>
                  
                  {/* Profile Dropdown Menu */}
                  {showProfileDropdown && (
                    <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
                      <div className="py-2">
                        <button
                          onClick={() => {
                            setProfileForm({ 
                              full_name: currentUser.full_name, 
                              email: currentUser.email 
                            });
                            setShowProfileModal(true);
                            setShowProfileDropdown(false);
                          }}
                          className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center"
                        >
                          <span className="mr-2">👤</span>
                          Profili Düzenle
                        </button>
                        <button
                          onClick={() => {
                            setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
                            setShowPasswordChangeModal(true);
                            setShowProfileDropdown(false);
                          }}
                          className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center"
                        >
                          <span className="mr-2">🔒</span>
                          Şifre Değiştir
                        </button>
                        <hr className="my-1" />
                        <button
                          onClick={() => {
                            handleLogout();
                            setShowProfileDropdown(false);
                          }}
                          className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center"
                        >
                          <span className="mr-2">🚪</span>
                          Çıkış Yap
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <button
                  onClick={() => setShowLogin(true)}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                  Giriş Yap
                </button>
              )}
            </div>
            
            {systemStatus && isAuthenticated && (
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
            onClick={() => setActiveTab('search')}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'search'
                ? 'bg-blue-500 text-white shadow-sm'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            🔍 Arama
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
          {isAuthenticated && currentUser?.role === 'admin' && (
            <button
              onClick={() => {
                setActiveTab('admin');
                fetchUserStats();
                fetchAllUsers();
                fetchRatingStats();
              }}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'admin'
                  ? 'bg-red-500 text-white shadow-sm'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              ⚙️ Yönetim
            </button>
          )}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {!isAuthenticated ? (
          /* Login Required Message */
          <div className="bg-white rounded-xl shadow-lg p-12 text-center">
            <div className="w-24 h-24 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-6">
              <span className="text-white text-3xl">🔒</span>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Kurumsal Prosedür Asistanı'na Hoş Geldiniz</h2>
            <p className="text-gray-600 mb-8">
              AI destekli doküman soru-cevap sistemi ile prosedürlerinize hızlı erişim sağlayın.<br />
              Sistemi kullanabilmek için giriş yapmanız gerekmektedir.
            </p>
            <button
              onClick={() => setShowLogin(true)}
              className="px-8 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-lg font-medium"
            >
              Giriş Yap
            </button>
            
            {/* Features Overview */}
            <div className="grid md:grid-cols-3 gap-6 mt-12">
              <div className="text-center">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                  <span className="text-blue-600 text-xl">💬</span>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Akıllı Q&A</h3>
                <p className="text-sm text-gray-600">AI ile dokümanlarınızdan anında yanıt alın</p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                  <span className="text-green-600 text-xl">📁</span>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Doküman Yönetimi</h3>
                <p className="text-sm text-gray-600">Word dosyalarınızı yükleyin ve organize edin</p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                  <span className="text-purple-600 text-xl">🔍</span>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Gelişmiş Arama</h3>
                <p className="text-sm text-gray-600">Dokümanlar içinde detaylı arama yapın</p>
              </div>
            </div>
          </div>
        ) : activeTab === 'chat' ? (
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
                              {message.type === 'ai' && isAuthenticated && (
                                <RatingWidget 
                                  sessionId={message.sessionId || sessionId}
                                  messageIndex={index}
                                  onRate={addRating}
                                  existingRating={messageRatings[message.sessionId || sessionId]}
                                />
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
        ) : activeTab === 'search' ? (
          /* Search Tab */
          <SearchTab
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            searchType={searchType}
            setSearchType={setSearchType}
            caseSensitive={caseSensitive}
            setCaseSensitive={setCaseSensitive}
            searchResults={searchResults}
            searchStatistics={searchStatistics}
            loadingSearch={loadingSearch}
            searchSuggestions={searchSuggestions}
            showSearchSuggestions={showSearchSuggestions}
            setShowSearchSuggestions={setShowSearchSuggestions}
            performDocumentSearch={performDocumentSearch}
            handleSearchQueryChange={handleSearchQueryChange}
            handleSearchSuggestionSelect={handleSearchSuggestionSelect}
            hideSearchSuggestions={hideSearchSuggestions}
            downloadOriginalDocument={downloadOriginalDocument}
          />
        ) : activeTab === 'admin' ? (
          /* Admin Dashboard */
          <div className="space-y-6">
            {/* User Statistics */}
            {userStats && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="bg-white rounded-xl shadow-lg p-6">
                  <div className="flex items-center">
                    <div className="p-3 bg-blue-100 rounded-full">
                      <span className="text-2xl">👥</span>
                    </div>
                    <div className="ml-4">
                      <p className="text-2xl font-bold text-blue-600">{userStats.total_users}</p>
                      <p className="text-gray-600">Toplam Kullanıcı</p>
                    </div>
                  </div>
                </div>
                
                <div className="bg-white rounded-xl shadow-lg p-6">
                  <div className="flex items-center">
                    <div className="p-3 bg-green-100 rounded-full">
                      <span className="text-2xl">✅</span>
                    </div>
                    <div className="ml-4">
                      <p className="text-2xl font-bold text-green-600">{userStats.active_users}</p>
                      <p className="text-gray-600">Aktif Kullanıcı</p>
                    </div>
                  </div>
                </div>
                
                <div className="bg-white rounded-xl shadow-lg p-6">
                  <div className="flex items-center">
                    <div className="p-3 bg-red-100 rounded-full">
                      <span className="text-2xl">🔴</span>
                    </div>
                    <div className="ml-4">
                      <p className="text-2xl font-bold text-red-600">{userStats.admin_count}</p>
                      <p className="text-gray-600">Yöneticiler</p>
                    </div>
                  </div>
                </div>
                
                <div className="bg-white rounded-xl shadow-lg p-6">
                  <div className="flex items-center">
                    <div className="p-3 bg-purple-100 rounded-full">
                      <span className="text-2xl">⚡</span>
                    </div>
                    <div className="ml-4">
                      <p className="text-2xl font-bold text-purple-600">{userStats.editor_count + userStats.viewer_count}</p>
                      <p className="text-gray-600">Editor & Viewer</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* User Management */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold text-gray-900">👥 Kullanıcı Yönetimi</h2>
                <div className="flex space-x-3">
                  <button
                    onClick={() => setShowCreateUser(true)}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                  >
                    ➕ Kullanıcı Oluştur
                  </button>
                  
                  {selectedUsers.length > 0 && (
                    <div className="flex space-x-2">
                      <button
                        onClick={() => bulkUpdateUsers('activate')}
                        className="px-3 py-2 bg-green-500 text-white text-sm rounded hover:bg-green-600"
                      >
                        ✅ Etkinleştir
                      </button>
                      <button
                        onClick={() => bulkUpdateUsers('deactivate')}
                        className="px-3 py-2 bg-yellow-500 text-white text-sm rounded hover:bg-yellow-600"
                      >
                        ⏸️ Devre Dışı
                      </button>
                      <button
                        onClick={() => bulkUpdateUsers('delete')}
                        className="px-3 py-2 bg-red-500 text-white text-sm rounded hover:bg-red-600"
                      >
                        🗑️ Sil
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* User List */}
              {loadingUsers ? (
                <div className="text-center py-8">
                  <div className="text-gray-600">Kullanıcılar yükleniyor...</div>
                </div>
              ) : allUsers.length === 0 ? (
                <div className="text-center py-8">
                  <div className="text-gray-600">Kullanıcı bulunamadı</div>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left">
                          <input
                            type="checkbox"
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedUsers(allUsers.filter(u => u.id !== currentUser?.id).map(u => u.id));
                              } else {
                                setSelectedUsers([]);
                              }
                            }}
                            className="rounded"
                          />
                        </th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Kullanıcı</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Email</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Rol</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Durum</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Son Giriş</th>
                        <th className="px-4 py-3 text-right text-sm font-medium text-gray-700">İşlemler</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {allUsers.map((user) => (
                        <tr key={user.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3">
                            <input
                              type="checkbox"
                              checked={selectedUsers.includes(user.id)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedUsers([...selectedUsers, user.id]);
                                } else {
                                  setSelectedUsers(selectedUsers.filter(id => id !== user.id));
                                }
                              }}
                              disabled={user.id === currentUser?.id}
                              className="rounded"
                            />
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center">
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold mr-3 ${
                                user.role === 'admin' ? 'bg-red-500' : 
                                user.role === 'editor' ? 'bg-blue-500' : 'bg-green-500'
                              }`}>
                                {user.full_name?.charAt(0)?.toUpperCase()}
                              </div>
                              <div>
                                <div className="font-medium text-gray-900">{user.full_name}</div>
                                <div className="text-sm text-gray-500">@{user.username}</div>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-900">{user.email}</td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              user.role === 'admin' ? 'bg-red-100 text-red-800' :
                              user.role === 'editor' ? 'bg-blue-100 text-blue-800' :
                              'bg-green-100 text-green-800'
                            }`}>
                              {user.role === 'admin' ? 'Yönetici' : 
                               user.role === 'editor' ? 'Editör' : 'Görüntüleyici'}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                            }`}>
                              {user.is_active ? 'Aktif' : 'Pasif'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-500">
                            {user.last_login ? new Date(user.last_login).toLocaleDateString('tr-TR') : 'Hiç giriş yapmamış'}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex justify-end space-x-2">
                              <button
                                onClick={() => {
                                  setEditingUser(user);
                                  setUserForm({
                                    full_name: user.full_name,
                                    email: user.email,
                                    role: user.role,
                                    is_active: user.is_active
                                  });
                                  setShowEditUser(true);
                                }}
                                className="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
                              >
                                ✏️ Düzenle
                              </button>
                              {user.id !== currentUser?.id && (
                                <button
                                  onClick={() => deleteUser(user.id, user.username)}
                                  className="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600"
                                >
                                  🗑️ Sil
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Rating Analytics */}
            {ratingStats && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">⭐ AI Cevap Kalitesi</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-yellow-600">{ratingStats.average_rating.toFixed(1)}</div>
                    <div className="text-gray-600">Ortalama Puan</div>
                    <div className="text-sm text-gray-500">({ratingStats.total_ratings} değerlendirme)</div>
                  </div>
                  <div className="col-span-2">
                    <div className="space-y-2">
                      {Object.entries(ratingStats.rating_distribution).reverse().map(([rating, count]) => (
                        <div key={rating} className="flex items-center">
                          <span className="w-8 text-sm">{rating}⭐</span>
                          <div className="flex-1 mx-3 bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-yellow-500 h-2 rounded-full" 
                              style={{ width: `${(count / ratingStats.total_ratings) * 100}%` }}
                            ></div>
                          </div>
                          <span className="w-8 text-sm text-gray-600">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
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
                            onClick={() => downloadOriginalDocument(doc.id, doc.filename)}
                            className="p-1 text-blue-500 hover:bg-blue-50 rounded transition-colors"
                            title="Orijinal Dosyayı İndir"
                          >
                            📎
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

      {/* Login Modal */}
      {showLogin && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 w-full max-w-md">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center mx-auto mb-4">
                <span className="text-white font-bold text-2xl">KPA</span>
              </div>
              <h3 className="text-2xl font-semibold text-gray-900">Giriş Yap</h3>
              <p className="text-gray-600 mt-2">Kurumsal Prosedür Asistanı'na erişim için giriş yapın</p>
            </div>
            
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Kullanıcı Adı
                </label>
                <input
                  type="text"
                  value={loginForm.username}
                  onChange={(e) => setLoginForm(prev => ({ ...prev, username: e.target.value }))}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Kullanıcı adınızı girin"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Şifre
                </label>
                <input
                  type="password"
                  value={loginForm.password}
                  onChange={(e) => setLoginForm(prev => ({ ...prev, password: e.target.value }))}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Şifrenizi girin"
                  required
                />
              </div>
              
              <div className="flex justify-between items-center space-x-4 mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setShowLogin(false);
                    setLoginForm({ username: '', password: '' });
                  }}
                  className="px-6 py-3 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  İptal
                </button>
                <button
                  type="submit"
                  disabled={loginLoading}
                  className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50"
                >
                  {loginLoading ? 'Giriş yapılıyor...' : 'Giriş Yap'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create User Modal */}
      {showCreateUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 w-full max-w-md">
            <h3 className="text-xl font-semibold text-gray-900 mb-6">➕ Yeni Kullanıcı Oluştur</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Kullanıcı Adı</label>
                <input
                  type="text"
                  value={newUser.username}
                  onChange={(e) => setNewUser(prev => ({ ...prev, username: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Kullanıcı adı"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
                <input
                  type="email"
                  value={newUser.email}
                  onChange={(e) => setNewUser(prev => ({ ...prev, email: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Email adresi"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Ad Soyad</label>
                <input
                  type="text"
                  value={newUser.full_name}
                  onChange={(e) => setNewUser(prev => ({ ...prev, full_name: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Ad Soyad"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Şifre</label>
                <input
                  type="password"
                  value={newUser.password}
                  onChange={(e) => setNewUser(prev => ({ ...prev, password: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Şifre"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Rol</label>
                <select
                  value={newUser.role}
                  onChange={(e) => setNewUser(prev => ({ ...prev, role: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="viewer">Görüntüleyici</option>
                  <option value="editor">Editör</option>
                  <option value="admin">Yönetici</option>
                </select>
              </div>
            </div>
            
            <div className="flex justify-between items-center space-x-4 mt-6">
              <button
                onClick={() => {
                  setShowCreateUser(false);
                  setNewUser({ username: '', email: '', full_name: '', password: '', role: 'viewer' });
                }}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                İptal
              </button>
              <button
                onClick={createUser}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                Oluştur
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit User Modal */}
      {showEditUser && editingUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 w-full max-w-md">
            <h3 className="text-xl font-semibold text-gray-900 mb-6">✏️ Kullanıcı Düzenle</h3>
            
            <div className="mb-4 p-3 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">
                <strong>Kullanıcı:</strong> @{editingUser.username}
              </p>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Ad Soyad</label>
                <input
                  type="text"
                  value={userForm.full_name}
                  onChange={(e) => setUserForm(prev => ({ ...prev, full_name: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
                <input
                  type="email"
                  value={userForm.email}
                  onChange={(e) => setUserForm(prev => ({ ...prev, email: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Rol</label>
                <select
                  value={userForm.role}
                  onChange={(e) => setUserForm(prev => ({ ...prev, role: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  disabled={editingUser.id === currentUser?.id}
                >
                  <option value="viewer">Görüntüleyici</option>
                  <option value="editor">Editör</option>
                  <option value="admin">Yönetici</option>
                </select>
              </div>
              
              <div>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={userForm.is_active}
                    onChange={(e) => setUserForm(prev => ({ ...prev, is_active: e.target.checked }))}
                    disabled={editingUser.id === currentUser?.id}
                    className="rounded mr-2"
                  />
                  <span className="text-sm font-medium text-gray-700">Aktif Kullanıcı</span>
                </label>
              </div>
            </div>
            
            <div className="flex justify-between items-center space-x-4 mt-6">
              <button
                onClick={() => {
                  setShowEditUser(false);
                  setEditingUser(null);
                  setUserForm({ full_name: '', email: '', role: '', is_active: true });
                }}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                İptal
              </button>
              <button
                onClick={() => updateUser(editingUser.id)}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                Güncelle
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Profile Modal */}
      {showProfileModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 w-full max-w-md">
            <h3 className="text-xl font-semibold text-gray-900 mb-6">👤 Profil Düzenle</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Ad Soyad</label>
                <input
                  type="text"
                  value={profileForm.full_name}
                  onChange={(e) => setProfileForm(prev => ({ ...prev, full_name: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
                <input
                  type="email"
                  value={profileForm.email}
                  onChange={(e) => setProfileForm(prev => ({ ...prev, email: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600">
                  <strong>Kullanıcı Adı:</strong> @{currentUser?.username}
                </p>
                <p className="text-sm text-gray-600">
                  <strong>Rol:</strong> {currentUser?.role === 'admin' ? 'Yönetici' : currentUser?.role === 'editor' ? 'Editör' : 'Görüntüleyici'}
                </p>
              </div>
            </div>
            
            <div className="flex justify-between items-center space-x-4 mt-6">
              <button
                onClick={() => {
                  setShowProfileModal(false);
                  setProfileForm({ full_name: '', email: '' });
                }}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                İptal
              </button>
              <button
                onClick={updateProfile}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                Güncelle
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Password Change Modal */}
      {showPasswordChangeModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 w-full max-w-md">
            <h3 className="text-xl font-semibold text-gray-900 mb-6">🔒 Şifre Değiştir</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Mevcut Şifre</label>
                <input
                  type="password"
                  value={passwordForm.current_password}
                  onChange={(e) => setPasswordForm(prev => ({ ...prev, current_password: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Mevcut şifrenizi girin"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Yeni Şifre</label>
                <input
                  type="password"
                  value={passwordForm.new_password}
                  onChange={(e) => setPasswordForm(prev => ({ ...prev, new_password: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Yeni şifrenizi girin (min 6 karakter)"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Yeni Şifre (Tekrar)</label>
                <input
                  type="password"
                  value={passwordForm.confirm_password}
                  onChange={(e) => setPasswordForm(prev => ({ ...prev, confirm_password: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Yeni şifrenizi tekrar girin"
                />
              </div>
              
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-800">
                  <strong>Şifre Kuralları:</strong>
                  <br />• En az 6 karakter uzunluğunda olmalıdır
                  <br />• Güvenlik için karmaşık bir şifre seçin
                </p>
              </div>
            </div>
            
            <div className="flex justify-between items-center space-x-4 mt-6">
              <button
                onClick={() => {
                  setShowPasswordChangeModal(false);
                  setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
                }}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                İptal
              </button>
              <button
                onClick={changePassword}
                disabled={passwordLoading}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
              >
                {passwordLoading ? 'Değiştiriliyor...' : 'Şifreyi Değiştir'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

// Rating Widget Component
const RatingWidget = ({ sessionId, messageIndex, onRate, existingRating }) => {
  const [showRating, setShowRating] = useState(false);
  const [rating, setRating] = useState(existingRating?.rating || 0);
  const [feedback, setFeedback] = useState(existingRating?.feedback || '');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (rating === 0) {
      alert('Lütfen bir puan verin (1-5 yıldız)');
      return;
    }

    setIsSubmitting(true);
    try {
      await onRate(sessionId, sessionId, rating, feedback);
      setShowRating(false);
      alert('Değerlendirme başarıyla kaydedildi!');
    } catch (error) {
      console.error('Rating error:', error);
    }
    setIsSubmitting(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setShowRating(!showRating)}
        className={`bg-white bg-opacity-20 hover:bg-opacity-30 px-2 py-1 rounded transition-colors ${
          existingRating ? 'text-yellow-300' : ''
        }`}
        title={existingRating ? `Oyunuz: ${existingRating.rating} yıldız` : 'Bu yanıtı oylayın'}
      >
        {existingRating ? `⭐ ${existingRating.rating}` : '⭐ Oyla'}
      </button>

      {showRating && (
        <div className="absolute bottom-full right-0 mb-2 bg-white border border-gray-200 rounded-lg shadow-lg p-4 w-80 z-10">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Bu yanıtı değerlendirin</h4>
          
          <div className="flex items-center space-x-1 mb-3">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                onClick={() => setRating(star)}
                className={`text-2xl ${
                  star <= rating ? 'text-yellow-400' : 'text-gray-300'
                } hover:text-yellow-400 transition-colors`}
              >
                ⭐
              </button>
            ))}
            <span className="ml-2 text-sm text-gray-600">
              {rating > 0 ? `${rating} yıldız` : 'Puan seçin'}
            </span>
          </div>

          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="İsteğe bağlı: Yorumunuzu yazın..."
            className="w-full p-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows="3"
          />

          <div className="flex justify-between items-center mt-3">
            <button
              onClick={() => setShowRating(false)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              İptal
            </button>
            <button
              onClick={handleSubmit}
              disabled={isSubmitting || rating === 0}
              className="px-4 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 disabled:opacity-50 transition-colors"
            >
              {isSubmitting ? 'Gönderiliyor...' : 'Gönder'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;