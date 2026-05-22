import React, { useState } from 'react';
import './FilterSidebar.css';

const MOCK_TITLES = [
  'SDE', 'SDE Intern', 'SDE I', 'SDE II', 'SDE III', 
  'Frontend Engineer', 'Backend Engineer', 'Staff Backend Engineer',
  'Data Scientist', 'Product Manager', 'DevOps Engineer'
];

const FilterSidebar = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTitles, setSelectedTitles] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);

  const filteredTitles = MOCK_TITLES.filter(t => 
    t.toLowerCase().includes(searchTerm.toLowerCase()) && !selectedTitles.includes(t)
  );

  const addTitle = (title) => {
    setSelectedTitles([...selectedTitles, title]);
    setSearchTerm('');
    setShowDropdown(false);
  };

  const removeTitle = (title) => {
    setSelectedTitles(selectedTitles.filter(t => t !== title));
  };

  return (
    <div className="filter-sidebar">
      
      <div className="filter-group">
        <div className="filter-title">Roles & Keywords</div>
        <div className="filter-input-wrapper">
          <label>Job Titles</label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '0.4rem' }}>
            {selectedTitles.map(t => (
              <span key={t} style={{ background: 'rgba(88, 166, 255, 0.1)', border: '1px solid #58a6ff', color: '#58a6ff', padding: '0.1rem 0.4rem', borderRadius: '4px', fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                {t} <span style={{ cursor: 'pointer', fontWeight: 'bold' }} onClick={() => removeTitle(t)}>x</span>
              </span>
            ))}
          </div>
          <input 
            className="filter-input" 
            type="text" 
            placeholder="Type to search roles... (e.g. SDE)" 
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setShowDropdown(true);
            }}
            onFocus={() => setShowDropdown(true)}
          />
          {showDropdown && searchTerm && filteredTitles.length > 0 && (
            <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, background: '#161b22', border: '1px solid #30363d', zIndex: 10, maxHeight: '150px', overflowY: 'auto' }}>
              {filteredTitles.map(t => (
                <div 
                  key={t} 
                  onClick={() => addTitle(t)}
                  style={{ padding: '0.4rem', cursor: 'pointer', fontSize: '0.8rem', borderBottom: '1px solid #30363d' }}
                  onMouseEnter={(e) => e.target.style.background = '#30363d'}
                  onMouseLeave={(e) => e.target.style.background = 'transparent'}
                >
                  {t}
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="filter-input-wrapper" style={{ marginTop: '0.5rem' }}>
          <label>Must-have Keywords</label>
          <input className="filter-input" type="text" placeholder="React, Python, Go" />
        </div>
      </div>

      <div className="filter-group">
        <div className="filter-title">Seniority</div>
        <label className="filter-checkbox"><input type="checkbox" /> Intern / Fresher</label>
        <label className="filter-checkbox"><input type="checkbox" /> Junior / Entry Level</label>
        <label className="filter-checkbox"><input type="checkbox" /> Mid Level</label>
        <label className="filter-checkbox"><input type="checkbox" /> Senior</label>
        <label className="filter-checkbox"><input type="checkbox" /> Lead / Staff / Manager</label>
      </div>

      <div className="filter-group">
        <div className="filter-title">Locations</div>
        <label className="filter-checkbox">
          <input type="checkbox" defaultChecked /> Remote Only
        </label>
        <div className="filter-input-wrapper" style={{ marginTop: '0.5rem' }}>
          <label>Specific Cities / Countries</label>
          <input className="filter-input" type="text" placeholder="New York, India, London" />
        </div>
      </div>

      <div className="filter-group">
        <div className="filter-title">Alert Settings</div>
        <div className="filter-input-wrapper">
          <label>Delivery Email</label>
          <input className="filter-input" type="email" placeholder="you@example.com" />
        </div>
        <div className="filter-input-wrapper">
          <label>Frequency</label>
          <select className="filter-input">
            <option>Instant (ASAP)</option>
            <option>Daily Digest</option>
            <option>Weekly Summary</option>
          </select>
        </div>
      </div>

    </div>
  );
};

export default FilterSidebar;
