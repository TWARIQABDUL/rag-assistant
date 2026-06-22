import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { MessageSquare, Upload, Server } from 'lucide-react';

const Navigation = () => {
  const [isOnline, setIsOnline] = useState(false);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        // Assuming API runs on port 8000
        const response = await fetch('http://localhost:8000/health');
        if (response.ok) {
          setIsOnline(true);
        } else {
          setIsOnline(false);
        }
      } catch (error) {
        setIsOnline(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, []);

  return (
    <nav className="glass" style={{ padding: '1rem 2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
        <h1 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: '#fff', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Server size={20} color="var(--primary)" />
          RAG Engine
        </h1>
        <div style={{ display: 'flex', gap: '1.5rem' }}>
          <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 500 }}>
            <MessageSquare size={18} /> Chat
          </NavLink>
          <NavLink to="/upload" className={({ isActive }) => isActive ? 'active' : ''} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 500 }}>
            <Upload size={18} /> Upload
          </NavLink>
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
        <div className={`status-dot ${!isOnline ? 'offline' : ''}`}></div>
        {isOnline ? 'System Online' : 'System Offline'}
      </div>
    </nav>
  );
};

export default Navigation;
