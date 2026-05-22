import React from 'react';

const Navbar = () => {
  return (
    <nav style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '1rem 0',
      borderBottom: '1px solid var(--border-color)',
      marginBottom: '2rem'
    }}>
      <div style={{ fontWeight: 'bold', color: 'var(--success-color)' }}>
        ~$ launchpad
      </div>
      <div style={{ display: 'flex', gap: '1rem' }}>
        <a href="#config">Config</a>
        <a href="#companies">Companies</a>
      </div>
    </nav>
  );
};

export default Navbar;
