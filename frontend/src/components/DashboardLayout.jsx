import React from 'react';
import './DashboardLayout.css';

const DashboardLayout = ({ header, leftCol, rightCol, footer }) => {
  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        {header || <div>&gt; launchpad_ v1.0</div>}
      </header>
      <main className="dashboard-main">
        <aside className="dashboard-left-col">
          {leftCol || <div>[ Filter Configuration ]</div>}
        </aside>
        <section className="dashboard-right-col">
          {rightCol || <div>[ Company Selection ]</div>}
        </section>
      </main>
      <footer className="dashboard-footer">
        {footer || <div>Status: Waiting for configuration...</div>}
      </footer>
    </div>
  );
};

export default DashboardLayout;
