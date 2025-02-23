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
  startBtn: document.getElementById('startBtn'),
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
  username: '',       // 存储用户名
  timerStarted: false // 标记计时是否已经开始
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

// 生成计算题，无需检查登录状态
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
    if (state.timerStarted) return; // 防止重复计时
    state.timerStarted = true;
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
    state.timerStarted = false;
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
  checkStatus: () => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      state.loggedIn = true;
      state.username = JSON.parse(storedUser).username;
      AuthManager.updateUI();
    } else {
      state.loggedIn = false;
      AuthManager.updateUI();
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
        localStorage.setItem('user', JSON.stringify({ username }));
        state.loggedIn = true;
        state.username = data.username;
        AuthManager.updateUI();
        window.location.href = data.redirect;
      } else {
        alert(data.message || '登录失败');
      }
    } catch (error) {
      alert('网络连接错误，请重试');
      console.error('登录请求失败:', error);
    }
  },

  handleLogout: async () => {
    try {
      const res = await fetch('/math_train_logout', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        localStorage.removeItem('user');
        state.loggedIn = false;
        state.username = '';
        AuthManager.updateUI();
        alert('退出成功');
        window.location.href = data.redirect;
      }
    } catch (error) {
      alert('退出失败，请重试');
      console.error('退出请求失败:', error);
    }
  },

  updateUI: () => {
    if (state.loggedIn) {
      document.querySelectorAll('.logged-in').forEach(el => el.style.display = 'inline-block');
      document.querySelectorAll('.logged-out').forEach(el => el.style.display = 'none');
      DOM.navbarElements.username.textContent = `欢迎，${state.username}`;
    } else {
      document.querySelectorAll('.logged-in').forEach(el => el.style.display = 'none');
      document.querySelectorAll('.logged-out').forEach(el => el.style.display = 'inline-block');
      DOM.navbarElements.username.textContent = '';
    }
  }
};

// ==================== 事件绑定 ====================

const setupEventListeners = () => {
  DOM.newBtn.addEventListener('click', generateQuestions);
  DOM.startBtn.addEventListener('click', timerManager.start);
  DOM.checkBtn.addEventListener('click', () => {
    timerManager.reset();
    alert('答案已提交');
  });

  document.getElementById('userCenterBtn').addEventListener('click', () => {
    alert('跳转到用户中心');
  });

  document.getElementById('logoutBtn').addEventListener('click', async () => {
    await AuthManager.handleLogout();
  });

  window.addEventListener('click', (event) => {
    if (event.target.classList.contains('modal')) {
      document.querySelectorAll('.modal').forEach(m => m.style.display = 'none');
    }
  });
};

// ==================== 初始化 ====================
const init = () => {
  AuthManager.checkStatus();
  generateQuestions();
  setupEventListeners();
};

document.addEventListener('DOMContentLoaded', init);







