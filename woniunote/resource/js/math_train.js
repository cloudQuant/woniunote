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
        document.querySelectorAll('.logged-in').forEach(el => el.style.display = 'inline-block');
        document.querySelectorAll('.logged-out').forEach(el => el.style.display = 'none');
        document.getElementById('navbarUsername').textContent = data.username;
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
        state.username = username;
        AuthManager.updateUI();
        document.getElementById('loginModal').style.display = 'none';
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
  DOM.checkBtn.addEventListener('click', () => {
    const { count, total } = validateAnswers();
    timerManager.reset();

    apiRequest('/math_train_save_result', 'POST', {
      math_level: 'basic',
      correct_count: count,
      total_questions: total,
      time_spent: state.time
    }).then(() => {
      alert(`正确率：${count}/${total}\n用时：${DOM.minutes.textContent}分${DOM.seconds.textContent}秒`);
    });
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

    try {
      const result = await apiRequest('/math_train_login', 'POST', { username, password });
      if (result.success) {
        state.loggedIn = true;
        state.username = username;
        AuthManager.updateUI();
        document.getElementById('loginModal').style.display = 'none';
      } else {
        alert(result.message);
      }
    } catch {
      alert('登录失败');
    }
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

  document.getElementById('showRegisterModalBtn').addEventListener('click', () => {
    DOM.loginModal.style.display = 'none';
    DOM.registerModal.style.display = 'flex';
  });

  // 关闭对话框
  window.addEventListener('click', (event) => {
    if (event.target.classList.contains('modal')) {
      document.querySelectorAll('.modal').forEach(m => m.style.display = 'none');
    }
  });

  document.getElementById('logoutBtn').addEventListener('click', AuthManager.handleLogout);
};

const validateAnswers = () => {
  let correctCount = 0;
  const total = state.inputsArray.length;

  state.inputsArray.forEach((input) => {
    const answer = parseInt(input.value, 10);
    const question = input.closest('.question-item');
    const num1 = parseInt(question.querySelector('.number:first-child').textContent, 10);
    const operator = question.querySelector('.operator:nth-child(2)').textContent;
    const num2 = parseInt(question.querySelector('.number:nth-child(3)').textContent, 10);

    let correctAnswer;
    switch (operator) {
      case '+':
        correctAnswer = num1 + num2;
        break;
      case '-':
        correctAnswer = num1 - num2;
        break;
      case '×':
        correctAnswer = num1 * num2;
        break;
      case '÷':
        correctAnswer = num1 / num2;
        break;
      default:
        break;
    }

    if (answer === correctAnswer) {
      correctCount++;
    }
  });

  return { count: correctCount, total };
};

// ==================== 初始化 ====================
const init = () => {
  generateQuestions();
  timerManager.start();
  AuthManager.checkStatus();
  setupEventListeners();
};

document.addEventListener('DOMContentLoaded', init);

