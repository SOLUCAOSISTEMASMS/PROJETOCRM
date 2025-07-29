CREATE TABLE leads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100),
    email VARCHAR(100),
    telefone VARCHAR(20),
    empresa VARCHAR(100),
    cargo VARCHAR(100),
    origem VARCHAR(50),
    status VARCHAR(20),
    interesses TEXT,
    observacoes TEXT,
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);