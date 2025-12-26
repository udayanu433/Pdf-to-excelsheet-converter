import React from 'react';
import { useNavigate } from 'react-router-dom';

const Home = () => {
  const navigate = useNavigate();

  return (
    <div style={{
      height: '100vh',
      backgroundImage: 'url("https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1920&q=80")', // Nature Image
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      textAlign: 'center',
      color: 'white',
      textShadow: '0 2px 4px rgba(0,0,0,0.5)'
    }}>
      <h1 style={{ fontSize: '3rem', marginBottom: '20px' }}>KTU Result Converter</h1>
      <p style={{ fontSize: '1.2rem', marginBottom: '40px' }}>Select your curriculum scheme to proceed</p>
      
      <div style={{ display: 'flex', gap: '20px' }}>
        <button 
          onClick={() => navigate('/scheme/2024')}
          style={buttonStyle}
        >
          2024 Scheme
        </button>
        <button 
          onClick={() => navigate('/scheme/2019')}
          style={buttonStyle}
        >
          2019 Scheme
        </button>
      </div>
    </div>
  );
};

const buttonStyle = {
  padding: '15px 40px',
  fontSize: '18px',
  fontWeight: 'bold',
  cursor: 'pointer',
  border: 'none',
  borderRadius: '50px',
  backgroundColor: 'rgba(255, 255, 255, 0.9)',
  color: '#2c3e50',
  transition: 'transform 0.2s',
  boxShadow: '0 4px 15px rgba(0,0,0,0.2)'
};

export default Home;