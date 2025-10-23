-- Tabela de Usuários
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    senha_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'vendedor')),
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ativo BOOLEAN DEFAULT 1
);

-- Tabela de Categorias
CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL,
    descricao TEXT
);

-- Tabela de Produtos
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_barras TEXT UNIQUE,
    nome TEXT NOT NULL,
    descricao TEXT,
    preco_compra DECIMAL(10, 2) NOT NULL,
    preco_venda DECIMAL(10, 2) NOT NULL,
    estoque INTEGER NOT NULL DEFAULT 0,
    estoque_minimo INTEGER DEFAULT 5,
    categoria_id INTEGER,
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ativo BOOLEAN DEFAULT 1,
    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
);

-- Tabela de Clientes
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT UNIQUE,
    telefone TEXT,
    cpf TEXT UNIQUE,
    endereco TEXT,
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ativo BOOLEAN DEFAULT 1
);

-- Tabela de Vendas
CREATE TABLE IF NOT EXISTS vendas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,
    cliente_id INTEGER,
    usuario_id INTEGER NOT NULL,
    data_venda TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    subtotal DECIMAL(10, 2) NOT NULL,
    desconto DECIMAL(10, 2) DEFAULT 0,
    total DECIMAL(10, 2) NOT NULL,
    forma_pagamento TEXT NOT NULL,
    status TEXT DEFAULT 'finalizada' CHECK(status IN ('pendente', 'finalizada', 'cancelada')),
    observacoes TEXT,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Tabela de Itens da Venda
CREATE TABLE IF NOT EXISTS itens_venda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venda_id INTEGER NOT NULL,
    produto_id INTEGER NOT NULL,
    quantidade INTEGER NOT NULL,
    preco_unitario DECIMAL(10, 2) NOT NULL,
    desconto DECIMAL(10, 2) DEFAULT 0,
    subtotal DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (venda_id) REFERENCES vendas(id) ON DELETE CASCADE,
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
);

-- Tabela de Configurações
CREATE TABLE IF NOT EXISTS configuracoes (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    tipo TEXT NOT NULL,
    descricao TEXT,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir Categorias Iniciais
INSERT OR IGNORE INTO categorias (nome, descricao) VALUES 
('Alimentos', 'Produtos alimentícios em geral'),
('Bebidas', 'Bebidas em geral'),
('Limpeza', 'Produtos de limpeza'),
('Higiene', 'Produtos de higiene pessoal'),
('Outros', 'Outros produtos');

-- Inserir Usuário Admin
-- Senha: admin123
INSERT OR IGNORE INTO usuarios (nome, email, senha_hash, role) VALUES 
('Administrador', 'admin@loja.com', '$2b$12$uKmy.z59mwHtkQ0QpxVp.OWqdEQTspgKLHcyYut/Ferp.tZNQSRmW', 'admin');

-- Inserir Usuário Vendedor
-- Senha: vendedor123
INSERT OR IGNORE INTO usuarios (nome, email, senha_hash, role) VALUES 
('Vendedor', 'vendedor@loja.com', '$2b$12$uKmy.z59mwHtkQ0QpxVp.OWqdEQTspgKLHcyYut/Ferp.tZNQSRmW', 'vendedor');

-- Inserir Produtos Iniciais
INSERT OR IGNORE INTO produtos (nome, descricao, preco_compra, preco_venda, estoque, categoria_id) VALUES
('Arroz 5kg', 'Arroz branco tipo 1', 15.00, 25.90, 100, 1),
('Feijão 1kg', 'Feijão carioca', 6.00, 9.90, 150, 1),
('Óleo 900ml', 'Óleo de soja', 4.50, 7.90, 200, 1),
('Sabão em Pó 1kg', 'Sabão em pó para roupas', 8.00, 14.90, 80, 3),
('Coca-Cola 2L', 'Refrigerante Coca-Cola', 6.00, 10.90, 120, 2);

-- Inserir Clientes Iniciais
INSERT OR IGNORE INTO clientes (nome, email, telefone, cpf, endereco) VALUES
('João Silva', 'joao@email.com', '(11) 99999-9999', '12345678901', 'Rua das Flores, 123 - Centro'),
('Maria Santos', 'maria@email.com', '(11) 98888-8888', '98765432109', 'Av. Brasil, 1000 - Vila Nova'),
('Carlos Oliveira', 'carlos@email.com', '(11) 97777-7777', '45678912345', 'Rua das Palmeiras, 50 - Jardim América');

-- Inserir Configurações Iniciais
INSERT OR IGNORE INTO configuracoes (chave, valor, tipo, descricao) VALUES
('empresa_nome', 'Minha Loja', 'text', 'Nome da empresa'),
('empresa_cnpj', '12.345.678/0001-90', 'text', 'CNPJ da empresa'),
('empresa_endereco', 'Rua Exemplo, 123 - Centro - Cidade/UF', 'text', 'Endereço da empresa'),
('empresa_telefone', '(00) 1234-5678', 'text', 'Telefone da empresa'),
('icms', '18.0', 'number', 'Alíquota de ICMS (%)'),
('iss', '5.0', 'number', 'Alíquota de ISS (%)'),
('mensagem_cupom', 'Obrigado pela preferência! Volte sempre!', 'textarea', 'Mensagem no rodapé do cupom'),
('tema', 'light', 'select', 'Tema do sistema (light/dark)');
