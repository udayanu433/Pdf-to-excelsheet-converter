import React, { useState } from 'react';
import './ExcelGenerator.css'; // Import the new styles

const BACKEND_URL = 'http://localhost:8000/generate-excel/';

export default function ExcelGenerator() {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState('');
  const [statusType, setStatusType] = useState(''); // 'success', 'error', or 'loading'
  const [isLoading, setIsLoading] = useState(false);

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      if (selectedFile.type === 'application/pdf' || selectedFile.name.endsWith('.txt')) {
        setFile(selectedFile);
        setMessage(''); // Clear previous messages
        setStatusType('');
      } else {
        setFile(null);
        setMessage('⚠️ Please select a valid PDF file.');
        setStatusType('error');
      }
    }
  };

  const handleConvert = async () => {
    if (!file) {
      setMessage('Please select a file to upload.');
      setStatusType('error');
      return;
    }

    setIsLoading(true);
    setMessage('Processing file... This may take a moment.');
    setStatusType('loading');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(BACKEND_URL, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const blob = await response.blob();
        let filename = 'converted_result.xlsx';
        const contentDisposition = response.headers.get('Content-Disposition');
        if (contentDisposition) {
          const match = contentDisposition.match(/filename="?(.+)"?/);
          if (match && match[1]) filename = match[1];
        }

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);

        setMessage(`✅ Success! Downloaded: ${filename}`);
        setStatusType('success');
      } else {
        let errorMsg = `Server Error (${response.status})`;
        try {
          const errorData = await response.json();
          if (errorData.detail) errorMsg = errorData.detail;
        } catch (e) {}
        setMessage(`❌ Failed: ${errorMsg}`);
        setStatusType('error');
      }
    } catch (error) {
      setMessage(`❌ Network Error: Is the backend running?`);
      setStatusType('error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="converter-card">
      <h2>📄 PDF to Excel</h2>
      <p>Convert your semester results instantly.</p>

      <div className="file-upload-wrapper">
        <input 
          type="file" 
          id="fileInput" 
          className="file-input" 
          accept=".pdf,.txt" 
          onChange={handleFileChange} 
        />
        <label htmlFor="fileInput" className="file-label">
          <span className="icon">📂</span>
          <span>{file ? 'Change File' : 'Click to Upload PDF'}</span>
          {file && <div className="file-name">{file.name}</div>}
        </label>
      </div>

      <button 
        className="convert-btn" 
        onClick={handleConvert} 
        disabled={!file || isLoading}
      >
        {isLoading ? (
          <>
            <span className="spinner"></span> Converting...
          </>
        ) : (
          'Convert Now'
        )}
      </button>

      {message && (
        <div className={`status-box ${statusType}`}>
          {message}
        </div>
      )}
    </div>
  );
}