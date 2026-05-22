import React from 'react';

const Homepage = () => {
  return (
    <div className="terminal-container">
      <header style={{ marginBottom: '3rem' }}>
        <h1>Launchpad Job Alerts</h1>
        <p style={{ color: 'var(--success-color)' }}>Status: Active | Uptime: 99.9%</p>
        <p>Configure your tracking preferences below. The background daemon will automatically sync these settings.</p>
      </header>
      
      <main>
        {/* Components like ConfigForm will go here */}
        <p style={{ fontStyle: 'italic', color: 'gray' }}>[ Component mounts here ]</p>
      </main>
      
      <footer style={{ marginTop: '4rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem', fontSize: '0.9em' }}>
        <p>Type <span style={{ color: 'var(--accent-color)' }}>help</span> or <span style={{ color: 'var(--accent-color)' }}>man launchpad</span> for documentation.</p>
      </footer>
    </div>
  );
};

export default Homepage;
