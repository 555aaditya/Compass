import React from 'react';
import './FilterSidebar.css';

const FilterSidebar = () => {
  return (
    <div className="filter-sidebar">
      
      <div className="filter-group">
        <div className="filter-title">Roles & Keywords</div>
        <div className="filter-input-wrapper">
          <label>Job Titles (comma separated)</label>
          <input className="filter-input" type="text" placeholder="Software Engineer, Data Scientist" />
        </div>
        <div className="filter-input-wrapper">
          <label>Must-have Keywords</label>
          <input className="filter-input" type="text" placeholder="React, Python, Go" />
        </div>
        <div className="filter-input-wrapper">
          <label>Exclude Keywords</label>
          <input className="filter-input" type="text" placeholder="Senior, Manager, Staff" />
        </div>
      </div>

      <div className="filter-group">
        <div className="filter-title">Locations</div>
        <label className="filter-checkbox">
          <input type="checkbox" defaultChecked /> Remote Only
        </label>
        <div className="filter-input-wrapper">
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
