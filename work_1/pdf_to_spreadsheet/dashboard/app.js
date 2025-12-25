/**
 * PDF to Spreadsheet - Dashboard JavaScript
 * Handles file upload, progress tracking, and results display
 */

const API_BASE = '/api';

// State
let currentJobId = null;
let pollInterval = null;

// DOM Elements
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const parserType = document.getElementById('parserType');
const outputFormat = document.getElementById('outputFormat');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressTitle = document.getElementById('progressTitle');
const progressStatus = document.getElementById('progressStatus');
const progressFilename = document.getElementById('progressFilename');
const jobsList = document.getElementById('jobsList');
const refreshBtn = document.getElementById('refreshBtn');
const previewModal = document.getElementById('previewModal');
const previewTable = document.getElementById('previewTable');
const previewTitle = document.getElementById('previewTitle');
const closeModal = document.getElementById('closeModal');
const downloadBtn = document.getElementById('downloadBtn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupDropZone();
    setupEventListeners();
    loadJobs();
});

// ============================================
// Drop Zone Setup
// ============================================

function setupDropZone() {
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0 && files[0].type === 'application/pdf') {
            uploadFile(files[0]);
        } else {
            showNotification('Please drop a PDF file', 'error');
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadFile(e.target.files[0]);
        }
    });
}

// ============================================
// Event Listeners
// ============================================

function setupEventListeners() {
    refreshBtn.addEventListener('click', loadJobs);

    closeModal.addEventListener('click', () => {
        previewModal.classList.remove('active');
    });

    document.querySelector('.modal-overlay').addEventListener('click', () => {
        previewModal.classList.remove('active');
    });
}

// ============================================
// File Upload
// ============================================

async function uploadFile(file) {
    // Show progress section
    progressSection.style.display = 'block';
    progressBar.style.width = '0%';
    progressTitle.textContent = 'Uploading...';
    progressStatus.textContent = 'Uploading';
    progressFilename.textContent = file.name;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(
            `${API_BASE}/upload?parser_type=${parserType.value}&output_format=${outputFormat.value}`,
            {
                method: 'POST',
                body: formData
            }
        );

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const job = await response.json();
        currentJobId = job.job_id;

        progressBar.style.width = '5%';
        progressTitle.textContent = 'Processing...';
        progressStatus.textContent = 'Queued';

        // Start polling for status
        startPolling(job.job_id);

    } catch (error) {
        progressTitle.textContent = 'Upload Failed';
        progressStatus.textContent = 'Error';
        showNotification(error.message, 'error');
    }
}

// ============================================
// Job Status Polling
// ============================================

function startPolling(jobId) {
    if (pollInterval) {
        clearInterval(pollInterval);
    }

    pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/jobs/${jobId}`);
            const job = await response.json();

            // Update progress
            progressBar.style.width = `${job.progress}%`;
            progressStatus.textContent = capitalizeFirst(job.status);

            if (job.status === 'processing') {
                progressTitle.textContent = 'Processing PDF...';
            }

            if (job.status === 'completed') {
                clearInterval(pollInterval);
                progressTitle.textContent = 'Completed!';
                progressBar.style.width = '100%';

                setTimeout(() => {
                    progressSection.style.display = 'none';
                    loadJobs();
                    showNotification(`Extracted ${job.result.total_rows} rows`, 'success');
                }, 1500);
            }

            if (job.status === 'failed') {
                clearInterval(pollInterval);
                progressTitle.textContent = 'Processing Failed';
                showNotification(job.error || 'Unknown error', 'error');
            }

        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 1000);
}

// ============================================
// Load Jobs
// ============================================

async function loadJobs() {
    try {
        const response = await fetch(`${API_BASE}/jobs`);
        const data = await response.json();

        renderJobs(data.jobs || []);

    } catch (error) {
        console.error('Failed to load jobs:', error);
    }
}

function renderJobs(jobs) {
    if (jobs.length === 0) {
        jobsList.innerHTML = `
            <div class="empty-state">
                <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
                    <polyline points="13 2 13 9 20 9"/>
                </svg>
                <p>No files processed yet</p>
                <span>Upload a PDF to get started</span>
            </div>
        `;
        return;
    }

    // Sort by created_at descending
    jobs.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    jobsList.innerHTML = jobs.map(job => renderJobCard(job)).join('');

    // Add event listeners
    jobs.forEach(job => {
        if (job.status === 'completed') {
            const previewBtn = document.getElementById(`preview-${job.job_id}`);
            const downloadBtn = document.getElementById(`download-${job.job_id}`);

            if (previewBtn) {
                previewBtn.addEventListener('click', () => showPreview(job.job_id, job.filename));
            }
            if (downloadBtn) {
                downloadBtn.addEventListener('click', () => downloadFile(job.job_id));
            }
        }

        const deleteBtn = document.getElementById(`delete-${job.job_id}`);
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => deleteJob(job.job_id));
        }
    });
}

function renderJobCard(job) {
    const iconHtml = getStatusIcon(job.status);
    const timeAgo = getTimeAgo(job.created_at);

    let resultInfo = '';
    if (job.result) {
        resultInfo = `${job.result.total_rows} rows`;
    }

    let actionsHtml = '';
    if (job.status === 'completed') {
        actionsHtml = `
            <button class="btn btn-secondary" id="preview-${job.job_id}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                </svg>
                Preview
            </button>
            <button class="btn btn-primary" id="download-${job.job_id}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                Download
            </button>
        `;
    } else if (job.status === 'processing') {
        actionsHtml = `
            <span class="loading" style="color: var(--accent-primary);">Processing...</span>
        `;
    }

    actionsHtml += `
        <button class="btn btn-icon" id="delete-${job.job_id}" title="Delete">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
        </button>
    `;

    return `
        <div class="job-card">
            <div class="job-icon ${job.status}">${iconHtml}</div>
            <div class="job-info">
                <div class="job-filename">${job.filename}</div>
                <div class="job-meta">
                    <span>${timeAgo}</span>
                    <span>${job.parser_type}</span>
                    <span>${job.output_format.toUpperCase()}</span>
                    ${resultInfo ? `<span>${resultInfo}</span>` : ''}
                </div>
            </div>
            <div class="job-actions">${actionsHtml}</div>
        </div>
    `;
}

function getStatusIcon(status) {
    switch (status) {
        case 'completed':
            return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
            </svg>`;
        case 'processing':
            return `<svg class="spinning" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
            </svg>`;
        case 'failed':
            return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>`;
        default:
            return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
            </svg>`;
    }
}

// ============================================
// Preview
// ============================================

async function showPreview(jobId, filename) {
    try {
        const response = await fetch(`${API_BASE}/preview/${jobId}?limit=50`);
        const data = await response.json();

        previewTitle.textContent = `Preview: ${filename}`;

        if (data.rows && data.rows.length > 0) {
            const columns = data.columns || Object.keys(data.rows[0]);

            let tableHtml = '<table class="preview-table"><thead><tr>';
            columns.slice(0, 10).forEach(col => {
                tableHtml += `<th>${col}</th>`;
            });
            tableHtml += '</tr></thead><tbody>';

            data.rows.forEach(row => {
                tableHtml += '<tr>';
                columns.slice(0, 10).forEach(col => {
                    const value = row[col] || '';
                    tableHtml += `<td title="${value}">${value}</td>`;
                });
                tableHtml += '</tr>';
            });

            tableHtml += '</tbody></table>';
            previewTable.innerHTML = tableHtml;
        } else {
            previewTable.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">No data to preview</p>';
        }

        // Set up download button
        downloadBtn.onclick = () => downloadFile(jobId);

        previewModal.classList.add('active');

    } catch (error) {
        showNotification('Failed to load preview', 'error');
    }
}

// ============================================
// Download
// ============================================

function downloadFile(jobId) {
    window.location.href = `${API_BASE}/download/${jobId}`;
}

// ============================================
// Delete
// ============================================

async function deleteJob(jobId) {
    if (!confirm('Delete this job and its output file?')) {
        return;
    }

    try {
        await fetch(`${API_BASE}/jobs/${jobId}`, { method: 'DELETE' });
        loadJobs();
        showNotification('Job deleted', 'success');
    } catch (error) {
        showNotification('Failed to delete job', 'error');
    }
}

// ============================================
// Utilities
// ============================================

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function getTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

function showNotification(message, type = 'info') {
    // Simple console notification for now
    console.log(`[${type.toUpperCase()}] ${message}`);

    // You could implement a toast notification here
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        padding: 14px 20px;
        background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 9999;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add slideIn animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
`;
document.head.appendChild(style);
