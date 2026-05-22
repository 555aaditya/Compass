import React from 'react';
import './AuthHeader.css';

const AuthHeader = () => {
  return (
    <div className="auth-header-container">
      <div className="auth-logo">&gt; launchpad_</div>
      <div className="auth-actions">
        <span style={{ fontSize: '0.9em', color: '#8b949e' }}>Authenticate:</span>
        <button className="auth-btn">GitHub</button>
        <button className="auth-btn">Google</button>
        <button className="auth-btn primary">Email OTP</button>
      </div>
    </div>
  );
};

export default AuthHeader;
