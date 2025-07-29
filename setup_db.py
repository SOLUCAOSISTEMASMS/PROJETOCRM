import os
from models import db, Lead, Usuario, Cliente, Funcionario
from app import app

# Caminho do banco
db_path = os.path.join(os.path.dirname(__file__), 'empresa.db')

def inicializar_banco():
    if os.path.exists(db_path):
        print("🔁 Banco já existe: empresa.db")
    else:
        with app.app_context():
            db.create_all()
            print("✅ Tabelas criadas com sucesso!")
            inserir_dados_teste()
            print("🧪 Dados de teste inseridos!")

def inserir_dados_teste():
    # Exemplo: usuário de teste
    usuario = Usuario(nome='Admin', email='admin@example.com')
    usuario.set_senha('123456')
    db.session.add(usuario)

    # Exemplo: lead de teste
    lead = Lead(
        nome='João Teste',
        email='joao@teste.com',
        telefone='(67) 99999-0000',
        empresa='Empresa Fictícia',
        cargo='Analista',
        origem='Site',
        status='Novo',
        interesses='Website, CRM',
        observacoes='Lead gerado pelo setup inicial.'
    )
    db.session.add(lead)

    # Exemplo: cliente de teste
    cliente = Cliente(
        nome='Cliente Exemplo',
        email='cliente@empresa.com',
        telefone='(67) 3222-3344',
        empresa='Cliente S/A'
    )
    db.session.add(cliente)

    # Exemplo: funcionário de teste
    funcionario = Funcionario(
        nome='Funcionário Exemplo',
        cargo='Vendas',
        email='funcionario@empresa.com',
        telefone='(67) 3555-8899'
    )
    db.session.add(funcionario)

    db.session.commit()

if __name__ == '__main__':
    inicializar_banco()