/* === CARDIOSENSE NEW UI - JAVASCRIPT === */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initNavbar();
    initMobileMenu();
    initScrollAnimations();
});

/* ==================== THEME TOGGLE ==================== */
function initTheme() {
    const themeToggle = document.getElementById('themeToggle');
    // Theme is already set by inline script in <head>, just get current value
    const savedTheme = document.documentElement.getAttribute('data-theme') || 'light';

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';

            // Temporarily disable all transitions for instant theme change
            document.body.classList.add('theme-switching');

            // Change theme
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('cardiosense-theme', newTheme);

            // Force reflow to ensure theme is applied
            void document.body.offsetHeight;

            // Remove transition-disabling class after a brief moment
            setTimeout(() => {
                document.body.classList.remove('theme-switching');
            }, 50);
        });
    }
}

/* ==================== NAVBAR ==================== */
function initNavbar() {
    const navbar = document.querySelector('.navbar');

    if (navbar) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }

    // Set active nav link based on current page
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPath || (currentPath === '/' && href === '/')) {
            link.classList.add('active');
        }
    });
}

/* ==================== MOBILE MENU ==================== */
function initMobileMenu() {
    const mobileToggle = document.getElementById('mobileMenuToggle');
    const navLinks = document.querySelector('.nav-links');

    if (mobileToggle && navLinks) {
        mobileToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            mobileToggle.classList.toggle('active');

            // Animate hamburger to X
            const spans = mobileToggle.querySelectorAll('span');
            if (mobileToggle.classList.contains('active')) {
                spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
                spans[1].style.opacity = '0';
                spans[2].style.transform = 'rotate(-45deg) translate(7px, -6px)';
            } else {
                spans[0].style.transform = 'none';
                spans[1].style.opacity = '1';
                spans[2].style.transform = 'none';
            }
        });

        // Close menu when clicking a link
        navLinks.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('active');
                mobileToggle.classList.remove('active');
            });
        });
    }
}

/* ==================== SCROLL ANIMATIONS ==================== */
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe elements
    const animateElements = document.querySelectorAll(
        '.feature-card, .step, .metric-item, .model-card, .education-card, ' +
        '.whatif-card, .stat-card, .about-feature, .tech-category'
    );

    animateElements.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
        observer.observe(el);
    });
}

// Add animate-in styles
const style = document.createElement('style');
style.textContent = `
    .animate-in {
        opacity: 1 !important;
        transform: translateY(0) !important;
    }
`;
document.head.appendChild(style);

/* ==================== SMOOTH SCROLL ==================== */
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

/* ==================== UTILITY FUNCTIONS ==================== */
// Debounce function
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

// Format number with commas
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/* ==================== COUNTER ANIMATION ==================== */
function animateCounter(element, target, duration = 2000) {
    let start = 0;
    const increment = target / (duration / 16);

    const updateCounter = () => {
        start += increment;
        if (start < target) {
            element.textContent = Math.floor(start);
            requestAnimationFrame(updateCounter);
        } else {
            element.textContent = target;
        }
    };

    updateCounter();
}

// Initialize counters when in view
const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const target = parseInt(entry.target.dataset.count);
            if (target) {
                animateCounter(entry.target, target);
                counterObserver.unobserve(entry.target);
            }
        }
    });
}, { threshold: 0.5 });

document.querySelectorAll('[data-count]').forEach(el => {
    counterObserver.observe(el);
});

/* ==================== RIPPLE EFFECT FOR BUTTONS ==================== */
document.querySelectorAll('.btn').forEach(button => {
    button.addEventListener('click', function (e) {
        const rect = this.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const ripple = document.createElement('span');
        ripple.style.cssText = `
            position: absolute;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            transform: scale(0);
            animation: ripple 0.6s linear;
            left: ${x}px;
            top: ${y}px;
            width: 100px;
            height: 100px;
            margin-left: -50px;
            margin-top: -50px;
            pointer-events: none;
        `;

        this.appendChild(ripple);

        setTimeout(() => ripple.remove(), 600);
    });
});

// Add ripple animation
const rippleStyle = document.createElement('style');
rippleStyle.textContent = `
    @keyframes ripple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    .btn {
        position: relative;
        overflow: hidden;
    }
`;
document.head.appendChild(rippleStyle);

/* ==================== TOOLTIP ==================== */
function createTooltip(element, text) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = text;
    tooltip.style.cssText = `
        position: absolute;
        background: var(--text-primary);
        color: var(--bg-primary);
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 0.8rem;
        white-space: nowrap;
        z-index: 1000;
        opacity: 0;
        transition: opacity 0.2s ease;
        pointer-events: none;
    `;

    element.style.position = 'relative';
    element.appendChild(tooltip);

    element.addEventListener('mouseenter', () => {
        const rect = element.getBoundingClientRect();
        tooltip.style.bottom = '100%';
        tooltip.style.left = '50%';
        tooltip.style.transform = 'translateX(-50%) translateY(-8px)';
        tooltip.style.opacity = '1';
    });

    element.addEventListener('mouseleave', () => {
        tooltip.style.opacity = '0';
    });
}

// Initialize tooltips
document.querySelectorAll('[data-tooltip]').forEach(el => {
    createTooltip(el, el.dataset.tooltip);
});

/* ==================== LOADING STATE ==================== */
function showLoading(button) {
    const originalContent = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `
        <span class="spinner"></span>
        <span>Processing...</span>
    `;
    button.dataset.originalContent = originalContent;
}

function hideLoading(button) {
    button.disabled = false;
    button.innerHTML = button.dataset.originalContent;
}

// Spinner styles
const spinnerStyle = document.createElement('style');
spinnerStyle.textContent = `
    .spinner {
        width: 18px;
        height: 18px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        border-top-color: white;
        animation: spin 0.8s linear infinite;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(spinnerStyle);

/* ==================== FORM SUBMISSION WITH LOADING ==================== */
const assessmentForm = document.getElementById('assessmentForm');
if (assessmentForm) {
    assessmentForm.addEventListener('submit', function (e) {
        const submitBtn = this.querySelector('#submitBtn');
        if (submitBtn) {
            showLoading(submitBtn);
        }
    });
}

console.log('🫀 CardioSense UI initialized');
