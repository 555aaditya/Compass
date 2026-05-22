import React from 'react';
import './CompanyGrid.css';

const companyCategories = [
  {
    title: 'Tier 1 / FAANG-adjacent',
    companies: ['Databricks', 'Figma', 'Stripe', 'Notion']
  },
  {
    title: 'Artificial Intelligence',
    companies: ['Anthropic', 'OpenAI', 'HuggingFace', 'Midjourney']
  },
  {
    title: 'FinTech & Crypto',
    companies: ['Plaid', 'Coinbase', 'Robinhood', 'Ramp']
  },
  {
    title: 'High-Growth Remote',
    companies: ['Zapier', 'GitLab', 'Vercel', 'Linear']
  },
  {
    title: 'Web3 & Blockchain',
    companies: ['Chainlink', 'Polygon', 'Consensys', 'Alchemy']
  }
];

const CompanyGrid = () => {
  return (
    <div className="company-grid-container">
      {companyCategories.map((category, idx) => (
        <div key={idx} className="company-category">
          <div className="company-category-title">
            <span>&gt;</span> {category.title}
          </div>
          <div className="company-items">
            {category.companies.map((company, cIdx) => (
              <label key={cIdx} className="company-checkbox">
                <input type="checkbox" /> {company}
              </label>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export default CompanyGrid;
