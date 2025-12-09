/* === ENHANCED CARDIOSENSE JAVASCRIPT === */

/* --- Global State --- */
let currentStep = 1;
const totalSteps = 4;
const formData = {};

/* --- Validation Rules --- */
const validationRules = {
    age: {
        min: 10,
        max: 120,
        message: 'Age must be between 10 and 120 years'
    },
    height: {
        min: 50,
        max: 250,
        message: 'Height must be between 50-250 cm'
    },
    weight: {
        min: 30,
        max: 250,
        message: 'Weight must be between 30-250 kg'
    },
    ap_hi: {
        min: 60,
        max: 250,
        message: 'Systolic BP must be between 60-250 mmHg',
        realtime: true
    },
    ap_lo: {
        min: 30,
        max: 180,
        message: 'Diastolic BP must be between 30-180 mmHg',
        realtime: true
    }
};

/* --- Initialize on DOM Load --- */
document.addEventListener('DOMContentLoaded', () => {
    updateUI();
    initializeValidation();
    addStepLabels();

    // Add real-time validation listeners
    const inputs = document.querySelectorAll('input[type="number"]');
    inputs.forEach(input => {
        input.addEventListener('input', handleRealtimeValidation);
        input.addEventListener('blur', handleBlurValidation);
    });

    // Blood pressure cross-validation
    const systolic = document.querySelector('input[name="ap_hi"]');
    const diastolic = document.querySelector('input[name="ap_lo"]');

    if (systolic && diastolic) {
        systolic.addEventListener('input', () => validateBloodPressure(systolic, diastolic));
        diastolic.addEventListener('input', () => validateBloodPressure(systolic, diastolic));
    }

    // BMI calculation
    const height = document.getElementById('height');
    const weight = document.getElementById('weight');

    if (height && weight) {
        height.addEventListener('input', calcBMI);
        weight.addEventListener('input', calcBMI);
    }
});

/* --- Add Step Labels --- */
function addStepLabels() {
    const circles = document.querySelectorAll('.step-circle');
    const labels = ['Basic', 'Physical', 'Medical', 'Lifestyle'];

    circles.forEach((circle, index) => {
        circle.setAttribute('data-label', labels[index]);
    });
}

/* --- UI Update --- */
function updateUI() {
    // Hide all steps
    for (let i = 1; i <= totalSteps; i++) {
        const el = document.getElementById('step' + i);
        if (el) {
            el.classList.remove('active');
        }
    }

    // Show current step with animation
    const currentEl = document.getElementById('step' + currentStep);
    if (currentEl) {
        currentEl.classList.add('active');
    }

    // Update circles
    const circles = document.querySelectorAll('.step-circle');
    circles.forEach((circle, index) => {
        if (index + 1 < currentStep) {
            circle.classList.add('completed');
            circle.classList.remove('active');
            circle.innerHTML = '<i class="fas fa-check"></i>';
        } else if (index + 1 === currentStep) {
            circle.classList.add('active');
            circle.classList.remove('completed');
            circle.textContent = index + 1;
        } else {
            circle.classList.remove('active', 'completed');
            circle.textContent = index + 1;
        }
    });

    // Update progress line
    const percent = ((currentStep - 1) / (totalSteps - 1)) * 100;
    const fill = document.getElementById('progressFill');
    if (fill) {
        fill.style.width = percent + '%';
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* --- Validation Functions --- */
function handleRealtimeValidation(e) {
    const input = e.target;
    const name = input.name;
    const value = parseFloat(input.value);

    if (!input.value) {
        clearValidation(input);
        return;
    }

    const rules = validationRules[name];
    if (!rules) return;

    if (value < rules.min || value > rules.max) {
        markInvalid(input, rules.message);
    } else {
        markValid(input);
    }
}

function handleBlurValidation(e) {
    const input = e.target;

    if (!input.value) {
        markInvalid(input, 'This field is required');
    } else {
        handleRealtimeValidation(e);
    }
}

function validateBloodPressure(systolicInput, diastolicInput) {
    const systolic = parseFloat(systolicInput.value);
    const diastolic = parseFloat(diastolicInput.value);

    if (!systolic || !diastolic) return;

    // Validate individual ranges first
    handleRealtimeValidation({ target: systolicInput });
    handleRealtimeValidation({ target: diastolicInput });

    // Cross-validation
    if (diastolic >= systolic) {
        markInvalid(diastolicInput, 'Diastolic BP must be lower than Systolic BP');
        markInvalid(systolicInput, 'Systolic BP must be higher than Diastolic BP');
    } else if ((systolic - diastolic) < 10) {
        markInvalid(diastolicInput, 'Pulse pressure too low (difference should be ≥ 10 mmHg)');
        markInvalid(systolicInput, 'Pulse pressure too low (difference should be ≥ 10 mmHg)');
    } else {
        // Only mark valid if within normal ranges
        if (systolic >= 60 && systolic <= 250) {
            markValid(systolicInput);
        }
        if (diastolic >= 30 && diastolic <= 180) {
            markValid(diastolicInput);
        }
    }
}

function markValid(input) {
    input.classList.remove('is-invalid');
    input.classList.add('is-valid');

    const feedbackEl = input.parentElement.querySelector('.invalid-feedback');
    if (feedbackEl) {
        feedbackEl.remove();
    }

    const validFeedback = input.parentElement.querySelector('.valid-feedback');
    if (!validFeedback) {
        const feedback = document.createElement('div');
        feedback.className = 'valid-feedback';
        feedback.innerHTML = '<i class="fas fa-check-circle me-1"></i>Looks good!';
        input.parentElement.appendChild(feedback);
    }
}

function markInvalid(input, message) {
    input.classList.remove('is-valid');
    input.classList.add('is-invalid');

    const validFeedback = input.parentElement.querySelector('.valid-feedback');
    if (validFeedback) {
        validFeedback.remove();
    }

    let feedbackEl = input.parentElement.querySelector('.invalid-feedback');
    if (!feedbackEl) {
        feedbackEl = document.createElement('div');
        feedbackEl.className = 'invalid-feedback';
        input.parentElement.appendChild(feedbackEl);
    }
    feedbackEl.innerHTML = `<i class="fas fa-exclamation-circle me-1"></i>${message}`;
}

function clearValidation(input) {
    input.classList.remove('is-valid', 'is-invalid');
    const feedback = input.parentElement.querySelector('.invalid-feedback, .valid-feedback');
    if (feedback) {
        feedback.remove();
    }
}

function initializeValidation() {
    const inputs = document.querySelectorAll('input[required], select[required]');
    inputs.forEach(input => {
        input.addEventListener('invalid', (e) => {
            e.preventDefault();
            markInvalid(input, 'This field is required');
        });
    });
}

/* --- Navigation Functions --- */
function nextStep(step) {
    const container = document.getElementById('step' + step);
    const inputs = container.querySelectorAll('input[required], select[required]');
    let valid = true;
    let firstInvalid = null;

    inputs.forEach(input => {
        if (!input.value) {
            markInvalid(input, 'This field is required');
            valid = false;
            if (!firstInvalid) firstInvalid = input;
        } else if (input.classList.contains('is-invalid')) {
            valid = false;
            if (!firstInvalid) firstInvalid = input;
        } else if (!input.classList.contains('is-valid')) {
            // Trigger validation
            const event = new Event('input', { bubbles: true });
            input.dispatchEvent(event);

            if (input.classList.contains('is-invalid')) {
                valid = false;
                if (!firstInvalid) firstInvalid = input;
            }
        }
    });

    // Special validation for BP in step 3
    if (step === 3) {
        const systolic = container.querySelector('input[name="ap_hi"]');
        const diastolic = container.querySelector('input[name="ap_lo"]');

        if (systolic && diastolic) {
            validateBloodPressure(systolic, diastolic);

            if (systolic.classList.contains('is-invalid') || diastolic.classList.contains('is-invalid')) {
                valid = false;
                if (!firstInvalid) firstInvalid = systolic;
            }
        }
    }

    if (valid) {
        // Store data
        inputs.forEach(input => {
            formData[input.name] = input.value;
        });

        currentStep++;
        updateUI();

        // Add animation effect
        const nextContainer = document.getElementById('step' + currentStep);
        if (nextContainer) {
            nextContainer.style.opacity = '0';
            setTimeout(() => {
                nextContainer.style.transition = 'opacity 0.5s ease-out';
                nextContainer.style.opacity = '1';
            }, 50);
        }
    } else {
        // Focus first invalid input
        if (firstInvalid) {
            firstInvalid.focus();
            firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });

            // Shake animation
            firstInvalid.style.animation = 'shake 0.5s';
            setTimeout(() => {
                firstInvalid.style.animation = '';
            }, 500);
        }
    }
}

function prevStep(step) {
    currentStep--;
    updateUI();
}

/* --- BMI Calculator --- */
function calcBMI() {
    const heightInput = document.getElementById('height');
    const weightInput = document.getElementById('weight');
    const display = document.getElementById('bmi-display');

    if (!heightInput || !weightInput || !display) return;

    const h = parseFloat(heightInput.value) / 100; // cm to m
    const w = parseFloat(weightInput.value);

    if (h > 0 && w > 0) {
        const bmi = (w / (h * h)).toFixed(1);
        const category = getBMICategory(bmi);

        display.innerHTML = `
            <div style="font-size: 2rem; font-weight: 900; margin-bottom: 0.5rem;">${bmi}</div>
            <div style="font-size: 0.9rem; opacity: 0.95;">${category.label}</div>
        `;

        // Change color based on category
        const parent = display.parentElement;
        parent.className = 'bmi-display-box';
        parent.style.background = category.gradient;
    } else {
        display.innerHTML = '<div style="font-size: 2rem; font-weight: 900;">--</div><div style="font-size: 0.9rem;">Enter values above</div>';
        display.parentElement.style.background = 'linear-gradient(135deg, #0066cc 0%, #004c99 100%)';
    }
}

function getBMICategory(bmi) {
    const value = parseFloat(bmi);

    if (value < 18.5) {
        return {
            label: 'Underweight 🕴️',
            gradient: 'linear-gradient(135deg, #4ea8de 0%, #3a86c4 100%)'
        };
    } else if (value >= 18.5 && value < 25) {
        return {
            label: 'Normal Weight 🏋🏻‍♀️',
            gradient: 'linear-gradient(135deg, #06d6a0 0%, #05b185 100%)'
        };
    } else if (value >= 25 && value < 30) {
        return {
            label: 'Overweight 😐',
            gradient: 'linear-gradient(135deg, #ffa500 0%, #e69500 100%)'
        };
    } else {
        return {
            label: 'Obese 🫃',
            gradient: 'linear-gradient(135deg, #ef476f 0%, #d63a5e 100%)'
        };
    }
}

/* --- Helper Functions --- */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} position-fixed top-0 start-50 translate-middle-x mt-3`;
    toast.style.zIndex = '10000';
    toast.style.minWidth = '300px';
    toast.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
            <div>${message}</div>
        </div>
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.transition = 'opacity 0.3s';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/* --- Add shake animation to styles --- */
const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
        20%, 40%, 60%, 80% { transform: translateX(5px); }
    }
    
    .pulse {
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(0, 102, 204, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(0, 102, 204, 0); }
        100% { box-shadow: 0 0 0 0 rgba(0, 102, 204, 0); }
    }
`;
document.head.appendChild(style);

/* --- Form Submit Enhancement --- */
document.addEventListener('submit', (e) => {
    const form = e.target;
    if (form.tagName === 'FORM') {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Analyzing...';
        }
    }
});