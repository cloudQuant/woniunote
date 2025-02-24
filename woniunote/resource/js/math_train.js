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
  startBtn: document.getElementById('beginBtn'),  // 修改为正确的 ID
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
    return { num1: num1 * num2, num2, operator };  // 保证除法运算结果是整数
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

const checkAnswers = () => {
  let correctAnswers = 0;
  state.inputsArray.forEach(input => {
    const questionElement = input.closest('.question-item');
    const num1 = parseInt(questionElement.querySelector('.number').textContent);
    const num2 = parseInt(questionElement.querySelectorAll('.number')[1].textContent);
    const operator = questionElement.querySelector('.operator').textContent;

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
    }

    if (parseInt(input.value) === correctAnswer) {
      input.style.backgroundColor = 'lightgreen'; // 正确答案
      correctAnswers++;
    } else {
      input.style.backgroundColor = 'lightcoral'; // 错误答案
    }
  });

  state.correctCount = correctAnswers;
  // 保存结果到后端
  fetch('/math_train_save_result', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      math_level: 1,
      correct_count: state.correctCount,
      total_questions: state.inputsArray.length,
      time_spent: state.time
    })
  });
  alert(`答对了 ${correctAnswers} 道题目，共 ${state.inputsArray.length} 道题目`);
};

// ==================== 计时器管理 ====================

const timerManager = {
  start: () => {
    if (state.timerStarted) return; // 防止重复计时
    state.timerStarted = true;
    state.timer = setInterval(() => {
      state.time++;
      //DOM.minutes.textContent = String(Math.floor(state.time / 60)).padStart(2, '0');
      //DOM.seconds.textContent = String(state.time % 60).padStart(2, '0');
      DOM.minutes.textContent = String(Math.floor(state.time / 60)).padStart(2, '0');
      DOM.seconds.textContent = String(state.time % 60).padStart(2, '0');
      document.getElementById('totalSeconds').textContent = `(${state.time}秒)`;
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
        document.getElementById('loginModal').style.display = 'none'; // 关闭登录模态框
        window.location.href = data.redirect;
      } else {
        alert(data.message || '登录失败');
      }
    } catch (error) {
      alert('网络连接错误，请重试');
      console.error('登录请求失败:', error);
    }
  },

  handleRegister: async (username, password, email) => {
    try {
      const res = await fetch('/math_train_register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, email })
      });

      const data = await res.json();
      if (data.success) {
        alert('注册成功！请登录');
        document.getElementById('registerModal').style.display = 'none'; // 关闭注册模态框
        document.getElementById('loginModal').style.display = 'block'; // 打开登录模态框
      } else {
        alert(data.message || '注册失败');
      }
    } catch (error) {
      alert('网络连接错误，请重试');
      console.error('注册请求失败:', error);
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
  DOM.startBtn.addEventListener('click', () => {
    timerManager.start();
    alert("开始做题！");
  });
  DOM.checkBtn.addEventListener('click', checkAnswers); // 修改为检查答案

  // 登录按钮事件
  DOM.navbarElements.login.addEventListener('click', () => {
    document.getElementById('loginModal').style.display = 'block'; // 打开登录对话框
  });

  // 注册按钮事件
  DOM.navbarElements.register.addEventListener('click', () => {
    document.getElementById('registerModal').style.display = 'block'; // 打开注册对话框
  });

  // 登录提交事件
  document.getElementById('loginBtn').addEventListener('click', () => {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    AuthManager.handleLogin(username, password);
  });

  // 注册提交事件
  document.getElementById('registerBtn').addEventListener('click', () => {
    const username = document.getElementById('registerUsername').value;
    const password = document.getElementById('registerPassword').value;
    const email = document.getElementById('registerEmail').value;
    AuthManager.handleRegister(username, password, email);
  });

  // 用户中心按钮
  document.getElementById('userCenterBtn').addEventListener('click', () => {
    if (state.loggedIn) {
      window.location.href = '/math_train_user'; // 正常跳转
    } else {
      alert('请先登录');
    }
  });

  // 退出按钮
  document.getElementById('logoutBtn').addEventListener('click', async () => {
    await AuthManager.handleLogout();
  });

  // 关闭弹出框
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
