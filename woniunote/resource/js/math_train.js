// 获取导航栏元素
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const loginBtn = document.getElementById('loginBtn');
const registerBtn = document.getElementById('registerBtn');

const grid = document.getElementById('grid');
const checkBtn = document.getElementById('checkBtn');
const newBtn = document.getElementById('newBtn');
const minutes = document.getElementById('minutes');
const seconds = document.getElementById('seconds');
let inputsArray = [];
let currentIndex = 0;
let timer = null;
let time = 0;

// 初始化输入框数组
function initInputsArray() {
  inputsArray = Array.from(document.querySelectorAll('.answer-input'));
  inputsArray.forEach((input, index) => input.dataset.index = index);
}

// 键盘导航
function handleKeyNavigation(e) {
  if (document.activeElement.classList.contains('answer-input')) {
    currentIndex = parseInt(document.activeElement.dataset.index);

    switch (e.key) {
      case 'ArrowRight':
      case 'ArrowDown':
      case 'Enter':
        e.preventDefault();
        navigate(1);
        break;
      case 'ArrowLeft':
      case 'ArrowUp':
        e.preventDefault();
        navigate(-1);
        break;
    }
  }
}

// 导航逻辑
function navigate(direction) {
  currentIndex += direction;
  if (currentIndex >= inputsArray.length) currentIndex = 0;
  if (currentIndex < 0) currentIndex = inputsArray.length - 1;
  const target = inputsArray[currentIndex];
  target.focus();
  target.classList.add('current-focus');
  target.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// 生成题目
function generateQuestions() {
  grid.innerHTML = '';
  for (let i = 0; i < 5; i++) {
    for (let j = 0; j < 4; j++) {
      let num1 = Math.floor(Math.random() * 20) + 1;
      let num2 = Math.floor(Math.random() * 20) + 1;
      const operator = Math.random();
      let operatorSymbol;
      let correctAnswer;

      if (operator < 0.25) {
        operatorSymbol = '+';
        correctAnswer = num1 + num2;
      } else if (operator < 0.5) {
        operatorSymbol = '-';
        correctAnswer = num1 - num2;
      } else if (operator < 0.75) {
        operatorSymbol = '×';
        correctAnswer = num1 * num2;
      } else {
        operatorSymbol = '÷';
        // 确保除数不为0
        while (num2 === 0) {
          num2 = Math.floor(Math.random() * 20) + 1; // 如果除数为0，重新生成
        }
        const dividend = num1 * num2; // 生成被除数
        correctAnswer = dividend / num2; // 结果为整数
        num1 = dividend; // 更新 num1 为被除数
      }

      const question = document.createElement('div');
      question.className = 'question-item';

      question.innerHTML = `
        <span class="number">${num1}</span>
        <span class="operator">${operatorSymbol}</span>
        <span class="number">${num2}</span>
        <span class="operator">=</span>
      `;

      const input = document.createElement('input');
      input.className = 'answer-input';
      input.type = 'number';
      input.placeholder = '?';
      question.appendChild(input);
      grid.appendChild(question);
    }
  }
  initInputsArray(); // 更新输入框数组
}

// 更新计时器
function updateTimer() {
  time++;
  minutes.textContent = String(Math.floor(time / 60)).padStart(2, '0');
  seconds.textContent = String(time % 60).padStart(2, '0');
}

// 检查答案
checkBtn.addEventListener('click', () => {
  let correctCount = 0;
  const inputs = document.querySelectorAll('.answer-input');
  inputs.forEach(input => {
    const numbers = input.parentElement.querySelectorAll('.number');
    const operator = input.parentElement.querySelector('.operator').textContent;
    const a = parseInt(numbers[0].textContent);
    const b = parseInt(numbers[1].textContent);
    let correct;

    if (operator === '+') correct = a + b;
    else if (operator === '-') correct = a - b;
    else if (operator === '×') correct = a * b;
    else if (operator === '÷') correct = a / b;

    if (parseInt(input.value) === correct) {
      correctCount++;
      input.classList.add('correct');
      input.classList.remove('wrong');
    } else {
      input.classList.add('wrong');
      input.classList.remove('correct');
    }
  });
  clearInterval(timer);
  alert(`正确率：${correctCount}/${inputs.length}\n用时：${minutes.textContent}分${seconds.textContent}秒`);
});

// 生成新题
newBtn.addEventListener('click', () => {
  generateQuestions();
  time = 0;
  clearInterval(timer);
  timer = setInterval(updateTimer, 1000);
  document.querySelectorAll('.answer-input').forEach(input => {
    input.value = '';
    input.classList.remove('correct', 'wrong');
  });
});

// 添加键盘导航
document.addEventListener('keydown', handleKeyNavigation);
fetch('/save_result', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    correct_count: correctCount,
    total_questions: inputs.length,
    time_spent: time
  })
});

// 初始化
generateQuestions();
timer = setInterval(updateTimer, 1000);

// 登录功能
loginBtn.addEventListener('click', async () => {
  const username = usernameInput.value;
  const password = passwordInput.value;

  if (!username || !password) {
    alert('请输入用户名和密码');
    return;
  }

  try {
    const response = await fetch('/math_train_login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    const result = await response.json();
    if (result.success) {
      alert('登录成功');
      window.location.href = '/math_train';
    } else {
      alert(result.message || '登录失败');
    }
  } catch (error) {
    console.error('登录失败:', error);
    alert('登录失败，请稍后重试');
  }
});

// 注册功能
registerBtn.addEventListener('click', async () => {
  const username = usernameInput.value;
  const password = passwordInput.value;

  if (!username || !password) {
    alert('请输入用户名和密码');
    return;
  }

  try {
    const response = await fetch('/math_train_register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    const result = await response.json();
    if (result.success) {
      alert('注册成功');
      window.location.href = '/math_train_login';
    } else {
      alert(result.message || '注册失败');
    }
  } catch (error) {
    console.error('注册失败:', error);
    alert('注册失败，请稍后重试');
  }
});