// ==================== 常量定义 ====================
const OPERATORS = ['+', '-', '×', '÷'];
const QUESTIONS_PER_ROW = 4;
const TOTAL_ROWS = 5;
const INITIAL_TIME = 0;

// ==================== DOM元素引用 ====================
const DOM = {
  grid: document.getElementById('grid'),
  checkBtn: document.getElementById('checkBtn'),
  newBtn: document.getElementById('newBtn'),
  minutes: document.getElementById('minutes'),
  seconds: document.getElementById('seconds'),
  loginModal: document.getElementById('loginModal'),
  registerModal: document.getElementById('registerModal'),
  navbarElements: {
    login: document.getElementById('showLoginModalBtn'),
    register: document.getElementById('showRegisterModalBtn'),
    logout: document.getElementById('logoutBtn'),
    userCenter: document.getElementById('userCenterBtn'),
    username: document.getElementById('navbarUsername')
  }
};

// ==================== 状态管理 ====================
let state = {
  inputsArray: [],
  currentIndex: 0,
  timer: null,
  time: INITIAL_TIME,
  correctCount: 0,
  loggedIn: false,   // 默认未登录
  username: ''       // 存储用户名
};

// ==================== 核心功能 ====================
const initInputsArray = () => {
  state.inputsArray = Array.from(document.querySelectorAll('.answer-input'));
  state.inputsArray.forEach((input, index) => input.dataset.index = index);
};

const generateQuestion = () => {
  let num1 = Math.floor(Math.random() * 20) + 1;
  let num2 = Math.floor(Math.random() * 20) + 1;
  const operator = OPERATORS[Math.floor(Math.random() * OPERATORS.length)];

  if (operator === '÷') {
    while (num2 === 0) num2 = Math.floor(Math.random() * 20) + 1;
    return { num1: num1 * num2, num2, operator };
  }

  return { num1, num2, operator };
};

const createQuestionElement = ({ num1, num2, operator }) => {
  const question = document.createElement('div');
  question.className = 'question-item';
  question.innerHTML = `
    <span class="number">${num1}</span>
    <span class="operator">${operator}</span>
    <span class="number">${num2}</span>
    <span class="operator">=</span>
    <input class="answer-input" type="number" placeholder="?">
  `;
  return question;
};

const generateQuestions = () => {
  DOM.grid.innerHTML = '';
  const fragment = document.createDocumentFragment();

  for (let i = 0; i < TOTAL_ROWS; i++) {
    const rowDiv = document.createElement('div');
    rowDiv.className = 'question-row';

    for (let j = 0; j < QUESTIONS_PER_ROW; j++) {
      rowDiv.appendChild(createQuestionElement(generateQuestion()));
    }
    fragment.appendChild(rowDiv);
  }

  DOM.grid.appendChild(fragment);
  initInputsArray();
};

// ==================== 计时器管理 ====================
const timerManager = {
  start: () => {
    state.timer = setInterval(() => {
      state.time++;
      DOM.minutes.textContent = String(Math.floor(state.time / 60)).padStart(2, '0');
      DOM.seconds.textContent = String(state.time % 60).padStart(2, '0');
    }, 1000);
  },

  reset: () => {
    state.time = INITIAL_TIME;
    DOM.minutes.textContent = '00';
    DOM.seconds.textContent = '00';
    clearInterval(state.timer);
  }
};

// ==================== 网络请求 ====================
const apiRequest = async (url, method, data) => {
  try {
    const response = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await response.json();
  } catch (error) {
    console.error(`${method}请求失败:`, error);
    throw error;
  }
};

// ==================== 用户状态管理 ====================
const AuthManager = {
  checkStatus: async () => {
    try {
      const res = await fetch('/math_train_check_login');
      const data = await res.json();

      if (data.loggedIn) {
        state.loggedIn = true;
        state.username = data.username;
        document.querySelectorAll('.logged-in').forEach(el => el.style.display = 'inline-block');
        document.querySelectorAll('.logged-out').forEach(el => el.style.display = 'none');
        document.getElementById('navbarUsername').textContent = state.username;
      } else {
        document.querySelectorAll('.logged-in').forEach(el => el.style.display = 'none');
        document.querySelectorAll('.logged-out').forEach(el => el.style.display = 'inline-block');
      }
    } catch (error) {
      console.error('登录状态检查失败:', error);
    }
  },

  handleLogin: async (username, password) => {
    try {
      const res = await fetch('/math_train_login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      const data = await res.json();
      if (data.success) {
        state.loggedIn = true;
        state.username = data.username;
        AuthManager.updateUI();
        window.location.href = data.redirect;
      } else {
        alert(data.message || '登录失败');
      }
    } catch {
      alert('登录失败');
    }
  },

  handleLogout: async () => {
    try {
      const res = await fetch('/math_train_logout', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        state.loggedIn = false;
        state.username = '';
        AuthManager.updateUI();
        window.location.href = data.redirect;
      }
    } catch (error) {
      console.error('退出失败:', error);
    }
  },

  updateUI: () => {
    if (state.loggedIn) {
      DOM.navbarElements.login.style.display = 'none';
      DOM.navbarElements.register.style.display = 'none';
      DOM.navbarElements.logout.style.display = 'inline-block';
      DOM.navbarElements.userCenter.style.display = 'inline-block';
      DOM.navbarElements.username.textContent = state.username;
    } else {
      DOM.navbarElements.login.style.display = 'inline-block';
      DOM.navbarElements.register.style.display = 'inline-block';
      DOM.navbarElements.logout.style.display = 'none';
      DOM.navbarElements.userCenter.style.display = 'none';
    }
  }
};

// ==================== 事件监听 ====================
const setupEventListeners = () => {
  // 控制按钮
  DOM.checkBtn.addEventListener('click', async () => {
    const { count, total } = validateAnswers();
    timerManager.reset();

    const result = await apiRequest('/math_train_save_result', 'POST', {
      math_level: 'basic',
      correct_count: count,
      total_questions: total,
      time_spent: state.time
    });

    if (result.success) {
      alert(`正确率：${count}/${total}\n用时：${DOM.minutes.textContent}分${DOM.seconds.textContent}秒`);
    } else {
      alert(result.message || '保存结果失败');
    }
  });

  DOM.newBtn.addEventListener('click', () => {
    generateQuestions();
    timerManager.reset();
    timerManager.start();
  });

  // 登录/注册相关
  document.getElementById('loginBtn').addEventListener('click', async () => {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;

    if (!username || !password) return alert('请输入用户名和密码');

    await AuthManager.handleLogin(username, password);
  });

  document.getElementById('registerBtn').addEventListener('click', async () => {
    const username = document.getElementById('registerUsername').value;
    const password = document.getElementById('registerPassword').value;
    const email = document.getElementById('registerEmail').value;

    if (!username || !password || !email) return alert('请输入用户名和密码');

    try {
      const result = await apiRequest('/math_train_register', 'POST', { username, password, email });
      if (result.success) {
        alert('注册成功');
        document.getElementById('registerModal').style.display = 'none';
        document.getElementById('loginModal').style.display = 'flex';
      } else {
        alert(result.message);
      }
    } catch {
      alert('注册失败');
    }
  });

  // 对话框控制
  document.getElementById('showLoginModalBtn').addEventListener('click', () => {
    DOM.loginModal.style.display = 'flex';
    DOM.registerModal.style.display = 'none';
  });

  document.getElementById('showRegisterModalBtn').addEventListener('

