import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Bot, User, FileText } from 'lucide-react';

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userQuery = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userQuery }]);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/v1/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: userQuery, max_sources: 3 })
      });

      if (!response.ok) throw new Error('API request failed');
      
      const data = await response.json();
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: data.answer,
        sources: data.sources,
        time: data.execution_time_seconds
      }]);
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'system', 
        content: 'Failed to connect to the RAG Engine. Is the backend running?' 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%', overflow: 'hidden' }}>
      
      {/* Header */}
      <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border-color)', background: 'rgba(0,0,0,0.2)' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 600, margin: 0 }}>Secure RAG Interface</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>Ask questions based on indexed government documents.</p>
      </div>

      {/* Chat History */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {messages.length === 0 && (
          <div style={{ margin: 'auto', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Bot size={48} style={{ opacity: 0.2, marginBottom: '1rem' }} />
            <p>How can I assist you today?</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className="animate-fade-in" style={{ display: 'flex', gap: '1rem', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
            
            {/* Avatar */}
            <div style={{ 
              width: '40px', height: '40px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              background: msg.role === 'user' ? 'var(--primary)' : msg.role === 'assistant' ? '#334155' : '#ef4444' 
            }}>
              {msg.role === 'user' ? <User size={20} color="white" /> : <Bot size={20} color={msg.role === 'system' ? 'white' : 'var(--primary)'} />}
            </div>

            {/* Bubble */}
            <div style={{ 
              maxWidth: '75%', 
              background: msg.role === 'user' ? 'rgba(14, 165, 233, 0.1)' : 'rgba(255, 255, 255, 0.05)',
              border: `1px solid ${msg.role === 'user' ? 'rgba(14, 165, 233, 0.2)' : 'rgba(255, 255, 255, 0.1)'}`,
              padding: '1.25rem',
              borderRadius: '16px',
              borderTopRightRadius: msg.role === 'user' ? '4px' : '16px',
              borderTopLeftRadius: msg.role === 'assistant' || msg.role === 'system' ? '4px' : '16px',
            }}>
              <p style={{ lineHeight: 1.6, whiteSpace: 'pre-wrap', margin: 0 }}>{msg.content}</p>
              
              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                  <p style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: '0.75rem', fontWeight: 600 }}>Sources Cited</p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {msg.sources.map((source, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(0,0,0,0.3)', padding: '0.5rem 0.75rem', borderRadius: '8px', fontSize: '0.8rem', border: '1px solid rgba(255,255,255,0.05)' }}>
                        <FileText size={14} color="var(--primary)" />
                        <span>{source.title || source.source_file || source.id}</span>
                      </div>
                    ))}
                  </div>
                  {msg.time && <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.75rem', textAlign: 'right' }}>Generated in {msg.time}s</p>}
                </div>
              )}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="animate-fade-in" style={{ display: 'flex', gap: '1rem' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: '#334155', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Bot size={20} color="var(--primary)" />
            </div>
            <div style={{ padding: '1.25rem', background: 'rgba(255,255,255,0.05)', borderRadius: '16px', borderTopLeftRadius: '4px', border: '1px solid rgba(255,255,255,0.1)' }}>
              <Loader2 className="lucide-spin" size={20} color="var(--primary)" style={{ animation: 'spin 1s linear infinite' }} />
              <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div style={{ padding: '1.5rem', borderTop: '1px solid var(--border-color)', background: 'rgba(0,0,0,0.2)' }}>
        <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '1rem', position: 'relative' }}>
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about the documents..."
            disabled={isLoading}
            style={{
              flex: 1,
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid var(--border-color)',
              borderRadius: '12px',
              padding: '1rem 1.25rem',
              paddingRight: '4rem',
              color: 'var(--text-main)',
              fontSize: '1rem',
              outline: 'none',
              transition: 'border-color 0.2s',
            }}
            onFocus={(e) => e.target.style.borderColor = 'var(--primary)'}
            onBlur={(e) => e.target.style.borderColor = 'var(--border-color)'}
          />
          <button 
            type="submit" 
            disabled={!input.trim() || isLoading}
            style={{
              position: 'absolute',
              right: '0.5rem',
              top: '50%',
              transform: 'translateY(-50%)',
              width: '40px',
              height: '40px',
              padding: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '8px'
            }}
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatPage;
