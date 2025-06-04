// Global dashboard utilities and functions

// Flow injection function
function injectFlows(ruleSet = 1) {
    const button = event.target;
    const originalText = button.innerHTML;

    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Injecting...';

    const endpoint = ruleSet === 1 ? '/api/inject_flows' : '/api/inject_flows_2';

    fetch(endpoint, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showStatusMessage(`Flow Rules ${ruleSet} injected successfully`, 'success');
            } else {
                showStatusMessage(`Failed to inject Flow Rules ${ruleSet}: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error(`Error injecting Flow Rules ${ruleSet}:`, error);
            showStatusMessage(`Error injecting Flow Rules ${ruleSet}`, 'danger');
        })
        .finally(() => {
            button.disabled = false;
            button.innerHTML = originalText;
        });
}

// Status message utility
function showStatusMessage(message, type = 'info', duration = 5000) {
    const container = document.getElementById('statusMessage');
    if (!container) return;

    const alertClass = `alert-${type}`;
    const iconClass = getIconForType(type);

    container.innerHTML = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            <i class="${iconClass} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    // Auto-dismiss after specified duration
    setTimeout(() => {
        const alert = container.querySelector('.alert');
        if (alert) {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }
    }, duration);
}

function getIconForType(type) {
    const icons = {
        'success': 'fas fa-check-circle',
        'danger': 'fas fa-exclamation-triangle',
        'warning': 'fas fa-exclamation-triangle',
        'info': 'fas fa-info-circle'
    };
    return icons[type] || icons['info'];
}

// Network status utilities
function formatNetworkStatus(isRunning) {
    return {
        text: isRunning ? 'Running' : 'Stopped',
        class: isRunning ? 'text-success' : 'text-danger',
        icon: isRunning ? 'fas fa-check-circle' : 'fas fa-times-circle',
        badge: isRunning ? 'bg-success' : 'bg-danger'
    };
}

// Data formatting utilities
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';

    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatBandwidth(mbps) {
    if (mbps >= 1000) {
        return (mbps / 1000).toFixed(1) + ' Gbps';
    }
    return mbps.toFixed(1) + ' Mbps';
}

function formatLatency(ms) {
    if (ms < 1) {
        return (ms * 1000).toFixed(0) + ' μs';
    }
    return ms.toFixed(1) + ' ms';
}

// Chart utilities
function createProgressChart(canvasId, value, maxValue = 100, color = '#007bff') {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    const ctx = canvas.getContext('2d');
    const percentage = Math.min(100, (value / maxValue) * 100);

    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [percentage, 100 - percentage],
                backgroundColor: [color, '#e9ecef'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: false,
            maintainAspectRatio: false,
            cutout: '75%',
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            }
        }
    });
}

// API call utilities
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API call to ${endpoint} failed:`, error);
        throw error;
    }
}

// Loading state utilities
function showLoading(elementId, message = 'Loading...') {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.innerHTML = `
        <div class="text-center">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <div class="mt-2">${message}</div>
        </div>
    `;
}

function hideLoading(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.innerHTML = '';
}

// Validation utilities
function validateIP(ip) {
    const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    return ipRegex.test(ip);
}

function validateCIDR(cidr) {
    const cidrRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(?:[0-9]|[1-2][0-9]|3[0-2])$/;
    return cidrRegex.test(cidr);
}

// DOM utilities
function createElement(tag, attributes = {}, content = '') {
    const element = document.createElement(tag);

    Object.entries(attributes).forEach(([key, value]) => {
        if (key === 'className') {
            element.className = value;
        } else if (key === 'innerHTML') {
            element.innerHTML = value;
        } else {
            element.setAttribute(key, value);
        }
    });

    if (content) {
        element.textContent = content;
    }

    return element;
}

// Time utilities
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
}

function getRelativeTime(timestamp) {
    const now = new Date();
    const past = new Date(timestamp);
    const diffMs = now - past;

    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) {
        return 'Just now';
    } else if (diffMins < 60) {
        return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    } else if (diffHours < 24) {
        return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    } else {
        return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    }
}

// Local storage utilities
function saveToLocalStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
        return true;
    } catch (error) {
        console.error('Failed to save to localStorage:', error);
        return false;
    }
}

function loadFromLocalStorage(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
        console.error('Failed to load from localStorage:', error);
        return defaultValue;
    }
}

// Event utilities
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Page visibility utilities
function onPageVisible(callback) {
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            callback();
        }
    });
}

// Copy to clipboard utility
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showStatusMessage('Copied to clipboard', 'success', 2000);
        return true;
    } catch (error) {
        console.error('Failed to copy to clipboard:', error);
        showStatusMessage('Failed to copy to clipboard', 'danger', 3000);
        return false;
    }
}

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// Global error handler
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    showStatusMessage('An unexpected error occurred', 'danger');
});

// Network connectivity checker
function checkNetworkConnectivity() {
    return fetch('/api/status', {
        method: 'HEAD',
        cache: 'no-cache'
    }).then(() => true).catch(() => false);
}

// Periodic connectivity check
setInterval(async () => {
    const isConnected = await checkNetworkConnectivity();
    const statusElement = document.getElementById('networkConnectivity');

    if (statusElement) {
        statusElement.className = isConnected ? 'status-indicator status-up' : 'status-indicator status-down';
        statusElement.title = isConnected ? 'Connected' : 'Disconnected';
    }
}, 30000); // Check every 30 seconds
