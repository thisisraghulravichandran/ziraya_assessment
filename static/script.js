
let currentFileId = null;
let selectedFile = null;

// DOM elements
const fileInput = document.getElementById('fileInput');
const uploadSection = document.getElementById('uploadSection');
const selectedFileDiv = document.getElementById('selectedFile');
const processButton = document.getElementById('processButton');
const loading = document.getElementById('loading');
const results = document.getElementById('results');
const complianceReport = document.getElementById('complianceReport');
const modifyButton = document.getElementById('modifyButton');
const downloadButton = document.getElementById('downloadButton');
const modifiedPreview = document.getElementById('modifiedPreview');
const alerts = document.getElementById('alerts');

// File input handling
fileInput.addEventListener('change', handleFileSelect);
processButton.addEventListener('click', processDocument);
modifyButton.addEventListener('click', modifyDocument);

// Drag and drop handling
uploadSection.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadSection.classList.add('dragover');
});

uploadSection.addEventListener('dragleave', () => {
    uploadSection.classList.remove('dragover');
});

uploadSection.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadSection.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
}

function handleFile(file) {
    selectedFile = file;
    
    // Validate file type
    const allowedTypes = ['.pdf', '.docx', '.doc'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!allowedTypes.includes(fileExtension)) {
        showAlert('Please select a PDF or Word document.', 'error');
        return;
    }

    // Validate file size (16MB)
    if (file.size > 16 * 1024 * 1024) {
        showAlert('File size must be less than 16MB.', 'error');
        return;
    }

    selectedFileDiv.innerHTML = `
        <strong>Selected:</strong> ${file.name} 
        <span style="color: #6c757d;">(${formatFileSize(file.size)})</span>
    `;
    selectedFileDiv.style.display = 'block';
    processButton.style.display = 'inline-block';
    processButton.disabled = false;
}

async function processDocument() {
    if (!selectedFile) {
        showAlert('Please select a file first.', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    processButton.disabled = true;
    loading.style.display = 'block';
    results.style.display = 'none';
    clearAlerts();

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Upload failed');
        }

        currentFileId = data.file_id;
        displayComplianceReport(data.compliance_report);
        results.style.display = 'block';
        showAlert('Document processed successfully!', 'success');

    } catch (error) {
        showAlert(`Error: ${error.message}`, 'error');
    } finally {
        loading.style.display = 'none';
        processButton.disabled = false;
    }
}

async function modifyDocument() {
    if (!currentFileId) {
        showAlert('No document to modify.', 'error');
        return;
    }

    modifyButton.disabled = true;
    modifyButton.textContent = '🔄 Processing...';

    try {
        const response = await fetch(`/modify/${currentFileId}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Modification failed');
        }

        showModifiedPreview(data.preview);
        downloadButton.href = `/download/${currentFileId}`;
        downloadButton.style.display = 'inline-block';
        showAlert('Document modified successfully!', 'success');

    } catch (error) {
        showAlert(`Error: ${error.message}`, 'error');
    } finally {
        modifyButton.disabled = false;
        modifyButton.textContent = '🔧 Fix Compliance Issues';
    }
}

function displayComplianceReport(report) {
    const statusClass = report.overall_compliance === 'COMPLIANT' ? 'compliant' : 'non-compliant';
    
    let violationsHtml = '';
    if (report.violations && report.violations.length > 0) {
        violationsHtml = `
            <div class="violations">
                <h4>Issues Found:</h4>
                ${report.violations.map(violation => `
                    <div class="violation">
                        <div class="violation-header">
                            ${violation.category}: ${violation.issue}
                            <span class="violation-severity severity-${violation.severity.toLowerCase()}">
                                ${violation.severity}
                            </span>
                        </div>
                        <div>Location: ${violation.location}</div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    let suggestionsHtml = '';
    if (report.suggestions && report.suggestions.length > 0) {
        suggestionsHtml = `
            <div class="suggestions">
                <h4>Suggestions for Improvement:</h4>
                <ul>
                    ${report.suggestions.map(suggestion => `<li>${suggestion}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    complianceReport.innerHTML = `
        <div class="compliance-header">
            <h3>Compliance Report</h3>
            <div class="compliance-status ${statusClass}">
                ${report.overall_compliance}
            </div>
            <div class="compliance-score">
                ${report.compliance_score}/100
            </div>
        </div>
        
        <div class="summary">
            <h4>Summary:</h4>
            <p>${report.summary}</p>
        </div>
        
        ${violationsHtml}
        ${suggestionsHtml}
    `;
}

function showModifiedPreview(preview) {
    modifiedPreview.innerHTML = `
        <h4>📝 Modified Document Preview:</h4>
        <div class="preview-text">${preview}</div>
    `;
    modifiedPreview.style.display = 'block';
}

function showAlert(message, type) {
    const alertClass = type === 'error' ? 'alert-error' : 'alert-success';
    const alertHtml = `
        <div class="alert ${alertClass}">
            ${message}
            <button onclick="this.parentElement.remove()" style="float: right; background: none; border: none; font-size: 1.2em; cursor: pointer;">&times;</button>
        </div>
    `;
    alerts.insertAdjacentHTML('afterbegin', alertHtml);

    // Auto-remove success alerts after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            const alert = alerts.querySelector('.alert-success');
            if (alert) alert.remove();
        }, 5000);
    }
}

function clearAlerts() {
    alerts.innerHTML = '';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Reset form when page loads
window.addEventListener('load', () => {
    selectedFile = null;
    currentFileId = null;
    results.style.display = 'none';
    loading.style.display = 'none';
    clearAlerts();
});