import React, { useState, useEffect, useCallback, useMemo } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Компонент кнопки избранного
const FavoriteButton = ({ isFavorite, onToggle, objectionId }) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleToggle = async () => {
    setIsLoading(true);
    try {
      await axios.post(`${API}/objections/${objectionId}/toggle-favorite`);
      onToggle();
    } catch (error) {
      console.error('Ошибка при переключении избранного:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      onClick={handleToggle}
      disabled={isLoading}
      className="ml-2 text-yellow-400 hover:text-yellow-300 disabled:opacity-50"
      aria-label={isFavorite ? 'Удалить из избранного' : 'Добавить в избранное'}
    >
      {isFavorite ? '★' : '☆'}
    </button>
  );
};

// Компонент кнопки копирования
const CopyButton = ({ text }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Ошибка при копировании:', error);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className={`ml-2 px-3 py-1 rounded text-sm transition-colors ${
        copied 
          ? 'bg-green-600 text-white' 
          : 'bg-gray-600 text-white hover:bg-gray-500'
      }`}
    >
      {copied ? 'Скопировано!' : 'Копировать'}
    </button>
  );
};

// Компонент цитаты
const QuoteCard = ({ quote, theme }) => (
  <div className={`quote ${theme === 'light' ? 'light' : ''} animate-fade-in`}>
    <div className="quote-text">"{quote.text}"</div>
    <div className="quote-author">-- {quote.author}</div>
  </div>
);

// Компонент возражения
const ObjectionCard = ({ objection, theme, onFavoriteToggle }) => {
  const incrementUsage = async () => {
    try {
      await axios.post(`${API}/objections/${objection.id}/increment-usage`);
    } catch (error) {
      console.error('Ошибка при увеличении счетчика:', error);
    }
  };

  const handleResponseCopy = (responseText) => {
    incrementUsage();
  };

  return (
    <div className="mb-6 p-6 bg-white bg-opacity-10 rounded-lg backdrop-blur-sm">
      <div className="objection-title flex items-center justify-between mb-4">
        <h3 className="text-xl font-bold text-blue-300">{objection.title}</h3>
        <div className="flex items-center">
          <FavoriteButton
            isFavorite={objection.is_favorite}
            onToggle={() => onFavoriteToggle(objection.id)}
            objectionId={objection.id}
          />
          {objection.usage_count > 0 && (
            <span className="ml-2 text-sm text-gray-400">
              Использовано: {objection.usage_count}
            </span>
          )}
        </div>
      </div>
      
      <div className="space-y-4">
        {objection.responses.map((response, index) => (
          <div key={response.id || index} className="border-l-4 border-blue-500 pl-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <strong className="text-blue-200">Вариант {index + 1}:</strong>
                <p className="mt-1 text-gray-100">{response.text}</p>
              </div>
              <CopyButton
                text={response.text}
                onCopy={() => handleResponseCopy(response.text)}
              />
            </div>
          </div>
        ))}
      </div>
      
      {objection.tags && objection.tags.length > 0 && (
        <div className="mt-4">
          <div className="flex flex-wrap gap-2">
            {objection.tags.map((tag, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-blue-600 text-white text-xs rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

function App() {
  const [objections, setObjections] = useState([]);
  const [quotes, setQuotes] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentView, setCurrentView] = useState('objections'); // 'objections' | 'quotes'
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [theme, setTheme] = useState('dark');
  const [isLoading, setIsLoading] = useState(false);
  const [randomMotto, setRandomMotto] = useState('');
  const [currentPage, setCurrentPage] = useState(0);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const perPage = 10;

  // Инициализация данных при первой загрузке
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Инициализация базы данных
        await axios.post(`${API}/initialize-data`);
        
        // Загрузка данных
        await Promise.all([
          fetchObjections(),
          fetchQuotes()
        ]);
      } catch (error) {
        console.error('Ошибка при инициализации:', error);
      }
    };

    initializeApp();
  }, []);

  // Установка случайного девиза
  useEffect(() => {
    if (quotes.length > 0) {
      const randomQuote = quotes[Math.floor(Math.random() * quotes.length)];
      setRandomMotto(`"${randomQuote.text}" -- ${randomQuote.author}`);
    }
  }, [quotes]);

  const fetchObjections = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append('search', searchTerm);
      if (showFavoritesOnly) params.append('favorites_only', 'true');

      const response = await axios.get(`${API}/objections?${params}`);
      setObjections(response.data);
    } catch (error) {
      console.error('Ошибка при загрузке возражений:', error);
    } finally {
      setIsLoading(false);
    }
  }, [searchTerm, showFavoritesOnly]);

  const fetchQuotes = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/quotes`);
      setQuotes(response.data);
    } catch (error) {
      console.error('Ошибка при загрузке цитат:', error);
    }
  }, []);

  // Обновление возражений при изменении фильтров
  useEffect(() => {
    fetchObjections();
    setCurrentPage(0);
  }, [fetchObjections]);

  // Генерация подсказок для поиска
  const generateSuggestions = useCallback((term) => {
    if (!term.trim()) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    const filtered = objections
      .filter(obj => 
        obj.title.toLowerCase().includes(term.toLowerCase()) ||
        obj.tags.some(tag => tag.toLowerCase().includes(term.toLowerCase()))
      )
      .slice(0, 5)
      .map(obj => obj.title);

    setSuggestions(filtered);
    setShowSuggestions(filtered.length > 0);
  }, [objections]);

  const handleSearchChange = (e) => {
    const value = e.target.value;
    setSearchTerm(value);
    generateSuggestions(value);
  };

  const handleSuggestionClick = (suggestion) => {
    setSearchTerm(suggestion);
    setShowSuggestions(false);
  };

  const handleFavoriteToggle = async (objectionId) => {
    // Обновляем локальное состояние
    setObjections(prev => 
      prev.map(obj => 
        obj.id === objectionId 
          ? { ...obj, is_favorite: !obj.is_favorite }
          : obj
      )
    );
  };

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  // Фильтрованные и пагинированные возражения
  const paginatedObjections = useMemo(() => {
    const startIndex = currentPage * perPage;
    return objections.slice(0, startIndex + perPage);
  }, [objections, currentPage]);

  const canLoadMore = useMemo(() => {
    return paginatedObjections.length < objections.length;
  }, [paginatedObjections.length, objections.length]);

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      theme === 'dark' 
        ? 'bg-gray-900 text-gray-100' 
        : 'bg-gray-100 text-gray-900'
    }`}>
      <div className="container mx-auto px-4 py-8 max-w-4xl relative">
        {/* Кнопка переключения темы */}
        <button
          onClick={toggleTheme}
          className="absolute top-4 right-4 p-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-white"
          aria-label={theme === 'dark' ? 'Включить светлую тему' : 'Включить тёмную тему'}
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>

        {/* Заголовок */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-4 text-white drop-shadow-lg">
            ПРОДАЖНИК
          </h1>
          
          {/* Девиз */}
          {randomMotto && (
            <div className="motto bg-blue-600 bg-opacity-20 p-4 rounded-lg border-b-2 border-blue-400 relative animate-slide-in">
              <p className="text-lg text-blue-300 italic">
                {randomMotto}
              </p>
              <span className="absolute right-4 bottom-0 text-blue-400 text-xl">❞</span>
            </div>
          )}
        </div>

        {/* Навигация */}
        <div className="flex flex-wrap gap-4 mb-6">
          <button
            onClick={() => {
              setCurrentView('objections');
              setShowFavoritesOnly(false);
            }}
            className={`px-4 py-2 rounded-lg transition-colors ${
              currentView === 'objections' && !showFavoritesOnly
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Все возражения
          </button>
          
          <button
            onClick={() => {
              setCurrentView('objections');
              setShowFavoritesOnly(true);
            }}
            className={`px-4 py-2 rounded-lg transition-colors ${
              currentView === 'objections' && showFavoritesOnly
                ? 'bg-yellow-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            ★ Избранные
          </button>
          
          <button
            onClick={() => {
              setCurrentView('quotes');
              setShowFavoritesOnly(false);
            }}
            className={`px-4 py-2 rounded-lg transition-colors ${
              currentView === 'quotes'
                ? 'bg-green-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            💬 Цитаты
          </button>
        </div>

        {/* Поиск (только для возражений) */}
        {currentView === 'objections' && (
          <div className="relative mb-6">
            <input
              type="text"
              placeholder="Введите ключевое слово (например, дорого)"
              value={searchTerm}
              onChange={handleSearchChange}
              className="w-full px-4 py-3 rounded-lg bg-gray-800 text-white border border-gray-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            
            {/* Подсказки */}
            {showSuggestions && suggestions.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-gray-800 border border-gray-600 rounded-lg shadow-lg">
                {suggestions.map((suggestion, index) => (
                  <div
                    key={index}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="px-4 py-2 hover:bg-gray-700 cursor-pointer border-b border-gray-600 last:border-b-0"
                  >
                    {suggestion}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Контент */}
        <div className="space-y-6">
          {currentView === 'objections' ? (
            <>
              {isLoading ? (
                <div className="text-center py-8">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                  <p className="mt-2">Загрузка...</p>
                </div>
              ) : paginatedObjections.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-400">
                    {searchTerm || showFavoritesOnly
                      ? 'Ничего не найдено. Попробуйте изменить поисковый запрос.'
                      : 'Возражения не найдены.'}
                  </p>
                </div>
              ) : (
                <>
                  {paginatedObjections.map((objection) => (
                    <ObjectionCard
                      key={objection.id}
                      objection={objection}
                      theme={theme}
                      onFavoriteToggle={handleFavoriteToggle}
                    />
                  ))}
                  
                  {canLoadMore && (
                    <div className="text-center">
                      <button
                        onClick={() => setCurrentPage(prev => prev + 1)}
                        className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        Показать ещё
                      </button>
                    </div>
                  )}
                </>
              )}
            </>
          ) : (
            <div className="space-y-4">
              <h2 className="text-2xl font-bold mb-4">Мудрые фразы для продаж</h2>
              {quotes.map((quote, index) => (
                <QuoteCard key={quote.id || index} quote={quote} theme={theme} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
