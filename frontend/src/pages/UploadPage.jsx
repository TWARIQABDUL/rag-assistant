import React, { useState, useCallback } from 'react';
import { UploadCloud, FileType, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

const UploadPage = () => {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState('idle'); // idle, uploading, success, error
  const [message, setMessage] = useState('');

  const onDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelection(e.target.files[0]);
    }
  };

  const handleFileSelection = (selectedFile) => {
    if (selectedFile.type !== 'application/pdf') {
      setStatus('error');
      setMessage('Only PDF files are supported.');
      setFile(null);
      return;
    }
    setFile(selectedFile);
    setStatus('idle');
    setMessage('');
  };

  const handleUpload = async () => {
    if (!file) return;

    setStatus('uploading');
    setMessage('Processing document and generating embeddings...');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/api/v1/ingest', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Upload failed');
      
      setStatus('success');
      setMessage(`Successfully ingested "${file.name}" into the vector database.`);
      setFile(null); // Reset form on success
    } catch (error) {
      setStatus('error');
      setMessage('Failed to upload document. Please check the backend connection.');
    }
  };

  return (
    <div style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="glass-panel" style={{ width: '100%', maxWidth: '600px', padding: '2.5rem' }}>
        
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '1.75rem', fontWeight: 600, margin: '0 0 0.5rem 0' }}>Knowledge Ingestion</h2>
          <p style={{ color: 'var(--text-muted)' }}>Upload PDF documents to expand the RAG Engine's knowledge base.</p>
        </div>

        {/* Drag & Drop Zone */}
        <div 
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          style={{
            border: `2px dashed ${isDragging ? 'var(--primary)' : 'var(--border-color)'}`,
            borderRadius: '16px',
            padding: '3rem 2rem',
            textAlign: 'center',
            background: isDragging ? 'rgba(14, 165, 233, 0.05)' : 'rgba(0,0,0,0.2)',
            transition: 'all 0.2s',
            cursor: 'pointer',
            marginBottom: '1.5rem'
          }}
          onClick={() => document.getElementById('file-upload').click()}
        >
          <input 
            id="file-upload" 
            type="file" 
            accept=".pdf" 
            style={{ display: 'none' }} 
            onChange={handleFileChange}
          />
          
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '64px', height: '64px', borderRadius: '50%', background: 'rgba(255,255,255,0.05)', marginBottom: '1rem' }}>
            <UploadCloud size={32} color={isDragging ? 'var(--primary)' : 'var(--text-muted)'} />
          </div>
          
          <h3 style={{ fontSize: '1.1rem', fontWeight: 500, marginBottom: '0.5rem' }}>
            {file ? file.name : 'Click or drag PDF here'}
          </h3>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
            {file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : 'Maximum file size 50MB'}
          </p>
        </div>

        {/* Status Messages */}
        {status !== 'idle' && (
          <div className="animate-fade-in" style={{ 
            display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem',
            background: status === 'error' ? 'rgba(239, 68, 68, 0.1)' : status === 'success' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(14, 165, 233, 0.1)',
            border: `1px solid ${status === 'error' ? 'rgba(239, 68, 68, 0.2)' : status === 'success' ? 'rgba(34, 197, 94, 0.2)' : 'rgba(14, 165, 233, 0.2)'}`
          }}>
            {status === 'uploading' && <Loader2 size={20} color="var(--primary)" style={{ animation: 'spin 1s linear infinite' }} />}
            {status === 'success' && <CheckCircle size={20} color="#22c55e" />}
            {status === 'error' && <AlertCircle size={20} color="#ef4444" />}
            
            <span style={{ fontSize: '0.9rem', color: status === 'error' ? '#fca5a5' : status === 'success' ? '#86efac' : '#bae6fd' }}>
              {message}
            </span>
          </div>
        )}

        {/* Upload Action */}
        <button 
          onClick={handleUpload} 
          disabled={!file || status === 'uploading'}
          style={{ width: '100%', padding: '1rem', fontSize: '1rem', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem' }}
        >
          {status === 'uploading' ? (
            <>Processing... <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /></>
          ) : (
            <>Ingest Document <FileType size={18} /></>
          )}
        </button>

      </div>
    </div>
  );
};

export default UploadPage;
