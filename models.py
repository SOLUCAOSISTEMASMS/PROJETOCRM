from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
db = SQLAlchemy()
import uuid
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired, Email
from wtforms import SubmitField


class Empresa(db.Model):
    __tablename__ = 'empresas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    plano = db.Column(db.String(50), default='gratuito')
    criada_em = db.Column(db.DateTime, default=datetime.utcnow)
    cnpj = db.Column(db.String(20), nullable=True)
    telefone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    endereco = db.Column(db.String(200), nullable=True)
    cidade = db.Column(db.String(50), nullable=True)
    estado = db.Column(db.String(2), nullable=True)
    representante = db.Column(db.String(100), nullable=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False, default=lambda: str(uuid.uuid4())[:8])

    # Relacionamento com usuários vinculados a esta empresa
    usuarios = db.relationship('Usuario', back_populates='empresa')  # ✅ conexão bidirecional

from werkzeug.security import generate_password_hash, check_password_hash
class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario'  # 👈 se quiser explicitar

    codigo = db.Column(db.Integer, nullable=False)
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    nome_usuario = db.Column(db.String(50), unique=True)
    ativo = db.Column(db.Boolean, default=True)
    email = db.Column(db.String(120), nullable=True)
    senha_hash = db.Column(db.String(128), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='vendedor')

    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=True)
    empresa = db.relationship('Empresa', back_populates='usuarios')  # 🧠 nome explícito

    __table_args__ = (
        db.UniqueConstraint('codigo', 'empresa_id'),
    )

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)




class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False)
    acao = db.Column(db.String(100), nullable=False)
    detalhes = db.Column(db.Text, nullable=True)
    data = db.Column(db.DateTime, default=datetime.utcnow)


# Valores possíveis: 'admin', 'gerente', 'vendedor'

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)
    



class EmpresaPersonalizada(db.Model):
    __tablename__ = 'empresa_personalizada'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(20), nullable=True)
    telefone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    endereco = db.Column(db.String(200), nullable=True)
    cidade = db.Column(db.String(50), nullable=True)
    estado = db.Column(db.String(2), nullable=True)
    representante = db.Column(db.String(100), nullable=True)

    # Empresa pode ter vários usuários
from wtforms.validators import DataRequired, Length, Email

class EmpresaForm(FlaskForm):
    nome = StringField('Nome da empresa', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[Email(), Length(max=120)])
    telefone = StringField('Telefone', validators=[Length(max=50)])
    endereco = StringField('Endereço', validators=[Length(max=200)])
    cidade = StringField('Cidade', validators=[Length(max=50)])
    estado = StringField('Estado', validators=[Length(max=2)])
    representante = StringField('Representante', validators=[Length(max=100)])
    cnpj = StringField('CNPJ', validators=[Length(max=20)])
    submit = SubmitField('Cadastrar')



# 🔹 Modelo de Cliente



class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Novo campo para identificação interna
    codigo = db.Column(db.Integer, unique=True, nullable=False)  # Código visível, controlado manualmente
    status = db.Column(db.String(10), nullable=False, default="ativo")  # valores: 'ativo', 'inativo'
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    telefone = db.Column(db.String(50))
    empresa = db.Column(db.String(100), nullable=True)
    data_cadastro = db.Column(db.DateTime, server_default=db.func.now())
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    endereco_rua = db.Column(db.String(100))
    endereco_numero = db.Column(db.String(10))
    endereco_complemento = db.Column(db.String(50))
    bairro = db.Column(db.String(50))
    cidade = db.Column(db.String(50))
    estado = db.Column(db.String(2))      # Ex: 'SP', 'RJ'
    rmcep = db.Column(db.String(9))         # Formato: 00000-000
    cpf_cnpj = db.Column(db.String(18), unique=True, nullable=False)


class Contato(db.Model):
    codigo = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, nullable=False)
    assunto = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.codigo'))
    cliente = db.relationship('Cliente', backref='contatos')  

    
from wtforms import SelectField

class ClienteForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    email = StringField('Email', validators=[Email()])
    telefone = StringField('Telefone')
    empresa = StringField('Empresa')
    endereco_rua = StringField('Rua')
    endereco_numero = StringField('Número')
    endereco_complemento = StringField('Complemento')
    bairro = StringField('Bairro')
    cidade = StringField('Cidade')
    estado = StringField('Estado')
    rmcep = StringField('CEP')
    cpf_cnpj = StringField('CPF/CNPJ', validators=[DataRequired()])

    status = SelectField(
        'Status',
        choices=[('ativo', 'Ativo'), ('inativo', 'Inativo')],
        default='ativo',
        validators=[DataRequired()]
    )


    



# 🔹 Modelo de Lead
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

class LogAcao(db.Model):
    __tablename__ = 'log_acao'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    acao = db.Column(db.String(100), nullable=False)
    detalhes = db.Column(db.Text, nullable=True)
    ip = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    data_hora = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship('Usuario', backref='logs')




class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    email = db.Column(db.String(100))
    telefone = db.Column(db.String(20))
    empresa = db.Column(db.String(100))
    cargo = db.Column(db.String(100))
    origem = db.Column(db.String(50))
    status = db.Column(db.String(20))
    interesses = db.Column(db.Text)
    observacoes = db.Column(db.Text)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    data_retorno = db.Column(db.Date)  # 👈 novo campo
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.codigo'))
    cliente = db.relationship('Cliente')
    criado_por_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    criado_por = db.relationship('Usuario', backref='leads_lancados')
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    
    



# 🔹 Modelo de Usuário (login)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin





