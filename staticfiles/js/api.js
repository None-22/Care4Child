/**
 * Care4Child - Shared API Utility
 * Provides authenticated fetch helpers for the Django REST API.
 * Uses session authentication + CSRF (works for browser-based users logged in via Django).
 */

/**
 * Reads the CSRF token from the Django-set cookie.
 * @returns {string} CSRF token value
 */
function getCsrfToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const trimmed = cookie.trim();
        if (trimmed.startsWith(name + '=')) {
            return decodeURIComponent(trimmed.substring(name.length + 1));
        }
    }
    return '';
}

/**
 * Authenticated Fetch wrapper.
 * Automatically attaches the CSRF header and handles 401/403 redirects.
 *
 * @param {string} url  - API endpoint URL
 * @param {object} options - Optional fetch options (method, body, headers, etc.)
 * @returns {Promise<any>} - Parsed JSON response
 */
async function apiFetch(url, options = {}) {
    const defaultHeaders = {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
    };

    const config = {
        credentials: 'same-origin',  // Send session cookie automatically
        headers: Object.assign(defaultHeaders, options.headers || {}),
        ...options,
    };

    const response = await fetch(url, config);

    if (response.status === 401 || response.status === 403) {
        // Session expired or unauthorized — redirect to login
        window.location.href = '/users/login/?next=' + encodeURIComponent(window.location.pathname);
        return null;
    }

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API Error ${response.status}: ${errorText}`);
    }

    // Handle empty responses (e.g., 204 No Content)
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
        return await response.json();
    }
    return null;
}

/**
 * Shows a simple loading spinner in a container element.
 * @param {HTMLElement} el - Container element
 */
function showLoader(el) {
    if (!el) return;
    el.innerHTML = `
        <div class="d-flex justify-content-center align-items-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">جاري التحميل...</span>
            </div>
            <span class="ms-3 text-muted fw-bold">جاري تحميل البيانات...</span>
        </div>`;
}

/**
 * Shows an error message in a container element.
 * @param {HTMLElement} el - Container element
 * @param {string} msg - Error message (Arabic)
 */
function showError(el, msg = 'حدث خطأ أثناء تحميل البيانات. يرجى تحديث الصفحة.') {
    if (!el) return;
    el.innerHTML = `
        <div class="alert alert-danger m-3" role="alert">
            <i class="fas fa-exclamation-circle me-2"></i>${msg}
        </div>`;
}
