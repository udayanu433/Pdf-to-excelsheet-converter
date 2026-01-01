import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './ExcelGenerator.css'; 

// Replace this with your actual Render/Backend URL
const BACKEND_URL = 'https://pdf-to-excelsheet-converter-api.onrender.com/generate-excel/';

export default function ExcelGenerator() {
  const { year, semester } = useParams(); // Retrieves scheme (2019/2024) and semester (S1-S8)
  const navigate = useNavigate();
  
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState('');
  const [statusType, setStatusType] = useState(''); 
  const [isLoading, setIsLoading] = useState(false);

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      if (selectedFile.type === 'application/pdf' || selectedFile.name.endsWith('.txt')) {
        setFile(selectedFile);
        setMessage(''); 
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
    setMessage(`Processing ${semester} (${year} Scheme)...`);
    setStatusType('loading');

    const formData = new FormData();
    formData.append('file', file);
    
    // Sending the scheme and semester as additional form data
    formData.append('scheme', year);
    formData.append('semester', semester);

    try {
      const response = await fetch(BACKEND_URL, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const blob = await response.blob();
        let filename = `${year}_${semester}_Results.xlsx`;
        
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

        setMessage(`✅ Success! Excel downloaded for ${semester}.`);
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
      <button 
        onClick={() => navigate(-1)} 
        style={{ float: 'left', border: 'none', background: 'none', cursor: 'pointer', color: '#3498db' }}
      >
        ← Back
      </button>
      
      <h2>📄 {semester} Converter</h2>
      <p style={{ fontWeight: 'bold', color: '#2c3e50' }}>{year} Scheme</p>
      <p>Upload the result PDF to generate your Excel sheet with SGPA calculation.</p>

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

      <div style={{ marginTop: '20px', fontSize: '12px', color: '#7f8c8d', borderTop: '1px solid #eee', paddingTop: '10px' }}>
        * SGPA calculation is based on the official KTU {year} Curriculum. [cite: 10, 1342]
      </div>
    </div>
  );
}
