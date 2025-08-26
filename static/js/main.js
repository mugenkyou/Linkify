// Linkify - Main JavaScript File

document.addEventListener('DOMContentLoaded', function() {
    // Add loading state to buttons when clicked
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        if (button.type === 'submit' || button.id === 'acceptConnectionsBtn' || button.id === 'skipOTP') {
            button.addEventListener('click', function(e) {
                // Don't apply for buttons that are within forms (handled separately)
                if (this.type === 'submit' && this.closest('form')) {
                    return;
                }
                
                const originalText = this.innerHTML;
                this.disabled = true;
                this.classList.add('loading');
                this.dataset.originalText = originalText;
                this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                
                // Reset button after 30 seconds if no response (failsafe)
                setTimeout(() => {
                    if (this.classList.contains('loading')) {
                        this.disabled = false;
                        this.classList.remove('loading');
                        this.innerHTML = this.dataset.originalText || 'Try Again';
                    }
                }, 30000);
            });
        }
    });
    
    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            
            // Basic validation for required fields
            const requiredFields = this.querySelectorAll('[required]');
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('error');
                    
                    // Create or update error message
                    let errorMsg = field.parentNode.querySelector('.error-message');
                    if (!errorMsg) {
                        errorMsg = document.createElement('div');
                        errorMsg.className = 'error-message';
                        field.parentNode.appendChild(errorMsg);
                    }
                    errorMsg.textContent = 'This field is required';
                } else {
                    field.classList.remove('error');
                    const errorMsg = field.parentNode.querySelector('.error-message');
                    if (errorMsg) errorMsg.remove();
                }
            });
            
            // Email validation
            const emailField = this.querySelector('input[type="email"]');
            if (emailField && emailField.value.trim()) {
                const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailPattern.test(emailField.value)) {
                    isValid = false;
                    emailField.classList.add('error');
                    
                    let errorMsg = emailField.parentNode.querySelector('.error-message');
                    if (!errorMsg) {
                        errorMsg = document.createElement('div');
                        errorMsg.className = 'error-message';
                        emailField.parentNode.appendChild(errorMsg);
                    }
                    errorMsg.textContent = 'Please enter a valid email address';
                }
            }
            
            if (!isValid) {
                e.preventDefault();
                return false;
            }
            
            // Disable submit button
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                const originalText = submitBtn.innerHTML;
                submitBtn.disabled = true;
                submitBtn.classList.add('loading');
                submitBtn.dataset.originalText = originalText;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            }
        });
    });
    
    // Field validation on input
    const inputFields = document.querySelectorAll('input, textarea, select');
    inputFields.forEach(field => {
        field.addEventListener('input', function() {
            if (this.hasAttribute('required') && this.value.trim()) {
                this.classList.remove('error');
                const errorMsg = this.parentNode.querySelector('.error-message');
                if (errorMsg) errorMsg.remove();
            }
            
            if (this.type === 'email' && this.value.trim()) {
                const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (emailPattern.test(this.value)) {
                    this.classList.remove('error');
                    const errorMsg = this.parentNode.querySelector('.error-message');
                    if (errorMsg) errorMsg.remove();
                }
            }
        });
    });
    
    // Password visibility toggle
    const togglePasswordBtn = document.getElementById('togglePassword');
    if (togglePasswordBtn) {
        const passwordInput = document.querySelector('input[type="password"]');
        if (passwordInput) {
            togglePasswordBtn.addEventListener('click', function() {
                const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
                passwordInput.setAttribute('type', type);
                this.innerHTML = type === 'password' ? 
                    '<i class="fas fa-eye"></i>' : 
                    '<i class="fas fa-eye-slash"></i>';
            });
        }
    }
    
    // Pulse animation for action buttons
    const actionButtons = document.querySelectorAll('.btn-primary');
    actionButtons.forEach(button => {
        button.classList.add('animate-pulse');
        
        // Remove animation on hover
        button.addEventListener('mouseenter', function() {
            this.classList.remove('animate-pulse');
        });
        
        // Add animation back on mouse leave
        button.addEventListener('mouseleave', function() {
            this.classList.add('animate-pulse');
        });
    });
    
    // Initialize dashboard counters
    const connectionsCount = document.getElementById('connectionsCount');
    if (connectionsCount) {
        connectionsCount.textContent = Math.floor(Math.random() * 20) + 5;
    }
}); 