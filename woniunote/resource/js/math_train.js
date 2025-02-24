// ==================== 常量定义 ====================
const OPERATORS = ['+', '-', '×', '÷'];
const QUESTIONS_PER_ROW = 4;
const TOTAL_ROWS = 5;
const INITIAL_TIME = 0;

// ==================== DOM元素引用 ====================
const DOM = {
  grid: document.getElementById('grid'),
  newBtn: document.getElementById('newBtn'),
  checkBtn: document.getElementById('checkBtn'),
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
  loggedIn: false,   // 默认未登录
  username: '',       // 存储用户名
  timerStarted: false, // 标记计时是否已经开始
  currentFocusIndex: 0
};

// ==================== 核心功能 ====================
const initInputsArray = () => {
  state.inputsArray = Array.from(document.querySelectorAll('.answer-input'));
  state.inputsArray.forEach((input, index) => {
    input.dataset.index = index;
    input.addEventListener('focus', () => {
      state.currentFocusIndex = index;
      updateFocusStyle();  // 确保updateFocusStyle已定义
    });
  });
};

// 添加updateFocusStyle函数
const updateFocusStyle = () => {
  const currentInput = state.inputsArray[state.currentFocusIndex];
  if (currentInput) {
    currentInput.style.borderColor = 'blue';  // 示例，改变焦点元素的边框颜色
  }
};

// 生成问题
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

  timerManager.start();
  state.currentFocusIndex = 0;
  setTimeout(() => {
    updateFocusStyle();
    state.inputsArray[0]?.focus();
  }, 0);
};

const checkAnswers = () => {
  const audio = new Audio('/sfx/submit.mp3');
  audio.play();

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

  setTimeout(generateQuestions, 1500);
};

const timerManager = {
  start: () => {
    if (state.timerStarted) return;
    state.timerStarted = true;
    state.timer = setInterval(() => {
      state.time++;
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

// ==================== 用户状态管理 ====================

async function handleMathLogin(e) {
  e.preventDefault();
  const username = document.getElementById('mathTrainUsername').value.trim();
  const password = document.getElementById('mathTrainPassword').value;
  if (!username) {
    alert('用户名不能为空');
    return;
  }
  if (!password) {
    alert('密码不能为空');
    return;
  }

  const loginButton = document.getElementById('loginBtn');
  try {
    const response = await fetch('/math_train_login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    if (!response.ok) {
      throw new Error(`HTTP错误! 状态码: ${response.status}`);
    }

    const result = await response.json();

    if (result.success) {
      localStorage.setItem('mathTrainUser', JSON.stringify({
        username: result.username,
        lastLogin: new Date().toISOString()
      }));

      document.getElementById('navbarUsername').textContent = result.username;
      document.getElementById('logoutBtn').style.display = 'inline-block';
      document.getElementById('userCenterBtn').style.display = 'inline-block';
      document.getElementById('showLoginModalBtn').style.display = 'none';

      const modal = document.getElementById('loginModal');
      if (modal) modal.style.display = 'none';

      state.loggedIn = true;  // 登录状态更新
      state.username = result.username;
    } else {
      alert(`登录失败: ${result.message || '未知错误'}`);
    }
  } catch (error) {
    alert(`请求失败: ${error.message}`);
  } finally {
    // loginButton.disabled = false;
    // loginButton.textContent = '登录';
    console.log('登录按钮已恢复');
  }
}

async function handleLogout() {
  try {
    const res = await fetch('/math_train_logout', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      localStorage.removeItem('mathTrainUser');
      document.getElementById('navbarUsername').textContent = '';
      document.getElementById('logoutBtn').style.display = 'none';
      document.getElementById('userCenterBtn').style.display = 'none';
      document.getElementById('showLoginModalBtn').style.display = 'inline-block';
      state.loggedIn = false;
      state.username = '';
    }
  } catch (error) {
    console.error('退出失败:', error);
  }
}

// ==================== 模态框动画控制 ====================

function showModal(modalId) {
  const modal = document.getElementById(modalId);
  modal.classList.add('show');
  modal.style.display = 'flex';
}

function hideModal(modalId) {
  const modal = document.getElementById(modalId);
  modal.classList.remove('show');
  setTimeout(() => {
    modal.style.display = 'none';
  }, 300);
}

// ==================== 事件绑定 ====================

const setupEventListeners = () => {
  if (DOM.newBtn) {
    DOM.newBtn.addEventListener('click', generateQuestions);
  }

  if (DOM.checkBtn) {
    DOM.checkBtn.addEventListener('click', checkAnswers);
  }

  if (DOM.navbarElements.login) {
    DOM.navbarElements.login.addEventListener('click', () => {
      showModal('loginModal');
    });
  }

  const mathLoginForm = document.getElementById('mathTrainLoginForm');
  if (mathLoginForm) {
    mathLoginForm.addEventListener('submit', handleMathLogin);
  }

  if (DOM.navbarElements.register) {
    DOM.navbarElements.register.addEventListener('click', () => {
      showModal('registerModal');
    });
  }

  if (document.getElementById('userCenterBtn')) {
    document.getElementById('userCenterBtn').addEventListener('click', () => {
      if (state.loggedIn) {
        window.location.href = '/math_train_user';
      } else {
        alert('请先登录');
      }
    });
  }

  if (document.getElementById('logoutBtn')) {
    document.getElementById('logoutBtn').addEventListener('click', async () => {
      await handleLogout();
    });
  }

  window.addEventListener('click', (event) => {
    if (event.target.classList.contains('modal')) {
      document.querySelectorAll('.modal').forEach(m => hideModal(m.id));
    }
  });
};

// ==================== 页面初始化 ====================
const init = () => {
  const user = localStorage.getItem('mathTrainUser');
  if (user) {
    const parsedUser = JSON.parse(user);
    state.loggedIn = true;
    state.username = parsedUser.username;
    document.getElementById('navbarUsername').textContent = state.username;
    document.getElementById('logoutBtn').style.display = 'inline-block';
    document.getElementById('userCenterBtn').style.display = 'inline-block';
    document.getElementById('showLoginModalBtn').style.display = 'none';
  }

  generateQuestions();
  setupEventListeners();
};

document.addEventListener('DOMContentLoaded', init);








