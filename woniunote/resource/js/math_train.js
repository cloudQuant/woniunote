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
  correctCount: 0
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

// ==================== 答案验证 ====================
const validateAnswers = () => {
  state.correctCount = 0;
  document.querySelectorAll('.answer-input').forEach(input => {
    const elements = input.parentElement;
    const [a, b] = Array.from(elements.querySelectorAll('.number')).map(n => parseInt(n.textContent));
    const operator = elements.querySelector('.operator').textContent;

    const operations = {
      '+': (x, y) => x + y,
      '-': (x, y) => x - y,
      '×': (x, y) => x * y,
      '÷': (x, y) => x / y
    };

    const correct = operations[operator](a, b);
    const userAnswer = parseInt(input.value);

    input.classList.toggle('correct', userAnswer === correct);
    input.classList.toggle('wrong', userAnswer !== correct);
    if (userAnswer === correct) state.correctCount++;
  });

  return { count: state.correctCount, total: state.inputsArray.length };
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
const authManager = {
  checkStatus: async () => {
    try {
      const response = await fetch('/math_train_check_login');
      const data = await response.json();
      this.updateUI(data.loggedIn, data.username);
    } catch (error) {
      console.error('登录状态检查失败:', error);
    }
  },

  updateUI: (loggedIn, username) => {
    const elements = DOM.navbarElements;
    const display = loggedIn ? ['none', 'inline-block'] : ['inline-block', 'none'];

    [elements.login, elements.register].forEach(el => el.style.display = display[0]);
    [elements.logout, elements.userCenter].forEach(el => el.style.display = display[1]);

    elements.username.textContent = loggedIn ? username : '';
    elements.username.style.display = loggedIn ? 'inline-block' : 'none';
  },

  handleLogout: () => {
    window.location.href = '/math_train_logout';
    setTimeout(() => window.location.reload(), 200);
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
      result.success ? window.location.href = '/math_train_user' : alert(result.message);
    } catch {
      alert('登录失败');
    }
  });

  document.getElementById('registerBtn').addEventListener('click', async () => {
    const username = document.getElementById('registerUsername').value;
    const password = document.getElementById('registerPassword').value;

    if (!username || !password) return alert('请输入用户名和密码');

    try {
      const result = await apiRequest('/math_train_register', 'POST', { username, password });
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
  const modalControls = {
    showLogin: () => toggleModals('flex', 'none'),
    showRegister: () => toggleModals('none', 'flex'),
    closeAll: (event) => {
      if (event.target.classList.contains('modal')) {
        document.querySelectorAll('.modal').forEach(m => m.style.display = 'none');
      }
    }
  };

  const toggleModals = (loginDisplay, registerDisplay) => {
    DOM.loginModal.style.display = loginDisplay;
    DOM.registerModal.style.display = registerDisplay;
  };

  document.querySelectorAll('[data-modal]').forEach(btn => {
    btn.addEventListener('click', modalControls[`show${btn.dataset.modal}`]);
  });

  window.addEventListener('click', modalControls.closeAll);
  document.getElementById('logoutBtn').addEventListener('click', authManager.handleLogout);
};

// ==================== 初始化 ====================
const init = () => {
  generateQuestions();
  timerManager.start();
  authManager.checkStatus();
  setupEventListeners();
};

document.addEventListener('DOMContentLoaded', init);