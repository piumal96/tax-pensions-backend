// Retirement Planner Web App - Frontend Script

// DOM Elements
const tabButtons = document.querySelectorAll('.tab-button');
const tabContents = document.querySelectorAll('.tab-content');
const csvFile = document.getElementById('csvFile');
const uploadArea = document.getElementById('uploadArea');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const runSimulationUploadBtn = document.getElementById('runSimulationUpload');
const parametersForm = document.getElementById('parametersForm');
const loadingSpinner = document.getElementById('loadingSpinner');
const errorMessage = document.getElementById('errorMessage');
const resultsSection = document.getElementById('resultsSection');
const resultsContainer = document.getElementById('resultsContainer');

let selectedFile = null;

// Tab Navigation
tabButtons.forEach(button => {
    button.addEventListener('click', () => {
        const tabName = button.dataset.tab;
        
        // Remove active class from all buttons and contents
        tabButtons.forEach(btn => btn.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));
        
        // Add active class to clicked button and corresponding content
        button.classList.add('active');
        document.getElementById(tabName).classList.add('active');
    });
});

// File Upload Handling
uploadArea.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    csvFile.click();
});

csvFile.addEventListener('click', (e) => {
    e.stopPropagation();
});

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});

csvFile.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

function handleFileSelect(file) {
    if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
        showError('Please select a valid CSV file.');
        return;
    }
    
    selectedFile = file;
    fileName.textContent = file.name;
    fileInfo.style.display = 'block';
    hideError();
}

// Run Simulation from Upload
runSimulationUploadBtn.addEventListener('click', () => {
    if (!selectedFile) {
        showError('Please select a CSV file first.');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    runSimulation(formData);
});

// Run Simulation from Form
parametersForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const formData = new FormData(parametersForm);
    runSimulation(formData);
});

function runSimulation(data) {
    loadingSpinner.style.display = 'flex';
    hideError();
    
    fetch('/api/run-simulation', {
        method: 'POST',
        body: data
    })
    .then(response => response.json())
    .then(result => {
        loadingSpinner.style.display = 'none';
        
        if (result.success) {
            displayResults(result.results, result.columns);
        } else {
            showError(result.error || 'An error occurred during simulation.');
        }
    })
    .catch(error => {
        loadingSpinner.style.display = 'none';
        showError('Network error: ' + error.message);
    });
}

function displayResults(data, columns) {
    // Use the columns array returned from the API (which has the correct order)
    // columns is an array in the correct order: ['Year', 'P1_Age', 'P2_Age', ...]
    
    // Create table
    let html = '<div class="table-wrapper"><table>';
    
    // Headers - use the columns array for proper order
    html += '<thead><tr>';
    columns.forEach(col => {
        html += `<th>${col}</th>`;
    });
    html += '</tr></thead>';
    
    // Body
    html += '<tbody>';
    data.forEach((row, idx) => {
        html += '<tr>';
        columns.forEach(col => {
            const value = row[col];
            const isNumeric = typeof value === 'number' && !['Year', 'P1_Age', 'P2_Age'].includes(col);
            const cellClass = isNumeric ? 'numeric' : '';
            
            let displayValue = value;
            if (isNumeric) {
                displayValue = Number(value).toLocaleString('en-US', {
                    maximumFractionDigits: 0
                });
            }
            
            html += `<td class="${cellClass}">${displayValue}</td>`;
        });
        html += '</tr>';
    });
    html += '</tbody>';
    html += '</table></div>';
    
    // Summary Stats
    if (data.length > 0) {
        const lastYear = data[data.length - 1];
        const summary = `
            <div class="summary-stats">
                <h3>Summary</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">
                    <div class="stat-card">
                        <div class="stat-label">Final Net Worth</div>
                        <div class="stat-value">$${Number(lastYear.Net_Worth).toLocaleString('en-US', {maximumFractionDigits: 0})}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Final Year</div>
                        <div class="stat-value">${lastYear.Year}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Total Tax Paid</div>
                        <div class="stat-value">$${data.reduce((sum, row) => sum + (row.Taxes_Paid || 0), 0).toLocaleString('en-US', {maximumFractionDigits: 0})}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Total Roth Conversions</div>
                        <div class="stat-value">$${data.reduce((sum, row) => sum + (row.Roth_Conversion || 0), 0).toLocaleString('en-US', {maximumFractionDigits: 0})}</div>
                    </div>
                </div>
            </div>
        `;
        html = summary + html;
    }
    
    // Add download button
    html += `
        <button class="btn btn-secondary mt-20" onclick="downloadResults()">📥 Download Results as CSV</button>
    `;
    
    resultsContainer.innerHTML = html;
    resultsSection.style.display = 'block';
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    // Store results and columns for download
    window.lastResults = data;
    window.lastResultsColumns = columns;  // Store the columns array with correct order
    
    // Store last run config
    const formData = new FormData(parametersForm);
    const config = {};
    for (let [key, value] of formData.entries()) {
        config[key] = value;
    }
    localStorage.setItem('lastRunConfig', JSON.stringify(config));
}

function downloadResults() {
    if (!window.lastResults) return;
    
    // Use the columns array that was stored (has correct order from API)
    const results = window.lastResults;
    const columns = window.lastResultsColumns || Object.keys(results[0]);
    
    let csv = columns.join(',') + '\n';
    results.forEach(row => {
        const values = columns.map(col => {
            const value = row[col];
            // Escape values that contain commas or quotes
            if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                return `"${value.replace(/"/g, '""')}"`;
            }
            return value;
        });
        csv += values.join(',') + '\n';
    });
    
    // Create download link
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `retirement_plan_results_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
}

function hideError() {
    errorMessage.style.display = 'none';
}

// Initialize - load form defaults on page load
document.addEventListener('DOMContentLoaded', () => {
    loadFormDefaults();
});

function loadFormDefaults() {
    // Try to load last run config first, otherwise load sample config
    const lastRunConfig = localStorage.getItem('lastRunConfig');
    
    if (lastRunConfig) {
        try {
            const config = JSON.parse(lastRunConfig);
            for (let [key, value] of Object.entries(config)) {
                const input = document.querySelector(`[name="${key}"]`);
                if (input) {
                    input.value = value;
                }
            }
            return; // Successfully loaded last run config
        } catch (e) {
            console.log('Could not parse last run config');
        }
    }
    
    // Load sample config as fallback
    fetch('/api/sample-config')
        .then(response => response.json())
        .then(result => {
            if (result.success && result.config) {
                // Pre-populate form with sample values
                result.config.forEach(item => {
                    const input = document.querySelector(`[name="${item.parameter}"]`);
                    if (input) {
                        input.value = item.value;
                    }
                });
            }
        })
        .catch(error => console.log('Could not load sample config:', error));
}

// Add some CSS for summary stats dynamically
const style = document.createElement('style');
style.textContent = `
    .summary-stats {
        background: #f0f8ff;
        border-left: 4px solid #3498db;
        padding: 20px;
        margin-bottom: 20px;
        border-radius: 5px;
    }
    
    .summary-stats h3 {
        color: var(--primary-color);
        margin-bottom: 15px;
    }
    
    .stat-card {
        background: white;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #ecf0f1;
    }
    
    .stat-label {
        color: #7f8c8d;
        font-size: 0.9em;
        margin-bottom: 8px;
    }
    
    .stat-value {
        font-size: 1.5em;
        font-weight: 700;
        color: var(--secondary-color);
    }

    .mt-20 {
        margin-top: 20px;
    }
`;
document.head.appendChild(style);
