(function () {
    'use strict';

    const LIBRARY_URL_KEY = 'last-library-url';

    function rememberLibrary() {
        if (!document.getElementById('books-list')) return;
        try {
            sessionStorage.setItem(
                LIBRARY_URL_KEY,
                window.location.pathname + window.location.search + window.location.hash
            );
        } catch {
            // Navigation still works through the canonical fallback links.
        }
    }

    function storedLibraryUrl() {
        try {
            const value = sessionStorage.getItem(LIBRARY_URL_KEY);
            if (!value) return null;
            const url = new URL(value, window.location.origin);
            if (url.origin !== window.location.origin) return null;
            return url.pathname + url.search + url.hash;
        } catch {
            return null;
        }
    }

    function hasSameOriginReferrer() {
        if (!document.referrer || window.history.length < 2) return false;
        try {
            return new URL(document.referrer).origin === window.location.origin;
        } catch {
            return false;
        }
    }

    document.addEventListener('DOMContentLoaded', rememberLibrary);
    window.addEventListener('pageshow', rememberLibrary);
    document.addEventListener('htmx:afterSettle', function (event) {
        if (event.detail.target && event.detail.target.id === 'books-list') rememberLibrary();
    });
    document.addEventListener('htmx:pushedIntoHistory', rememberLibrary);

    document.addEventListener('click', function (event) {
        if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
            return;
        }
        if (!(event.target instanceof Element)) return;

        const libraryLink = event.target.closest('[data-library-back]');
        if (libraryLink) {
            const url = storedLibraryUrl();
            if (url) {
                event.preventDefault();
                window.location.assign(url);
            }
            return;
        }

        const historyLink = event.target.closest('[data-history-back]');
        if (historyLink && hasSameOriginReferrer()) {
            event.preventDefault();
            window.history.back();
        }
    });
})();
