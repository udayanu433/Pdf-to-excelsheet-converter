import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';

const SemesterSelect = () => {
  const { year } = useParams(); // Gets '2019' or '2024' from the URL
  const navigate = useNavigate();
  const semesters = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8'];

  return (
    <div style={{ padding: '50px', textAlign: 'center', backgroundColor: '#f9f9f9', minHeight: '100vh' }}>
      <h2 style={{ color: '#34495e', marginBottom: '10px' }}>{year} Scheme</h2>
      <p style={{ marginBottom: '40px', fontSize: '1.2rem' }}>Select the Semester</p>
      
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', 
        gap: '20px', 
        maxWidth: '800px', 
        margin: '0 auto' 
      }}>
        {semesters.map((sem) => (
          <button
            key={sem}
            onClick={() => navigate(`/converter/${year}/${sem}`)}
            style={{
              padding: '20px',
              fontSize: '20px',
              fontWeight: 'bold',
              backgroundColor: '#3498db',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
            }}
          >
            {sem}
          </button>
        ))}
      </div>
      <button 
        onClick={() => navigate('/')}
        style={{ marginTop: '50px', background: 'none', border: 'none', color: '#7f8c8d', cursor: 'pointer', textDecoration: 'underline' }}
      >
        Go Back to Home
      </button>
    </div>
  );
};

export default SemesterSelect;