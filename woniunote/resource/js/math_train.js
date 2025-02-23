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
  startBtn: document.getElementById('beginBtn'),
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
  username: '',
  timerStarted: false
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

const checkAnswers = () => {
  let correctAnswers = 0;
  state.inputsArray.forEach(input => {
    const questionElement = input.closest('.question-item');
    const num1 = parseInt(questionElement.querySelector('.number').textContent);
    const num2 = parseInt(questionElement.querySelectorAll('.number')[1].textContent);
    const operator = questionElement.querySelector('.operator').textContent;

    let correctAnswer;
    switch (operator) {
      case '+': correctAnswer = num1 + num2; break;
      case '-': correctAnswer = num1 - num2; break;
      case '×': correctAnswer = num1 * num2; break;
      case '÷': correctAnswer = num1 / num2; break;
    }

    if (parseInt(input.value) === correctAnswer) {
      input.style.backgroundColor = 'lightgreen';
      correctAnswers++;
    } else {
      input.style.backgroundColor = 'lightcoral';
    }
  });

  state.correctCount = correctAnswers;
  alert(`答对了 ${correctAnswers} 道题目，共 ${state.inputsArray.length} 道题目`);
};

// ==================== 计时器管理 ====================
const timerManager = {
  start: () => {
    if (state.timerStarted) return;
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
      credentials: 'include', // 关键修复：携带cookie
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    if (response.status === 401) {
      AuthManager.handleLogout();
      throw new Error('需要重新登录');
    }

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
      const res = await fetch('/math_train_check_login', {
        credentials: 'include' // 携带cookie
      });
      const data = await res.json();

      if (data.loggedIn) {
        state.loggedIn = true;
        state.username = data.username;
        DOM.navbarElements.username.textContent = `欢迎，${data.username}`;
        document.querySelectorAll('.logged-in').forEach(el => el.style.display = 'inline-block');
        document.querySelectorAll('.logged-out').forEach(el => el.style.display = 'none');
      } else {
        this.handleLogout();
      }
    } catch (error) {
      console.error('登录状态检查失败:', error);
    }
  },

  handleLogin: async (username, password) => {
    try {
      const res = await apiRequest('/math_train_login', 'POST', { username, password });

      if (res.success) {
        await this.checkStatus();
        document.getElementById('loginModal').style.display = 'none';
        window.location.href = res.redirect;
      } else {
        alert(res.message || '登录失败');
      }
    } catch (error) {
      alert('登录请求失败，请检查网络');
    }
  },

  handleRegister: async (username, password, email) => {
    try {
      const res = await apiRequest('/math_train_register', 'POST', { username, password, email });

      if (res.success) {
        alert('注册成功！请登录');
        document.getElementById('registerModal').style.display = 'none';
        document.getElementById('loginModal').style.display = 'block';
      } else {
        alert(res.message || '注册失败');
      }
    } catch (error) {
      alert('注册请求失败，请检查网络');
    }
  },

  handleLogout: async () => {
    try {
      await apiRequest('/math_train_logout', 'POST');
      state.loggedIn = false;
      state.username = '';
      DOM.navbarElements.username.textContent = '';
      document.querySelectorAll('.logged-in').forEach(el => el.style.display = 'none');
      document.querySelectorAll('.logged-out').forEach(el => el.style.display = 'inline-block');
      window.location.href = '/math_train';
    } catch (error) {
      console.error('退出失败:', error);
    }
  }
};

// ==================== 事件绑定 ====================
const setupEventListeners = () => {
  DOM.newBtn.addEventListener('click', generateQuestions);
  DOM.startBtn.addEventListener('click', () => {
    timerManager.start();
    alert("开始做题！");
  });
  DOM.checkBtn.addEventListener('click', checkAnswers);

  // 登录相关
  DOM.navbarElements.login.addEventListener('click', () => {
    document.getElementById('loginModal').style.display = 'block';
  });

  // 注册相关
  DOM.navbarElements.register.addEventListener('click', () => {
    document.getElementById('registerModal').style.display = 'block';
  });

  document.getElementById('loginBtn').addEventListener('click', () => {
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value.trim();
    if (!username || !password) return alert('请输入用户名和密码');
    AuthManager.handleLogin(username, password);
  });

  document.getElementById('registerBtn').addEventListener('click', () => {
    const username = document.getElementById('registerUsername').value.trim();
    const password = document.getElementById('registerPassword').value.trim();
    const email = document.getElementById('registerEmail').value.trim();
    if (!username || !password || !email) return alert('请填写完整信息');
    AuthManager.handleRegister(username, password, email);
  });

  // 用户中心跳转
  document.getElementById('userCenterBtn').addEventListener('click', () => {
    if (state.loggedIn) {
      window.location.href = '/math_train_user';
    } else {
      alert('请先登录');
      document.getElementById('loginModal').style.display = 'block';
    }
  });

  // 退出登录
  document.getElementById('logoutBtn').addEventListener('click', () => {
    AuthManager.handleLogout();
  });

  // 模态框关闭
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











