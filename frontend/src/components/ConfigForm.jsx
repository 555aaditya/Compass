import React, { useState } from 'react';

const ConfigForm = () => {
  const [email, setEmail] = useState('');
  const [titles, setTitles] = useState('');
  
  const handleSubmit = (e) => {
    e.preventDefault();
    console.log({ email, titles });
    alert('Config saved! (Mock)');
  };

  return (
    <div style={{
      border: '1px solid var(--border-color)',
      padding: '2rem',
      backgroundColor: '#161b22',
      marginBottom: '2rem'
    }}>
      <h2 style={{ marginTop: 0 }}>&gt; configure_alerts.sh</h2>
      
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <label htmlFor="email">Email Address</label>
          <input 
            type="email" 
            id="email" 
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com" 
            required
          />
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <label htmlFor="titles">Job Titles (comma separated)</label>
          <textarea 
            id="titles" 
            rows="3" 
            value={titles}
            onChange={(e) => setTitles(e.target.value)}
            placeholder="Software Engineer, Frontend Developer..." 
            required
          />
        </div>
        
        <button type="submit" style={{ alignSelf: 'flex-start' }}>
          [Save Configuration]
        </button>
      </form>
    </div>
  );
};

export default ConfigForm;
