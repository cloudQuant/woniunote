// woniunote.js
class AuthManager {
    constructor() {
        this.modal = new bootstrap.Modal('#authModal');
        this.initEventListeners();
    }

    initEventListeners() {
        // 表单提交事件
        document.getElementById('loginForm').addEventListener('submit', this.handleLogin.bind(this));
        
        // 验证码刷新
        document.querySelectorAll('.captcha-img').forEach(img => {
            img.addEventListener('click', () => this.refreshCaptcha(img));
        });

        // 模态框显示事件
        document.getElementById('authModal').addEventListener('shown.bs.modal', () => {
            document.querySelector('#loginForm input').focus();
        });
    }

    async handleLogin(e) {
        e.preventDefault();
        
        const formData = {
            email: e.target[0].value,
            password: e.target[1].value,
            captcha: e.target[2].value
        };

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();
            
            if (result.success) {
                window.location.reload();
            } else {
                this.showError(result.message);
                this.refreshCaptcha();
            }
        } catch (error) {
            this.showError('网络请求失败，请检查连接');
        }
    }

    refreshCaptcha(imgElement) {
        const captchaImg = imgElement || document.querySelector('.captcha-img');
        captchaImg.src = `/vcode?t=${Date.now()}`;
    }

    showError(message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger mt-3';
        alertDiv.textContent = message;
        
        const form = document.getElementById('loginForm');
        form.appendChild(alertDiv);
        
        setTimeout(() => alertDiv.remove(), 5000);
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    new AuthManager();
});