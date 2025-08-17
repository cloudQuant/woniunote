/**
 * WoniuNote 统一前端验证库
 * 与后端验证逻辑保持同步
 */

const WoniuValidation = {
    
    // 验证消息
    messages: {
        required: '此字段不能为空',
        username: {
            length: '用户名长度必须在2-50个字符之间',
            format: '用户名只能包含字母、数字、下划线和中文字符'
        },
        password: {
            length: '密码长度必须在6-128个字符之间',
            complexity: '密码必须包含字母或数字'
        },
        email: {
            format: '请输入有效的邮箱地址'
        },
        article: {
            title: '标题长度必须在5-200个字符之间',
            content: '内容长度必须在10-50000个字符之间'
        },
        comment: {
            content: '评论长度必须在5-1000个字符之间'
        },
        file: {
            type: '文件类型不支持，支持的类型：jpg, jpeg, png, gif, pdf, doc, docx, txt',
            size: '文件大小不能超过16MB'
        }
    },

    /**
     * 验证用户名
     * @param {string} username 用户名
     * @returns {object} {valid: boolean, message: string}
     */
    validateUsername(username) {
        if (!username) {
            return { valid: false, message: this.messages.required };
        }
        
        // 长度检查：2-50个字符
        if (username.length < 2 || username.length > 50) {
            return { valid: false, message: this.messages.username.length };
        }
        
        // 格式检查：只允许字母、数字、下划线、中文
        const pattern = /^[\w\u4e00-\u9fa5]+$/;
        if (!pattern.test(username)) {
            return { valid: false, message: this.messages.username.format };
        }
        
        return { valid: true, message: '' };
    },

    /**
     * 验证密码
     * @param {string} password 密码
     * @returns {object} {valid: boolean, message: string}
     */
    validatePassword(password) {
        if (!password) {
            return { valid: false, message: this.messages.required };
        }
        
        // 长度检查：6-128个字符
        if (password.length < 6 || password.length > 128) {
            return { valid: false, message: this.messages.password.length };
        }
        
        // 复杂度检查：必须包含字母或数字
        const hasLetter = /[a-zA-Z]/.test(password);
        const hasDigit = /\d/.test(password);
        if (!hasLetter && !hasDigit) {
            return { valid: false, message: this.messages.password.complexity };
        }
        
        return { valid: true, message: '' };
    },

    /**
     * 验证邮箱
     * @param {string} email 邮箱地址
     * @returns {object} {valid: boolean, message: string}
     */
    validateEmail(email) {
        if (!email) {
            return { valid: false, message: this.messages.required };
        }
        
        // 标准邮箱格式验证
        const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!pattern.test(email)) {
            return { valid: false, message: this.messages.email.format };
        }
        
        return { valid: true, message: '' };
    },

    /**
     * 验证文章标题
     * @param {string} title 文章标题
     * @returns {object} {valid: boolean, message: string}
     */
    validateArticleTitle(title) {
        if (!title) {
            return { valid: false, message: this.messages.required };
        }
        
        // 清理HTML标签后的长度
        const cleanTitle = this.stripHtml(title);
        if (cleanTitle.length < 5 || cleanTitle.length > 200) {
            return { valid: false, message: this.messages.article.title };
        }
        
        return { valid: true, message: '' };
    },

    /**
     * 验证文章内容
     * @param {string} content 文章内容
     * @returns {object} {valid: boolean, message: string}
     */
    validateArticleContent(content) {
        if (!content) {
            return { valid: false, message: this.messages.required };
        }
        
        // 清理HTML标签后的长度
        const cleanContent = this.stripHtml(content);
        if (cleanContent.length < 10 || cleanContent.length > 50000) {
            return { valid: false, message: this.messages.article.content };
        }
        
        return { valid: true, message: '' };
    },

    /**
     * 验证评论内容
     * @param {string} content 评论内容
     * @returns {object} {valid: boolean, message: string}
     */
    validateComment(content) {
        if (!content) {
            return { valid: false, message: this.messages.required };
        }
        
        // 清理HTML标签后的长度
        const cleanContent = this.stripHtml(content);
        if (cleanContent.length < 5 || cleanContent.length > 1000) {
            return { valid: false, message: this.messages.comment.content };
        }
        
        return { valid: true, message: '' };
    },

    /**
     * 验证文件上传
     * @param {File} file 文件对象
     * @returns {object} {valid: boolean, message: string}
     */
    validateFile(file) {
        if (!file) {
            return { valid: false, message: this.messages.required };
        }
        
        // 允许的文件类型（与后端保持一致）
        const allowedTypes = ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'txt', 'zip', 'rar'];
        const fileName = file.name.toLowerCase();
        const fileExt = fileName.split('.').pop();
        
        if (!allowedTypes.includes(fileExt)) {
            return { valid: false, message: this.messages.file.type };
        }
        
        // 文件大小限制：16MB
        const maxSize = 16 * 1024 * 1024;
        if (file.size > maxSize) {
            return { valid: false, message: this.messages.file.size };
        }
        
        return { valid: true, message: '' };
    },

    /**
     * 清理HTML标签
     * @param {string} html HTML字符串
     * @returns {string} 清理后的纯文本
     */
    stripHtml(html) {
        if (!html) return '';
        
        // 创建临时DOM元素来清理HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        return tempDiv.textContent || tempDiv.innerText || '';
    },

    /**
     * 验证表单
     * @param {HTMLFormElement} form 表单元素
     * @param {object} rules 验证规则
     * @returns {object} {valid: boolean, errors: object}
     */
    validateForm(form, rules) {
        const errors = {};
        let isValid = true;

        for (const fieldName in rules) {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (!field) continue;

            const value = field.value.trim();
            const rule = rules[fieldName];
            let result = { valid: true, message: '' };

            // 根据验证类型调用相应的验证方法
            switch (rule.type) {
                case 'username':
                    result = this.validateUsername(value);
                    break;
                case 'password':
                    result = this.validatePassword(value);
                    break;
                case 'email':
                    result = this.validateEmail(value);
                    break;
                case 'article_title':
                    result = this.validateArticleTitle(value);
                    break;
                case 'article_content':
                    result = this.validateArticleContent(value);
                    break;
                case 'comment':
                    result = this.validateComment(value);
                    break;
                case 'required':
                    result = value ? { valid: true, message: '' } : { valid: false, message: this.messages.required };
                    break;
                case 'custom':
                    if (rule.validator && typeof rule.validator === 'function') {
                        result = rule.validator(value);
                    }
                    break;
            }

            if (!result.valid) {
                errors[fieldName] = result.message;
                isValid = false;
                
                // 显示错误信息
                this.showFieldError(field, result.message);
            } else {
                // 清除错误信息
                this.clearFieldError(field);
            }
        }

        return { valid: isValid, errors: errors };
    },

    /**
     * 显示字段错误信息
     * @param {HTMLElement} field 表单字段
     * @param {string} message 错误信息
     */
    showFieldError(field, message) {
        // 移除现有错误信息
        this.clearFieldError(field);
        
        // 添加错误样式
        field.classList.add('is-invalid');
        
        // 创建错误信息元素
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        errorDiv.setAttribute('data-validation-error', '');
        
        // 插入错误信息
        field.parentNode.insertBefore(errorDiv, field.nextSibling);
    },

    /**
     * 清除字段错误信息
     * @param {HTMLElement} field 表单字段
     */
    clearFieldError(field) {
        // 移除错误样式
        field.classList.remove('is-invalid');
        
        // 移除错误信息元素
        const errorDiv = field.parentNode.querySelector('[data-validation-error]');
        if (errorDiv) {
            errorDiv.remove();
        }
    },

    /**
     * 实时验证字段
     * @param {HTMLElement} field 表单字段
     * @param {string} validationType 验证类型
     */
    bindRealTimeValidation(field, validationType) {
        const validateField = () => {
            const value = field.value.trim();
            let result = { valid: true, message: '' };

            switch (validationType) {
                case 'username':
                    result = this.validateUsername(value);
                    break;
                case 'password':
                    result = this.validatePassword(value);
                    break;
                case 'email':
                    result = this.validateEmail(value);
                    break;
                case 'article_title':
                    result = this.validateArticleTitle(value);
                    break;
                case 'article_content':
                    result = this.validateArticleContent(value);
                    break;
                case 'comment':
                    result = this.validateComment(value);
                    break;
            }

            if (!result.valid) {
                this.showFieldError(field, result.message);
            } else {
                this.clearFieldError(field);
            }
        };

        // 绑定事件
        field.addEventListener('blur', validateField);
        field.addEventListener('input', () => {
            // 输入时延迟验证，避免频繁提示
            clearTimeout(field.validationTimeout);
            field.validationTimeout = setTimeout(validateField, 500);
        });
    },

    /**
     * 初始化表单验证
     * @param {string} formSelector 表单选择器
     * @param {object} config 配置选项
     */
    initFormValidation(formSelector, config = {}) {
        const form = document.querySelector(formSelector);
        if (!form) return;

        const rules = config.rules || {};
        const realTimeValidation = config.realTimeValidation !== false;

        // 绑定实时验证
        if (realTimeValidation) {
            for (const fieldName in rules) {
                const field = form.querySelector(`[name="${fieldName}"]`);
                if (field && rules[fieldName].type) {
                    this.bindRealTimeValidation(field, rules[fieldName].type);
                }
            }
        }

        // 绑定表单提交验证
        form.addEventListener('submit', (e) => {
            const validation = this.validateForm(form, rules);
            if (!validation.valid) {
                e.preventDefault();
                
                // 滚动到第一个错误字段
                const firstErrorField = form.querySelector('.is-invalid');
                if (firstErrorField) {
                    firstErrorField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    firstErrorField.focus();
                }
                
                // 调用错误回调
                if (config.onError && typeof config.onError === 'function') {
                    config.onError(validation.errors);
                }
            } else {
                // 调用成功回调
                if (config.onSuccess && typeof config.onSuccess === 'function') {
                    config.onSuccess();
                }
            }
        });
    }
};

// 全局暴露
window.WoniuValidation = WoniuValidation;