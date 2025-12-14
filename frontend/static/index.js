// 获取DOM元素
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const uploadStatus = document.getElementById('uploadStatus');
const questionInput = document.getElementById('questionInput');
const qaBtn = document.getElementById('qaBtn');
const qaLoading = document.getElementById('qaLoading');
const answerDisplay = document.getElementById('answerDisplay');
const sourceDisplay = document.getElementById('sourceDisplay');

// 文档上传功能
uploadBtn.addEventListener('click', () => {
    const file = fileInput.files[0];
    if (!file) {
        uploadStatus.innerHTML = '<div class="alert alert-warning">请选择要上传的文件</div>';
        return;
    }

    // 检查文件类型
    const fileExt = file.name.split('.').pop().toLowerCase();
    if (fileExt !== 'pdf' && fileExt !== 'docx') {
        uploadStatus.innerHTML = '<div class="alert alert-danger">仅支持PDF和DOCX格式的文档</div>';
        return;
    }

    // 创建FormData对象
    const formData = new FormData();
    formData.append('file', file);

    // 显示上传状态
    uploadStatus.innerHTML = '<div class="alert alert-info">正在上传文档...</div>';

    // 发送请求
    fetch('/upload_doc/', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.code === 0) {
            uploadStatus.innerHTML = '<div class="alert alert-success">' + data.msg + '</div>';
            // 清空文件输入
            fileInput.value = '';
        } else {
            uploadStatus.innerHTML = '<div class="alert alert-danger">上传失败：' + data.msg + '</div>';
        }
    })
    .catch(error => {
        uploadStatus.innerHTML = '<div class="alert alert-danger">上传失败：' + error.message + '</div>';
    });
});

// 问答功能
qaBtn.addEventListener('click', () => {
    const question = questionInput.value.trim();
    if (!question) {
        alert('请输入问题');
        return;
    }

    // 显示加载状态
    qaLoading.style.display = 'block';
    answerDisplay.innerHTML = '';
    sourceDisplay.innerHTML = '';

    // 创建FormData对象
    const formData = new FormData();
    formData.append('query', question);

    // 发送请求
    fetch('/qa/', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        // 隐藏加载状态
        qaLoading.style.display = 'none';

        if (data.code === 0) {
            // 显示回答
            answerDisplay.innerHTML = '<div class="answer-box">' + data.answer + '</div>';
            
            // 显示参考片段
            if (data.source && data.source.length > 0) {
                let sourceHtml = '';
                data.source.forEach((source, index) => {
                    sourceHtml += `<div class="source-item">
                        <strong>参考片段 ${index + 1}:</strong><br>
                        ${source}
                    </div>`;
                });
                sourceDisplay.innerHTML = '<div class="source-box">' + sourceHtml + '</div>';
            } else {
                sourceDisplay.innerHTML = '<div class="source-box">没有相关参考片段</div>';
            }
        } else {
            answerDisplay.innerHTML = '<div class="alert alert-danger">请求失败：' + data.msg + '</div>';
        }
    })
    .catch(error => {
        // 隐藏加载状态
        qaLoading.style.display = 'none';
        answerDisplay.innerHTML = '<div class="alert alert-danger">请求失败：' + error.message + '</div>';
    });
});

// 回车键提交问题
questionInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        qaBtn.click();
    }
});

// 登录和注册功能
// 获取登录相关DOM元素
const loginSubmitBtn = document.getElementById('loginSubmitBtn');
const loginUsername = document.getElementById('loginUsername');
const loginPassword = document.getElementById('loginPassword');
const loginMessage = document.getElementById('loginMessage');

// 获取注册相关DOM元素
const registerSubmitBtn = document.getElementById('registerSubmitBtn');
const registerUsername = document.getElementById('registerUsername');
const registerEmail = document.getElementById('registerEmail');
const registerPassword = document.getElementById('registerPassword');
const registerConfirmPassword = document.getElementById('registerConfirmPassword');
const registerMessage = document.getElementById('registerMessage');

// 登录功能
loginSubmitBtn.addEventListener('click', () => {
    const username = loginUsername.value.trim();
    const password = loginPassword.value.trim();
    
    // 简单验证
    if (!username || !password) {
        loginMessage.innerHTML = '<div class="alert alert-danger">请输入用户名和密码</div>';
        return;
    }
    
    // 发送真实登录请求
    loginMessage.innerHTML = '<div class="alert alert-info">正在登录...</div>';
    
    fetch('/login/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: username,
            password: password
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.code === 0) {
            loginMessage.innerHTML = '<div class="alert alert-success">登录成功！</div>';
            
            // 关闭模态框
            const loginModal = new bootstrap.Modal(document.getElementById('loginModal'));
            loginModal.hide();
            
            // 重置表单
            document.getElementById('loginForm').reset();
            
            // 可以在这里保存token等信息
            if (data.data && data.data.access_token) {
                localStorage.setItem('token', data.data.access_token);
            }
        } else {
            // 安全处理错误消息，确保不会显示undefined
            const errorMsg = data.msg || '未知错误';
            loginMessage.innerHTML = `<div class="alert alert-danger">${errorMsg}</div>`;
        }
    })
    .catch(error => {
        loginMessage.innerHTML = '<div class="alert alert-danger">登录失败，请稍后重试</div>';
        console.error('登录请求错误:', error);
    });
});

// 注册功能
registerSubmitBtn.addEventListener('click', () => {
    const username = registerUsername.value.trim();
    const email = registerEmail.value.trim();
    const password = registerPassword.value.trim();
    const confirmPassword = registerConfirmPassword.value.trim();
    
    // 简单验证
    if (!username || !email || !password || !confirmPassword) {
        registerMessage.innerHTML = '<div class="alert alert-danger">请填写所有必填字段</div>';
        return;
    }
    
    if (username.length < 3 || username.length > 20) {
        registerMessage.innerHTML = '<div class="alert alert-danger">用户名长度应在3-20个字符之间</div>';
        return;
    }
    
    if (password.length < 6) {
        registerMessage.innerHTML = '<div class="alert alert-danger">密码长度应至少为6个字符</div>';
        return;
    }
    
    if (password !== confirmPassword) {
        registerMessage.innerHTML = '<div class="alert alert-danger">两次输入的密码不一致</div>';
        return;
    }
    
    // 发送真实注册请求
    registerMessage.innerHTML = '<div class="alert alert-info">正在注册...</div>';
    
    fetch('/register/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: username,
            email: email,
            password: password,
            confirm_password: confirmPassword
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errData => {
                if (response.status === 422) {
                    // 解析422错误的详细信息
                    let errorMessage = '验证错误: ';
                    if (errData.detail && Array.isArray(errData.detail)) {
                        errorMessage += errData.detail.map(item => `${item.loc[1]}: ${item.msg}`).join('; ');
                    } else {
                        errorMessage += JSON.stringify(errData.detail || '参数验证失败');
                    }
                    throw new Error(errorMessage);
                } else {
                    throw new Error(`HTTP错误: ${response.status} - ${errData.msg || '请求失败'}`);
                }
            }).catch(() => {
                // 如果无法解析JSON响应，抛出通用错误
                throw new Error(`HTTP错误: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.code === 0) {
            registerMessage.innerHTML = '<div class="alert alert-success">注册成功！</div>';
            
            // 关闭模态框
            const registerModal = new bootstrap.Modal(document.getElementById('registerModal'));
            registerModal.hide();
            
            // 重置表单
            document.getElementById('registerForm').reset();
        } else {
            // 安全处理错误消息，确保不会显示undefined
            const errorMsg = data.msg || '未知错误';
            registerMessage.innerHTML = `<div class="alert alert-danger">${errorMsg}</div>`;
        }
    })
    .catch(error => {
        registerMessage.innerHTML = `<div class="alert alert-danger">注册失败: ${error.message}</div>`;
        console.error('注册请求错误:', error);
    });
});

// 回车键提交登录
loginPassword.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        loginSubmitBtn.click();
    }
});

// 回车键提交注册
registerConfirmPassword.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        registerSubmitBtn.click();
    }
});