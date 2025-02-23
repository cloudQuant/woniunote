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
  loggedIn: false,
  username: ''
};

// ==================== 核心功能 ====================
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

// ==================== 用户状态管理 ====================
const authManager = {
  checkStatus: async () => {
    try {
      const response = await fetch('/math_train_check_login');
      const data = await response.json();
      state.loggedIn = data.loggedIn;
      state.username = data.username;
      authManager.updateUI();
    } catch (error) {
      console.error('登录状态检查失败:', error);
    }
  },

  updateUI: () => {
    const elements = DOM.navbarElements;
    if (state.loggedIn) {
      elements.login.style.display = 'none';
      elements.register.style.display = 'none';
      elements.logout.style.display = 'inline-block';
      elements.userCenter.style.display = 'inline-block';
      elements.username.textContent = state.username;
      elements.username.style.display = 'inline-block';
    } else {
      elements.login.style.display = 'inline-block';
      elements.register.style.display = 'inline-block';
      elements.logout.style.display = 'none';
      elements.userCenter.style.display = 'none';
      elements.username.style.display = 'none';
    }
  },

  handleLogout: async () => {
    await fetch('/math_train_logout', { method: 'POST' });
    state.loggedIn = false;
    state.username = '';
    authManager.updateUI();
    window.location.href = '/math_train';  // 重定向到训练页面
  }
};

// ==================== 初始化 ====================
const init = () => {
  generateQuestions();
  timerManager.start();
  authManager.checkStatus();
  setupEventListeners();
};

document.addEventListener('DOMContentLoaded', init);
