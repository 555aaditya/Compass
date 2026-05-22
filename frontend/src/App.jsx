import React from 'react';
import DashboardLayout from './components/DashboardLayout';
import AuthHeader from './components/AuthHeader';
import FilterSidebar from './components/FilterSidebar';
import CompanyGrid from './components/CompanyGrid';
import './theme.css';
import './App.css';

function App() {
  return (
    <DashboardLayout 
      header={<AuthHeader />}
      leftCol={<FilterSidebar />}
      rightCol={<CompanyGrid />}
      footer={
        <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
          <span style={{ color: '#8b949e' }}>Status: Ready</span>
          <button style={{ 
            backgroundColor: 'rgba(88, 166, 255, 0.1)', 
            border: '1px solid #58a6ff', 
            color: '#58a6ff',
            padding: '0.5rem 2rem',
            cursor: 'pointer',
            fontFamily: 'inherit'
          }}>
            [ Initialize Tracking ]
          </button>
        </div>
      }
    />
  );
}

export default App;
