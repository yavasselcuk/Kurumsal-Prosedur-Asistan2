import React from 'react';
import ReactMarkdown from 'react-markdown';

const SearchTab = ({
  searchQuery,
  setSearchQuery,
  searchType,
  setSearchType,
  caseSensitive,
  setCaseSensitive,
  searchResults,
  searchStatistics,
  loadingSearch,
  searchSuggestions,
  showSearchSuggestions,
  performDocumentSearch,
  handleSearchQueryChange,
  handleSearchSuggestionSelect,
  hideSearchSuggestions,
  downloadOriginalDocument
}) => {
  
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    performDocumentSearch();
  };

  return (
    <div className="space-y-6">
      {/* Arama Header */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-semibold text-gray-900">🔍 Doküman İçinde Arama</h2>
        </div>

        {/* Arama Formu */}
        <form onSubmit={handleSearchSubmit} className="space-y-4">
          {/* Ana Arama Input */}
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={handleSearchQueryChange}
              onFocus={() => {
                if (searchSuggestions.length > 0) {
                  setShowSearchSuggestions(true);
                }
              }}
              onBlur={hideSearchSuggestions}
              placeholder="Dokümanlar içinde aranacak metni girin..."
              disabled={loadingSearch}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
            />

            {/* Arama Önerileri Dropdown */}
            {showSearchSuggestions && searchSuggestions.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-48 overflow-y-auto">
                <div className="py-1">
                  <div className="px-3 py-2 text-xs font-medium text-gray-500 bg-gray-50 border-b">
                    🔍 Arama Önerileri
                  </div>
                  {searchSuggestions.map((suggestion, index) => (
                    <button
                      key={index}
                      type="button"
                      onClick={() => handleSearchSuggestionSelect(suggestion)}
                      className="w-full text-left px-3 py-2 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
                    >
                      <div className="flex items-center space-x-2">
                        <span className="text-sm">{suggestion.icon}</span>
                        <div className="flex-1">
                          <p className="text-sm text-gray-900">{suggestion.text}</p>
                          <p className="text-xs text-gray-500">{suggestion.frequency} kez geçiyor</p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Arama Seçenekleri */}
          <div className="flex flex-wrap gap-4">
            {/* Arama Tipi */}
            <div className="flex-1 min-w-48">
              <label className="block text-sm font-medium text-gray-700 mb-2">Arama Tipi</label>
              <select
                value={searchType}
                onChange={(e) => setSearchType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="text">📝 Metin Arama</option>
                <option value="exact">🎯 Tam Eşleşme</option>
                <option value="regex">🔧 Regex Pattern</option>
              </select>
            </div>

            {/* Case Sensitivity */}
            <div className="flex items-center space-x-2 mt-6">
              <input
                type="checkbox"
                id="caseSensitive"
                checked={caseSensitive}
                onChange={(e) => setCaseSensitive(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="caseSensitive" className="text-sm text-gray-700">
                Büyük/küçük harf duyarlı
              </label>
            </div>

            {/* Arama Butonu */}
            <div className="flex-1 min-w-32">
              <button
                type="submit"
                disabled={loadingSearch || !searchQuery.trim()}
                className="w-full mt-6 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {loadingSearch ? '🔄 Aranıyor...' : '🔍 Ara'}
              </button>
            </div>
          </div>
        </form>

        {/* Arama İstatistikleri */}
        {searchStatistics && (
          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <h3 className="text-sm font-medium text-gray-900 mb-2">📊 Arama Sonuçları</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="text-center">
                <div className="text-lg font-bold text-blue-600">{searchStatistics.total_documents_searched}</div>
                <div className="text-gray-600">Aranan Doküman</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-green-600">{searchStatistics.documents_with_matches}</div>
                <div className="text-gray-600">Eşleşme Bulunan</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-purple-600">{searchStatistics.total_matches}</div>
                <div className="text-gray-600">Toplam Eşleşme</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-orange-600">{Math.round(searchStatistics.average_match_score * 100)}%</div>
                <div className="text-gray-600">Ortalama Skor</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Arama Sonuçları */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">📋 Arama Sonuçları</h3>
        
        {loadingSearch ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-600">Dokümanlar aranıyor...</p>
          </div>
        ) : searchResults.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl">🔍</span>
            </div>
            {searchQuery ? (
              <>
                <p className="text-gray-600">"{searchQuery}" için sonuç bulunamadı.</p>
                <p className="text-gray-500 text-sm mt-1">Farklı arama terimleri deneyin veya arama tipini değiştirin.</p>
              </>
            ) : (
              <>
                <p className="text-gray-600">Henüz arama yapılmadı.</p>
                <p className="text-gray-500 text-sm mt-1">Yukarıdaki arama kutusunu kullanarak dokümanlar içinde arama yapın.</p>
              </>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {searchResults.map((result, index) => (
              <div
                key={index}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                {/* Doküman Header */}
                <div className="flex justify-between items-start mb-3">
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900 mb-1">
                      📄 {result.document_filename}
                    </h4>
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <span>📁 {result.document_group}</span>
                      <span>🎯 {result.total_matches} eşleşme</span>
                      <span>⭐ {Math.round(result.match_score * 100)}% skor</span>
                    </div>
                  </div>
                  <button
                    onClick={() => downloadOriginalDocument(result.document_id, result.document_filename)}
                    className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
                  >
                    📎 İndir
                  </button>
                </div>

                {/* Eşleşmeler */}
                <div className="space-y-3">
                  {result.matches.slice(0, 3).map((match, matchIndex) => (
                    <div key={matchIndex} className="bg-gray-50 rounded-lg p-3">
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-xs text-gray-500">
                          Bölüm {match.chunk_index + 1} • Konum: {match.position}
                        </span>
                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                          {Math.round(match.score * 100)}% eşleşme
                        </span>
                      </div>
                      
                      {/* Highlighted Context */}
                      <div className="text-sm text-gray-800">
                        <ReactMarkdown
                          components={{
                            strong: ({children}) => <mark className="bg-yellow-300 font-semibold">{children}</mark>,
                            p: ({children}) => <p className="leading-relaxed">{children}</p>
                          }}
                        >
                          {match.highlighted_context}
                        </ReactMarkdown>
                      </div>
                    </div>
                  ))}
                  
                  {/* Daha fazla eşleşme varsa göster */}
                  {result.matches.length > 3 && (
                    <div className="text-center">
                      <span className="text-sm text-gray-500">
                        ... ve {result.matches.length - 3} eşleşme daha
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchTab;