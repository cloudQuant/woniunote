// ==================== 常量定义 ====================
const OPERATORS = ['+', '-', '×', '÷'];
const QUESTIONS_PER_ROW = 4;
const TOTAL_ROWS = 5;
const INITIAL_TIME = 0;

// ==================== DOM元素引用 ====================
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const loginBtn = document.getElementById('loginBtn');
const registerBtn = document.getElementById('registerBtn');
const grid = document.getElementById('grid');
const checkBtn = document.getElementById('checkBtn');
const newBtn = document.getElementById('newBtn');
const minutes = document.getElementById('minutes');
const seconds = document.getElementById('seconds');

// 获取对话框相关元素
const loginModal = document.getElementById('loginModal');
const registerModal = document.getElementById('registerModal');
const showLoginModalBtn = document.getElementById('showLoginModalBtn');
const showRegisterModalBtn = document.getElementById('showRegisterModalBtn');
const switchToRegister = document.getElementById('switchToRegister');
const switchToLogin = document.getElementById('switchToLogin');

// ==================== 状态变量 ====================
let inputsArray = [];
let currentIndex = 0;
let timer = null;
let time = INITIAL_TIME;
let correctCount = 0;

// ==================== 核心功能 ====================
// 初始化题目输入框数组
const initInputsArray = () => {
  inputsArray = Array.from(document.querySelectorAll('.answer-input'));
  inputsArray.forEach((input, index) => input.dataset.index = index);
};

// 生成单个题目
const generateQuestion = () => {
  let num1 = Math.floor(Math.random() * 20) + 1;
  let num2 = Math.floor(Math.random() * 20) + 1;
  const operator = OPERATORS[Math.floor(Math.random() * OPERATORS.length)];

  // 处理除法特殊情况
  if (operator === '÷') {
    while (num2 === 0) num2 = Math.floor(Math.random() * 20) + 1;
    const dividend = num1 * num2;
    return { num1: dividend, num2, operator };
  }

  return { num1, num2, operator };
};

// 创建题目DOM元素
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

// 生成所有题目
const generateQuestions = () => {
  grid.innerHTML = '';
  const fragment = document.createDocumentFragment();

  for (let i = 0; i < TOTAL_ROWS; i++) {
    const rowDiv = document.createElement('div');
    rowDiv.className = 'question-row';

    for (let j = 0; j < QUESTIONS_PER_ROW; j++) {
      rowDiv.appendChild(createQuestionElement(generateQuestion()));
    }
    fragment.appendChild(rowDiv);
  }

  grid.appendChild(fragment);
  initInputsArray();
};

// ==================== 计时器功能 ====================
const updateTimer = () => {
  time++;
  minutes.textContent = String(Math.floor(time / 60)).padStart(2, '0');
  seconds.textContent = String(time % 60).padStart(2, '0');
};

const startTimer = () => {
  timer = setInterval(updateTimer, 1000);
};

const resetTimer = () => {
  time = INITIAL_TIME;
  minutes.textContent = '00';
  seconds.textContent = '00';
};

// ==================== 答案检查功能 ====================
const calculateCorrectAnswer = (operator, a, b) => {
  const operations = {
    '+': (x, y) => x + y,
    '-': (x, y) => x - y,
    '×': (x, y) => x * y,
    '÷': (x, y) => x / y
  };
  return operations[operator](a, b);
};

const validateAnswers = () => {
  correctCount = 0;
  const inputs = document.querySelectorAll('.answer-input');

  inputs.forEach(input => {
    const numbers = input.parentElement.querySelectorAll('.number');
    const operator = input.parentElement.querySelector('.operator').textContent;
    const a = parseInt(numbers[0].textContent);
    const b = parseInt(numbers[1].textContent);

    const correct = calculateCorrectAnswer(operator, a, b);
    const userAnswer = parseInt(input.value);

    input.classList.toggle('correct', userAnswer === correct);
    input.classList.toggle('wrong', userAnswer !== correct);

    if (userAnswer === correct) correctCount++;
  });

  return { correctCount, total: inputs.length };
};

// ==================== 用户交互功能 ====================
const handleKeyNavigation = (e) => {
  if (!e.target.classList.contains('answer-input')) return;

  currentIndex = parseInt(e.target.dataset.index);
  const directionMap = {
    'ArrowRight': 1, 'ArrowDown': 1, 'Enter': 1,
    'ArrowLeft': -1, 'ArrowUp': -1
  };

  if (directionMap[e.key] !== undefined) {
    e.preventDefault();
    navigate(directionMap[e.key]);
  }
};

const navigate = (direction) => {
  currentIndex = (currentIndex + direction + inputsArray.length) % inputsArray.length;
  const target = inputsArray[currentIndex];

  target.focus();
  target.classList.add('current-focus');
  target.scrollIntoView({
    behavior: 'smooth',
    block: 'center',
    inline: 'center'
  });
};

// ==================== 网络请求功能 ====================
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

// ==================== 事件监听 ====================
checkBtn.addEventListener('click', () => {
  const { correctCount: count, total } = validateAnswers();
  clearInterval(timer);

  // 保存结果到服务器
  // 在checkBtn的事件处理中
  apiRequest('/math_train_save_result', 'POST', {
    math_level: 'basic', // 根据实际需要调整难度级别
    correct_count: count,
    total_questions: total,
    time_spent: time
  })

  alert(`正确率：${count}/${total}\n用时：${minutes.textContent}分${seconds.textContent}秒`);
});

newBtn.addEventListener('click', () => {
  generateQuestions();
  resetTimer();
  clearInterval(timer);
  startTimer();
});

document.addEventListener('keydown', handleKeyNavigation);

loginBtn.addEventListener('click', async () => {
  const username = document.getElementById('loginUsername').value;
  const password = document.getElementById('loginPassword').value;

  if (!username || !password) {
    return alert('请输入用户名和密码');
  }

  try {
    const result = await apiRequest('/math_train_login', 'POST', { username, password });
    if (result.success) {
      window.location.href = '/math_train'; // 重定向到训练页面
    } else {
      alert(result.message);
    }
  } catch {
    alert('登录失败，请稍后重试');
  }
});

registerBtn.addEventListener('click', async () => {
  const username = document.getElementById('registerUsername').value;
  const password = document.getElementById('registerPassword').value;

  if (!username || !password) {
    return alert('请输入用户名和密码');
  }

  try {
    const result = await apiRequest('/math_train_register', 'POST', { username, password });
    if (result.success) {
      alert('注册成功，请登录');
      // 切换到登录对话框
      document.getElementById('registerModal').style.display = 'none';
      document.getElementById('loginModal').style.display = 'flex';
    } else {
      alert(result.message);
    }
  } catch {
    alert('注册失败，请稍后重试');
  }
});

// 显示登录对话框
showLoginModalBtn.addEventListener('click', () => {
  loginModal.style.display = 'flex';
  registerModal.style.display = 'none';
});

// 显示注册对话框
showRegisterModalBtn.addEventListener('click', () => {
  registerModal.style.display = 'flex';
  loginModal.style.display = 'none';
});

// 切换到注册对话框
switchToRegister.addEventListener('click', () => {
  registerModal.style.display = 'flex';
  loginModal.style.display = 'none';
});

// 切换到登录对话框
switchToLogin.addEventListener('click', () => {
  loginModal.style.display = 'flex';
  registerModal.style.display = 'none';
});

// 关闭对话框（点击外部区域）
window.addEventListener('click', (event) => {
  if (event.target.classList.contains('modal')) {
    event.target.style.display = 'none';
  }
});

// 检查登录状态
const checkLoginStatus = async () => {
  try {
    const response = await fetch('/math_train_check_login');
    const data = await response.json();
    updateNavbar(data.loggedIn, data.username);
  } catch (error) {
    console.error('检查登录状态失败:', error);
  }
};

// 更新导航栏显示
const updateNavbar = (loggedIn, username) => {
  const loginBtn = document.getElementById('showLoginModalBtn');
  const registerBtn = document.getElementById('showRegisterModalBtn');
  const logoutBtn = document.getElementById('logoutBtn');
  const usernameSpan = document.getElementById('navbarUsername');

  if (loggedIn) {
    loginBtn.style.display = 'none';
    registerBtn.style.display = 'none';
    logoutBtn.style.display = 'inline-block';
    usernameSpan.textContent = username;
    usernameSpan.style.display = 'inline-block';
  } else {
    loginBtn.style.display = 'inline-block';
    registerBtn.style.display = 'inline-block';
    logoutBtn.style.display = 'none';
    usernameSpan.style.display = 'none';
  }
};

// 退出功能
document.getElementById('logoutBtn').addEventListener('click', () => {
  window.location.href = '/math_train_logout';
});

// 修改登录成功后的跳转
loginBtn.addEventListener('click', async () => {
  // ...保持原有逻辑...
  if (result.success) {
    window.location.href = '/math_train_user';  // 修改跳转地址
  }
});

// 在训练页面添加用户中心按钮


// 页面加载时检查登录状态
checkLoginStatus();

// ==================== 初始化 ====================
generateQuestions();
startTimer();