USE woniunote;

CREATE TABLE math_train_users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  email VARCHAR(255)  NOT NULL
);

CREATE TABLE math_train_results (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  math_level INT NOT NULL,
  correct_count INT NOT NULL,
  total_questions INT NOT NULL,
  time_spent INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES math_train_users(id)
);