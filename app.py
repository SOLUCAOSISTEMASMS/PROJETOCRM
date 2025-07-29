from flask import Flask, render_template, request, redirect, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Lead, Usuario, Cliente
import config
from functools import wraps
from flask import abort
from flask_login import current_user
from datetime import datetime
from models import Cliente, Contato, Lead, Usuario
from flask import url_for
from collections import Counter
from flask_login import login_required
from collections import Counter
from sqlalchemy.orm import joinedload
from models import db, Empresa  # importa o modelo
from models import ClienteForm
import uuid
from sqlalchemy.exc import IntegrityError
import re
from wtforms import StringField, SubmitField, EmailField, TelField
from slugify import slugify
from werkzeug.security import generate_password_hash
from flask import session
from datetime import date
from sqlalchemy.orm import joinedload
from datetime import datetime, UTC
from models import Log
from models import LogAcao
from flask import request
import copy
from flask import Blueprint, render_template, request
from models import Lead  # Supondo que você tenha um modelo Lead definido
from sqlalchemy import and_
from flask_sqlalchemy import SQLAlchemy







def registrar_log(usuario_id, acao, detalhes=None):
    log = LogAcao(
        usuario_id=usuario_id,
        acao=acao,
        detalhes=detalhes,
        ip=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(log)
    db.session.commit()

def gerar_codigo_usuario(empresa_id):
    ultimo = Usuario.query.filter_by(empresa_id=empresa_id).order_by(Usuario.codigo.desc()).first()
    return 1 if not ultimo or ultimo.codigo is None else ultimo.codigo + 1





app = Flask(__name__)
app.config.from_object(config)  # carrega config.py
db.init_app(app)

with app.app_context():
    db.create_all()









def permissoes_requeridas(*tipos_permitidos):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if current_user.tipo not in tipos_permitidos:
                abort(403)  # acesso proibido
            return f(*args, **kwargs)
        return wrapper
    return decorator
from flask_login import LoginManager

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

@app.context_processor
def inject_empresa():
    if current_user.is_authenticated:
        return {'empresa': current_user.empresa}
    return {'empresa': None}

# Rota principal: listagem de leads
@app.route('/')
@login_required
def home():
    busca = request.args.get('busca', '')
    status = request.args.get('status', '')
    hoje = date.today()

    # 🔄 Base da query
    if current_user.tipo == 'admin':
        query = Lead.query.options(joinedload(Lead.cliente))
    else:
        query = Lead.query.options(joinedload(Lead.cliente)).filter(
            Lead.criado_por_id == current_user.id
        )

    # 🔍 Filtro de busca (nome, origem ou status)
    if busca:
        query = query.join(Cliente).filter(
            (Cliente.nome.ilike(f'%{busca}%')) |
            (Lead.origem.ilike(f'%{busca}%')) |
            (Lead.status.ilike(f'%{busca}%'))
        )

    # 📌 Filtro por status
    if status:
        query = query.filter(Lead.status == status)

    leads = query.all()

    # ✅ Flash se veio de uma atualização bem-sucedida
    if 'lead_atualizado' in request.args:
        flash('lead_atualizado', 'success')

    # 📊 Contagem por origem para gráfico
    contagem_origem = Counter(
        lead.origem.strip().title()
        for lead in leads
        if lead.origem and isinstance(lead.origem, str)
    )

    origens = list(contagem_origem.keys())
    totais = list(contagem_origem.values())

    return render_template(
        'listar.html',
        leads=leads,
        status=status,
        origens=origens,
        totais=totais,
        current_date=hoje
    )


@app.route('/minha_empresa', methods=['GET', 'POST'])
@login_required
def minha_empresa():
    # 🔎 Recupera a empresa vinculada diretamente ou via CNPJ (admin global)
    empresa = current_user.empresa

    if current_user.tipo == 'admin' and current_user.empresa_id is None:
        empresa_id = session.get('empresa_id')
        if empresa_id:
            empresa = Empresa.query.get(empresa_id)

    if not empresa:
        flash('Empresa não encontrada ou não definida.', 'danger')
        return redirect('/login')

    # 📝 Atualização de dados da empresa (somente admin global pode)
    if request.method == 'POST':
        if current_user.tipo != 'admin':
            abort(403)

        nome = request.form.get('nome')
        if not nome or nome.strip() == "":
            flash("⚠️ O campo Nome da Empresa é obrigatório!", "warning")
            return redirect(url_for('minha_empresa'))

        # ⏎ Atualiza os campos da empresa
        empresa.nome = nome
        empresa.cnpj = request.form.get('cnpj')
        empresa.telefone = request.form.get('telefone')
        empresa.email = request.form.get('email')
        empresa.endereco = request.form.get('endereco')
        empresa.cidade = request.form.get('cidade')
        empresa.estado = request.form.get('estado')
        empresa.representante = request.form.get('representante')

        db.session.commit()
        flash('✅ Dados da empresa atualizados com sucesso!', 'success')
        return redirect(url_for('listar'))

    # 🎯 Renderiza a página com os dados da empresa
    return render_template('minha_empresa.html', empresa=empresa)


@app.route('/cadastro')
@login_required
def cadastro():
    return render_template('cadastro.html')


# Rota: salvar novo lead
@app.route('/salvar', methods=['POST'])
def salvar():
    nome = request.form.get('nome', '').strip()
    telefone = request.form.get('telefone', '').strip()

    # 👉 Verifica se campos obrigatórios estão preenchidos
    if not nome or not telefone:
        flash('Nome e telefone são obrigatórios para salvar o lead.')
        return redirect('/cadastro')

    # 🧱 Continua o preenchimento dos demais campos
    email = request.form.get('email', '').strip()
    empresa = request.form.get('empresa', '').strip()
    cargo = request.form.get('cargo', '').strip()
    origem = request.form.get('origem', '').strip()
    status = request.form.get('status', '').strip()
    interesses = request.form.get('interesses', '').strip()
    observacoes = request.form.get('observacoes', '').strip()

    lead = Lead(
        nome=nome,
        telefone=telefone,
        email=email,
        empresa=empresa,
        cargo=cargo,
        origem=origem,
        status=status,
        interesses=interesses,
        observacoes=observacoes
    )

    db.session.add(lead)
    db.session.commit()
    flash('Lead salvo com sucesso!')
    return redirect('/')

# Rota: carregar dados para editar
from flask import abort
#editar lead
from datetime import datetime
import copy  # caso queira usar deepcopy futuramente

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_lead(id):
    lead = Lead.query.get_or_404(id)

    # 🔒 Permissão de edição
    if lead.criado_por_id != current_user.id and current_user.tipo != 'admin':
        flash("⚠️ Você não tem permissão para editar este lead.", "warning")
        return redirect(url_for('listar'))

    clientes = Cliente.query.order_by(Cliente.nome).all()
    clientes_dict = {
        cliente.codigo: {
            'email': cliente.email,
            'telefone': cliente.telefone,
            'empresa': cliente.empresa
        } for cliente in clientes
    }

    if request.method == 'POST':
        valores_antigos = {
            'cliente_id': lead.cliente_id,
            'status': lead.status,
            'cargo': lead.cargo,
            'origem': lead.origem,
            'interesses': lead.interesses,
            'observacoes': lead.observacoes,
            'data_retorno': lead.data_retorno
        }

        # ✏️ Atualiza os campos
        lead.cliente_id = int(request.form.get('cliente_id'))
        lead.status = request.form.get('status')
        lead.cargo = request.form.get('cargo')
        lead.origem = request.form.get('origem')
        lead.interesses = request.form.get('interesses')
        lead.observacoes = request.form.get('observacoes')
        data_retorno_str = request.form.get('data_retorno')
        lead.data_retorno = datetime.strptime(data_retorno_str, "%Y-%m-%d").date() if data_retorno_str else None

        try:
            db.session.commit()

            alteracoes = []
            for campo, valor_antigo in valores_antigos.items():
                valor_novo = getattr(lead, campo)
                if valor_novo != valor_antigo:
                    alteracoes.append(f"{campo}: '{valor_antigo}' → '{valor_novo}'")

            detalhes_log = " | ".join(alteracoes) if alteracoes else "Nenhuma alteração detectada"
            cliente_nome = lead.cliente.nome if lead.cliente else "Cliente não identificado"

            registrar_log(
                usuario_id=current_user.id,
                acao="Editou lead",
                detalhes=f"Lead ID: {lead.id}; Cliente: {cliente_nome} | {detalhes_log}"
            )

            flash('✅ Lead atualizado com sucesso!', 'success')
            return redirect(url_for('listar'))

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erro ao editar lead: {e}")
            flash("❌ Erro interno ao atualizar lead.", "erro")
            return render_template('editar_lead.html', lead=lead, clientes=clientes, clientes_json=clientes_dict)

    return render_template('editar_lead.html', lead=lead, clientes=clientes, clientes_json=clientes_dict)

# Rota: atualizar dados do lead
@app.route('/atualizar/<int:id>', methods=['POST'])
@login_required
def atualizar(id):
    lead = Lead.query.get_or_404(id)

    valores_antigos = {
        'cliente_id': lead.cliente_id,
        'cargo': lead.cargo,
        'origem': lead.origem,
        'status': lead.status,
        'interesses': lead.interesses,
        'observacoes': lead.observacoes,
        'data_retorno': lead.data_retorno
    }

    # ✏️ Atualiza os campos
    lead.cliente_id = int(request.form.get('cliente_id'))
    lead.cargo = request.form.get('cargo')
    lead.origem = request.form.get('origem')
    lead.status = request.form.get('status')
    lead.interesses = request.form.get('interesses')
    lead.observacoes = request.form.get('observacoes')
    data_str = request.form.get('data_retorno')
    lead.data_retorno = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else None

    try:
        db.session.commit()

        alteracoes = []
        for campo, valor_antigo in valores_antigos.items():
            valor_novo = getattr(lead, campo)
            if valor_novo != valor_antigo:
                alteracoes.append(f"{campo}: '{valor_antigo}' → '{valor_novo}'")

        detalhes_log = " | ".join(alteracoes) if alteracoes else "Nenhuma alteração detectada"
        cliente_nome = lead.cliente.nome if lead.cliente else "Cliente não identificado"

        registrar_log(
            usuario_id=current_user.id,
            acao="Atualizou lead",
            detalhes=f"Lead ID: {lead.id}; Cliente: {cliente_nome} | {detalhes_log}"
        )

        flash('✅ Lead atualizado com sucesso!', 'success')
        return redirect(url_for('listar'))

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Erro ao atualizar lead: {e}")
        flash("❌ Erro interno ao atualizar lead.", "erro")
        return redirect(url_for('listar'))



# Rota: excluir lead
@app.route('/excluir_lead/<int:lead_id>', methods=['POST'])
@login_required
def excluir_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)

    try:
        # 📝 Captura dados antes da exclusão
        cliente_nome = lead.cliente.nome if lead.cliente else "Cliente não identificado"
        detalhes = (
            f"Lead ID: {lead.id}; Cliente: {cliente_nome}; Cargo: {lead.cargo}; "
            f"Status: {lead.status}; Origem: {lead.origem}; Interesses: {lead.interesses}; "
            f"Data de Retorno: {lead.data_retorno}"
        )

        # 📋 Registra o log da exclusão antes de apagar
        registrar_log(
            usuario_id=current_user.id,
            acao="Excluiu lead",
            detalhes=detalhes
        )

        # 🔥 Remove o lead
        db.session.delete(lead)
        db.session.commit()

        flash("✅ Lead excluído com sucesso!", "success")
        return redirect(url_for('listar'))

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Erro ao excluir lead: {e}")
        flash("❌ Erro interno ao excluir lead.", "erro")
        return redirect(url_for('listar'))

from flask import flash
from flask_login import UserMixin
from flask import Blueprint, render_template, request
from models import Lead  # Certifique-se que o modelo Lead está bem definido
from sqlalchemy import and_
from datetime import datetime
from flask import Flask




# Blueprint registrado com nome 'relatorio'
relatorios_bp = Blueprint('relatorio', __name__)





@relatorios_bp.route('/relatorio_leads', methods=['GET'])
def relatorio_leads():
    # Obtém parâmetros da URL
    origem = request.args.get('origem')
    status = request.args.get('status')
    inicio = request.args.get('inicio')
    fim = request.args.get('fim')

    # Filtros dinâmicos
    filtros = []

    if origem:
        filtros.append(Lead.origem == origem)
    if status:
        filtros.append(Lead.status == status)
    if inicio:
        try:
            data_inicio = datetime.strptime(inicio, "%Y-%m-%d")
            filtros.append(Lead.data_cadastro >= data_inicio)
        except ValueError:
            pass  # Evita erro se data estiver em formato inválido
    if fim:
        try:
            data_fim = datetime.strptime(fim, "%Y-%m-%d")
            filtros.append(Lead.data_cadastro <= data_fim)
        except ValueError:
            pass

    # Consulta
    leads = Lead.query.filter(and_(*filtros)).order_by(Lead.data_cadastro.desc()).all()

    return render_template('relatorio_leads.html', leads=leads)



#logar no sistema
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome_usuario = request.form['nome_usuario']
        senha = request.form['senha']
        cnpj = request.form['cnpj'].replace('.', '').replace('/', '').replace('-', '')

        # 📌 Validação básica do CNPJ
        if not re.match(r'^\d{14}$', cnpj):
            flash('CNPJ inválido.')
            return redirect('/login')

        # 🔍 Busca o usuário
        usuario = Usuario.query.filter_by(nome_usuario=nome_usuario).first()
        if not usuario:
            flash('Usuário não encontrado.')
            return redirect('/login')

        # ❌ Verifica se está ativo
        if not usuario.ativo:
            flash('Este usuário está inativo.')
            return redirect('/login')

        # 🔍 Busca a empresa pelo CNPJ
        empresa = Empresa.query.filter_by(cnpj=cnpj).first()
        if not empresa:
            flash('Empresa com esse CNPJ não encontrada.')
            return redirect('/login')

        # 🔐 Verifica permissão de acesso à empresa
        acesso_liberado = False
        if usuario.tipo == 'admin' and usuario.empresa_id is None:
            acesso_liberado = True  # 🔓 Admin global
        elif usuario.empresa == empresa:
            acesso_liberado = True  # ✅ Vínculo direto à empresa

        if not acesso_liberado:
            flash('Este usuário não tem acesso à empresa informada.')
            return redirect('/login')

        # 🔑 Verifica a senha
        if usuario.verificar_senha(senha):
            login_user(usuario)

            # ✅ Armazena empresa ativa na sessão
            session['empresa_id'] = empresa.id
            session['empresa_nome'] = empresa.nome  # opcional

            # 📆 Verifica se há leads com retorno hoje
            hoje = date.today()
            leads_hoje = Lead.query.filter_by(empresa_id=empresa.id, data_retorno=hoje).all()
            if leads_hoje:
                flash('retorno_hoje', 'warning')

            return redirect('/listar')
        else:
            flash('Usuário ou senha inválidos.')
            return redirect('/login')

    # 👀 Exibe o formulário de login
    return render_template('login.html')



@app.route('/listar_funcionarios')
@login_required
def listar_funcionarios():
    termo = request.args.get('filtro')

    if termo:
        funcionarios = Usuario.query.filter(
            (Usuario.nome.ilike(f"%{termo}%")) | 
            (Usuario.email.ilike(f"%{termo}%")),
            Usuario.tipo.in_(['funcionario', 'vendedor', 'admin', 'gerente'])
        ).order_by(Usuario.id.desc()).all()
    else:
        funcionarios = Usuario.query.filter(
            Usuario.tipo.in_(['funcionario', 'vendedor', 'admin', 'gerente'])
        ).order_by(Usuario.id.desc()).all()

    return render_template('listar_funcionarios.html', funcionarios=funcionarios)

@app.route('/logout')

def logout():
    logout_user()
    return redirect('/entrada')
@app.route('/entrada')
def entrada():
    return render_template('entrada.html')
from flask_login import current_user, login_required

@app.route('/inicio')
def inicio():
    if current_user.is_authenticated:
        return redirect('/')  # vai para painel principal (lista de leads)
    else:
        return redirect('/entrada')  # volta para página pública
    
    
from datetime import datetime

@app.route('/criar_lead', methods=['GET', 'POST'])
@login_required
def criar_lead():
    cliente_selecionado = None
    cliente_id = request.args.get('cliente_id')

    if cliente_id:
        try:
            cliente_id_int = int(cliente_id)
            cliente_selecionado = Cliente.query.get(cliente_id_int)
            if not cliente_selecionado:
                flash('❌ Cliente não encontrado na criação de lead.', 'danger')
        except ValueError:
            flash('❌ Parâmetro de cliente inválido.', 'danger')

    # Buscar todos os clientes para preencher o select
    clientes = Cliente.query.order_by(Cliente.nome).all()

    # Dicionário para preencher os campos via JS
    clientes_dict = {
        cliente.codigo: {
            'email': cliente.email,
            'telefone': cliente.telefone,
            'empresa': cliente.empresa
        } for cliente in clientes
    }

    if request.method == 'POST':
        db.session.rollback()

        try:
            nome = request.form.get('nome')
            email = request.form.get('email')
            telefone = request.form.get('telefone')
            cliente_id = int(request.form.get('cliente_id'))
            status = request.form.get('status')
            cargo = request.form.get('cargo')
            origem = request.form.get('origem')
            interesses = request.form.get('interesses')
            observacoes = request.form.get('observacoes')
            data_retorno_str = request.form.get('data_retorno')
            data_retorno = datetime.strptime(data_retorno_str, '%Y-%m-%d').date() if data_retorno_str else None
            empresa_id = session.get('empresa_id')

            if not empresa_id:
                flash('⚠️ Sessão inválida: nenhuma empresa ativa.', 'danger')
                return redirect(url_for('login'))

            novo_lead = Lead(
                nome=nome,
                email=email,
                telefone=telefone,
                cliente_id=cliente_id,
                cargo=cargo,
                origem=origem,
                status=status,
                interesses=interesses,
                observacoes=observacoes,
                data_retorno=data_retorno,
                criado_por_id=current_user.id,
                empresa_id=empresa_id
            )

            db.session.add(novo_lead)
            db.session.commit()

            cliente = Cliente.query.get(cliente_id)
            nome_cliente = cliente.nome if cliente else "Cliente não encontrado"

            registrar_log(
                usuario_id=current_user.id,
                acao="Criou lead",
                detalhes=f"Lead ID: {novo_lead.id}, Cliente: {nome_cliente}, Status: {status}, Origem: {origem}"
            )

            flash('✅ Lead criado com sucesso!', 'success')
            return redirect(url_for('listar'))

        except Exception as e:
            db.session.rollback()
            flash(f'❌ Ocorreu um erro ao criar o lead: {str(e)}', 'danger')

    return render_template(
        'criar_lead.html',
        clientes=clientes,
        clientes_dict=clientes_dict,
        cliente_selecionado=cliente_selecionado
    )

    




 #listar leads  
@app.route('/listar')
@login_required
def listar():
    busca = request.args.get('busca', '')
    status = request.args.get('status', '')
    hoje = date.today()

    # 🔄 Base da query
    if current_user.tipo == 'admin':
        query = Lead.query.options(joinedload(Lead.cliente))
    else:
        query = Lead.query.options(joinedload(Lead.cliente)).filter(
            Lead.criado_por_id == current_user.id
        )

    # 🔍 Filtro de busca (nome, origem ou status)
    if busca:
        query = query.join(Cliente).filter(
            (Cliente.nome.ilike(f'%{busca}%')) |
            (Lead.origem.ilike(f'%{busca}%')) |
            (Lead.status.ilike(f'%{busca}%'))
        )

    # 📌 Filtro por status
    if status:
        query = query.filter(Lead.status == status)

    leads = query.all()

    # ✅ Flash se veio de uma atualização bem-sucedida
    if 'lead_atualizado' in request.args:
        flash('lead_atualizado', 'success')

    # 📊 Contagem por origem para gráfico
    contagem_origem = Counter(
        lead.origem.strip().title()
        for lead in leads
        if lead.origem and isinstance(lead.origem, str)
    )

    origens = list(contagem_origem.keys())
    totais = list(contagem_origem.values())

    return render_template(
        'listar.html',
        leads=leads,
        status=status,
        origens=origens,
        totais=totais,
        current_date=hoje
    )





    

@app.route('/salvar_cliente', methods=['POST'])
@login_required
@permissoes_requeridas('admin', 'gerente')
def salvar_cliente():
    cliente = Cliente(
        nome=request.form['nome'],
        email=request.form['email'],
        telefone=request.form['telefone'],
        empresa=request.form['empresa']
    )
    db.session.add(cliente)
    db.session.commit()
    flash('Cliente cadastrado com sucesso!' 'success')
    return redirect('/listar_clientes')
def gerar_codigo_cliente():
    ultimo = Cliente.query.order_by(Cliente.id.desc()).first()
    sequencia = (ultimo.id + 1) if ultimo else 1
    return str(sequencia).zfill(6)



def validar_cpf_cnpj(valor):
    valor = re.sub(r'\D', '', valor)
    if len(valor) == 11:
        return validar_cpf(valor)
    elif len(valor) == 14:
        return validar_cnpj(valor)
    return False
def validar_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    soma1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = (soma1 * 10 % 11) % 10
    soma2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = (soma2 * 10 % 11) % 10
    return cpf[-2:] == f"{digito1}{digito2}"
def validar_cnpj(cnpj):
    cnpj = ''.join(filter(str.isdigit, cnpj))
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma1 = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    digito1 = 11 - (soma1 % 11)
    digito1 = digito1 if digito1 < 10 else 0

    pesos2 = [6] + pesos1
    soma2 = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    digito2 = 11 - (soma2 % 11)
    digito2 = digito2 if digito2 < 10 else 0

    return cnpj[-2:] == f"{digito1}{digito2}"

@app.route('/criar_cliente', methods=['GET', 'POST'])
@login_required
def criar_cliente():
    form = ClienteForm()

    if request.method == 'POST' and form.validate_on_submit():
        cpf_cnpj = form.cpf_cnpj.data.strip()
        print(f"CPF/CNPJ recebido: '{cpf_cnpj}'")

        # ✅ Validação de CPF/CNPJ
        if not validar_cpf_cnpj(cpf_cnpj):
            flash("CPF ou CNPJ inválido.", "erro")
            return render_template("criar_cliente.html", form=form)

        # ✅ Verifica duplicidade
        if Cliente.query.filter_by(cpf_cnpj=cpf_cnpj).first():
            flash("CPF/CNPJ já cadastrado.", "erro")
            return render_template("criar_cliente.html", form=form)

        # 🔢 Gerar código sequencial único
        try:
            ultimo_cliente = Cliente.query.order_by(Cliente.codigo.desc()).first()
            ultimo_numero = ultimo_cliente.codigo if ultimo_cliente else 0
            numero = ultimo_numero + 1

            while Cliente.query.filter_by(codigo=numero).first():
                numero += 1


            codigo_valor = numero
        except Exception as e:
            app.logger.error(f"Erro ao gerar código do cliente: {e}")
            codigo_valor = datetime.utcnow().strftime("%H%M%S")

        # 🧾 Criar novo cliente
        cliente = Cliente(
            codigo=codigo_valor,
            
            nome=form.nome.data,
            email=form.email.data,
            telefone=form.telefone.data,
            empresa=form.empresa.data,
            cpf_cnpj=cpf_cnpj,
            endereco_rua=form.endereco_rua.data,
            endereco_numero=form.endereco_numero.data,
            endereco_complemento=form.endereco_complemento.data,
            bairro=form.bairro.data,
            cidade=form.cidade.data,
            estado=form.estado.data,
            rmcep=form.rmcep.data,
            status=form.status.data,
            data_criacao=datetime.utcnow()
        )

        try:
            db.session.add(cliente)
            db.session.commit()

            # 📝 Log de criação de cliente
            registrar_log(
                usuario_id=current_user.id,
                acao="Criou cliente",
                detalhes=f"Código: {cliente.codigo}, Nome: {cliente.nome}, CPF/CNPJ: {cliente.cpf_cnpj}"
            )

            flash("Registro salvo com sucesso!", "success")
            return redirect(url_for("listar_clientes"))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erro ao salvar cliente: {e}")
            flash("Erro interno ao salvar cliente.", "erro")
            return render_template("criar_cliente.html", form=form)

    return render_template("criar_cliente.html", form=form)









from flask import flash

@app.route("/novo_contato/<int:cliente_codigo>", methods=["GET", "POST"])
@login_required
def novo_contato(cliente_codigo):
    cliente = Cliente.query.get_or_404(cliente_codigo)

    if request.method == "POST":
        try:
            data = datetime.strptime(request.form["data"], "%Y-%m-%dT%H:%M")
            assunto = request.form["assunto"]
            descricao = request.form["descricao"]

            novo = Contato(data=data, assunto=assunto, descricao=descricao, cliente=cliente)
            db.session.add(novo)
            db.session.commit()

            # 📝 Log de criação de contato
            registrar_log(
                usuario_id=current_user.id,
                acao="Criou contato",
                detalhes=f"Cliente Código: {cliente.codigo}, Assunto: {assunto}, Data: {data.strftime('%Y-%m-%d %H:%M')}"
            )

            flash('contato_salvo', 'success')
            return redirect(url_for("detalhes_cliente", cliente_id=cliente.codigo))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erro ao salvar contato: {e}")
            flash("Erro ao salvar contato.", "erro")
            return redirect(url_for("detalhes_cliente", cliente_id=cliente.codigo))

    return render_template("novo_contato.html", cliente=cliente)

@app.route("/relatorio_clientes")
@login_required
def relatorio_clientes():
    inicio = request.args.get("inicio")
    fim = request.args.get("fim")
    status = request.args.get("status")

    filtros = []
    if status:
        filtros.append(Cliente.status == status)
    if inicio:
        try:
            dt_inicio = datetime.strptime(inicio, "%Y-%m-%d")
            filtros.append(Cliente.data_cadastro >= dt_inicio)
        except ValueError:
            pass
    if fim:
        try:
            dt_fim = datetime.strptime(fim, "%Y-%m-%d")
            filtros.append(Cliente.data_cadastro <= dt_fim)
        except ValueError:
            pass

    clientes = Cliente.query.filter(and_(*filtros)).all()
    return render_template("relatorio_clientes.html", clientes=clientes)






@app.route('/detalhes_lead/<int:lead_id>')
@login_required
def detalhes_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    return render_template('detalhes_lead.html', lead=lead)

@app.route('/ver_contato/<int:contato_id>')
def ver_contato(contato_id):
    contato = Contato.query.get_or_404(contato_id)
    return render_template('ver_contato.html', contato=contato)

from sqlalchemy.exc import IntegrityError

from sqlalchemy.exc import IntegrityError

from sqlalchemy.exc import IntegrityError

@app.route('/criar_usuario', methods=['GET', 'POST'])
@login_required
@permissoes_requeridas('admin')
def criar_usuario():
    if request.method == 'POST':
        nome = request.form.get('nome')
        nome_usuario = request.form.get('nome_usuario')
        email = request.form.get('email')
        senha = request.form.get('senha')
        tipo = request.form.get('tipo')

        empresa_id = current_user.empresa_id

        # Validações de unicidade
        if Usuario.query.filter_by(nome=nome).first():
            alerta = 'nome'
        elif Usuario.query.filter_by(nome_usuario=nome_usuario).first():
            alerta = 'nome_usuario'
        elif Usuario.query.filter_by(email=email).first():
            alerta = 'email'
        else:
            alerta = None

        if alerta:
            return render_template('criar_usuario.html',
                                   alerta=alerta,
                                   nome=nome,
                                   nome_usuario=nome_usuario,
                                   email=email,
                                   tipo=tipo)

        tipo = request.form.get('tipo') or 'vendedor'

        # 🔐 Lógica de código sequencial
        admin_existente = Usuario.query.filter_by(empresa_id=empresa_id, tipo='admin').first()

        if tipo == 'admin' and not admin_existente:
            codigo = 1  # 👑 Reservado para admin global
        else:
            ultimo = Usuario.query.filter(Usuario.codigo != 1).order_by(Usuario.codigo.desc()).first()
            codigo = 2 if not ultimo or ultimo.codigo is None else ultimo.codigo + 1

        try:
            novo_usuario = Usuario(
                nome=nome,
                nome_usuario=nome_usuario,
                email=email,
                tipo=tipo,
                empresa_id=empresa_id,
                codigo=codigo
            )
            novo_usuario.set_senha(senha)
            db.session.add(novo_usuario)
            db.session.commit()

            # 📝 Log de criação de usuário
            registrar_log(
                usuario_id=current_user.id,
                acao="Criou usuário",
                detalhes=f"Código: {codigo}, Nome: {nome}, Nome de usuário: {nome_usuario}, Email: {email}, Tipo: {tipo}"
            )

            return render_template('criar_usuario.html', alerta='salvo')

        except IntegrityError:
            db.session.rollback()
            return render_template('criar_usuario.html',
                                   alerta='erro_interno',
                                   nome=nome,
                                   nome_usuario=nome_usuario,
                                   email=email,
                                   tipo=tipo)

    return render_template('criar_usuario.html')

@app.route('/salvar_usuarios', methods=['POST'])
@login_required
@permissoes_requeridas('admin')
def salvar_usuarios():
    nome = request.form['nome']
    nome_usuario = request.form['nome_usuario']
    email = request.form['email']
    senha = request.form['senha']
    tipo = request.form['tipo']

    # 🔎 Verificar se já existe usuário com mesmo nome_usuario ou email
    existente = Usuario.query.filter(
        (Usuario.nome_usuario == nome_usuario) | (Usuario.email == email)
    ).first()

    if existente:
        flash('Já existe um usuário com este nome de usuário ou email.')
        return redirect('/cadastro_usuarios')

    try:
        novo_usuario = Usuario(
            nome=nome,
            nome_usuario=nome_usuario,
            email=email,
            tipo=tipo
        )
        novo_usuario.set_senha(senha)
        db.session.add(novo_usuario)
        db.session.commit()

        # 📝 Log de criação de funcionário
        registrar_log(
            usuario_id=current_user.id,
            acao="Criou funcionário",
            detalhes=f"Nome: {nome}, Nome de usuário: {nome_usuario}, Email: {email}, Tipo: {tipo}"
        )

        flash('Funcionário cadastrado com sucesso!')
        return redirect('/listar_funcionarios')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Erro ao cadastrar funcionário: {e}")
        flash("Erro interno ao cadastrar funcionário.")
        return redirect('/cadastro_usuarios')
    


@app.route('/editar_cliente/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(cliente_id):

    def gerar_detalhes_alteracao(cliente_antigo, cliente_novo):
        campos = [
            'nome', 'email', 'telefone', 'empresa',
            'cpf_cnpj', 'endereco_rua', 'endereco_numero', 'endereco_complemento',
            'bairro', 'cidade', 'estado', 'rmcep'
        ]
        detalhes = []

        for campo in campos:
            antigo = getattr(cliente_antigo, campo)
            novo = getattr(cliente_novo, campo)
            if antigo != novo:
                detalhes.append(f"{campo}: '{antigo}' → '{novo}'")

        return "; ".join(detalhes)

    cliente = Cliente.query.get_or_404(cliente_id)
    cliente_original = copy.deepcopy(cliente)  # garante que os valores antigos não mudem

    if request.method == 'POST':
        cliente.nome = request.form.get('nome')
        cliente.cpf_cnpj = request.form.get('cpf_cnpj')
        cliente.telefone = request.form.get('telefone')
        cliente.email = request.form.get('email')
        cliente.empresa = request.form.get('empresa')
        cliente.endereco_rua = request.form.get('endereco_rua')
        cliente.endereco_numero = request.form.get('endereco_numero')
        cliente.endereco_complemento = request.form.get('endereco_complemento')
        cliente.bairro = request.form.get('bairro')
        cliente.cidade = request.form.get('cidade')
        cliente.estado = request.form.get('estado')
        cliente.rmcep = request.form.get('rmcep')

        try:
            alteracoes = gerar_detalhes_alteracao(cliente_original, cliente)
            db.session.commit()

            registrar_log(
                usuario_id=current_user.id,
                acao="Editou cliente",
                detalhes=f"Código: {cliente.codigo}; {alteracoes}"
            )

            flash('✅ Cliente atualizado com sucesso!', 'success')
            return redirect(url_for('listar_clientes'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erro ao editar cliente: {e}")
            flash("Erro interno ao atualizar cliente.", "erro")
            return render_template('editar_cliente.html', cliente=cliente)

    return render_template('editar_cliente.html', cliente=cliente)

@app.route('/detalhes_cliente/<int:cliente_id>')
@login_required
def detalhes_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)

    # 🔄 Ordena os contatos do cliente por data decrescente
    contatos_ordenados = sorted(cliente.contatos, key=lambda c: c.data, reverse=True)

    return render_template('detalhes_cliente.html', cliente=cliente, contatos=contatos_ordenados)



@app.route('/atualizar_cliente/<int:id>', methods=['POST'])
@login_required
def atualizar_cliente(id):
    cliente = Cliente.query.get_or_404(id)

    cliente.nome = request.form['nome']
    cliente.email = request.form['email']
    cliente.telefone = request.form['telefone']
    cliente.empresa = request.form['empresa']

    try:
        db.session.commit()

        # 📝 Log de atualização de cliente
        registrar_log(
            usuario_id=current_user.id,
            acao="Atualizou cliente",
            detalhes=f"ID: {cliente.id}, Código: {cliente.codigo}, Nome: {cliente.nome}, CPF/CNPJ: {cliente.cpf_cnpj}"
        )

        flash('Cliente atualizado com sucesso!', 'sucesso')
        return redirect('/listar_clientes')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Erro ao atualizar cliente: {e}")
        flash("Erro interno ao atualizar cliente.", "erro")
        return redirect('/listar_clientes')

@app.route('/excluir_cliente/<int:cliente_id>', methods=['POST'])
@login_required
def excluir_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)

    try:
        # 📝 Log antes da exclusão
        registrar_log(
            usuario_id=current_user.id,
            acao="Excluiu cliente",
            detalhes=f"Código: {cliente.codigo}; Nome: {cliente.nome}; CPF/CNPJ: {cliente.cpf_cnpj}"
        )

        db.session.delete(cliente)
        db.session.commit()

        flash("✅ Cliente excluído com sucesso!", "success")
        return redirect(url_for('listar_clientes'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Erro ao excluir cliente: {e}")
        flash("Erro interno ao excluir cliente.", "erro")
        return redirect(url_for('listar_clientes'))

@app.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):

    def gerar_detalhes_alteracao(usuario_antigo, usuario_novo):
        campos = ['nome', 'nome_usuario', 'email', 'tipo']
        detalhes = []
        for campo in campos:
            antigo = getattr(usuario_antigo, campo)
            novo = getattr(usuario_novo, campo)
            if antigo != novo:
                detalhes.append(f"{campo}: '{antigo}' → '{novo}'")
        return "; ".join(detalhes)

    usuario = Usuario.query.get_or_404(id)
    usuario_original = copy.deepcopy(usuario)

    if current_user.tipo != 'admin':
        flash("⚠️ Você não tem permissão para editar usuários.", "warning")
        return redirect(url_for('listar_funcionarios'))

    if request.method == 'POST':
        # Obtém dados do formulário
        nome = request.form['nome']
        nome_usuario = request.form['nome_usuario']
        email = request.form['email']
        senha = request.form['senha']
        tipo = request.form['tipo']

        # Verifica se o nome de login já existe
        login_existente = Usuario.query.filter_by(nome_usuario=nome_usuario).first()
        if login_existente and login_existente.id != usuario.id:
            flash("❌ Este login já está sendo usado por outro usuário.", "warning")
            return redirect(url_for('editar_usuario', id=usuario.id))

        # Atualiza os campos
        usuario.nome = nome
        usuario.nome_usuario = nome_usuario
        usuario.email = email
        usuario.tipo = tipo

        if senha:
            usuario.set_senha(senha)

        try:
            alteracoes = gerar_detalhes_alteracao(usuario_original, usuario)
            db.session.commit()

            registrar_log(
                usuario_id=current_user.id,
                acao="Editou usuário",
                detalhes=f"ID: {usuario.id}; {alteracoes}"
            )

            flash("✅ Usuário atualizado com sucesso!", "success")
            return redirect(url_for('listar_funcionarios'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erro ao editar usuário: {e}")
            flash("Erro interno ao atualizar usuário.", "erro")
            return render_template('editar_usuario.html', usuario=usuario)

    return render_template('editar_usuario.html', usuario=usuario)


@app.route('/excluir_usuario/<int:id>')
@login_required
@permissoes_requeridas ('admin' , 'gerente')
def excluir_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    db.session.delete(usuario)
    db.session.commit()
    flash('Funcionário excluído com sucesso!')
    return redirect('/listar_funcionarios')



    
    

@app.route('/listar_clientes')
@login_required
def listar_clientes():
    termo = request.args.get('busca')
    if termo:
        clientes = Cliente.query.filter(
            Cliente.nome.ilike(f"%{termo}%") |
            Cliente.email.ilike(f"%{termo}%") |
            Cliente.empresa.ilike(f"%{termo}%")
        ).all()
    else:
        clientes = Cliente.query.all()

    return render_template('listar_clientes.html', clientes=clientes)


    


import csv
from flask import Response
@app.route('/editar_permissao/<int:id>', methods=['GET', 'POST'])
@login_required
@permissoes_requeridas('admin')  # só admins podem editar permissões
def editar_permissao(id):
    usuario = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        novo_tipo = request.form.get('tipo')
        if novo_tipo in ['admin', 'gerente', 'funcionario']:
            tipo_antigo = usuario.tipo
            usuario.tipo = novo_tipo

            try:
                db.session.commit()

                # 📝 Log de alteração de permissão
                registrar_log(
                    usuario_id=current_user.id,
                    acao="Alterou permissão",
                    detalhes=f"Usuário ID: {usuario.id}, Nome: {usuario.nome}, Tipo antigo: {tipo_antigo}, Tipo novo: {novo_tipo}"
                )

                flash('Permissão atualizada com sucesso!')
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Erro ao atualizar permissão: {e}")
                flash("Erro interno ao atualizar permissão.")

        else:
            flash('Tipo inválido.')

        return redirect('/listar_funcionarios')
    
    

    return render_template('editar_permissao.html', usuario=usuario)
@app.route('/painel_logs')
@login_required
@permissoes_requeridas('admin')
def painel_logs():
    # 🔍 Ações distintas para o filtro
    acoes_raw = db.session.query(LogAcao.acao).distinct().all()
    acoes_lista = sorted({acao[0] for acao in acoes_raw if acao[0]})

    # 📄 Parâmetros da URL
    pagina = request.args.get('pagina', 1, type=int)
    termo = request.args.get('termo', '')
    acao = request.args.get('acao', '')  # ajustando nome para bater com o template

    # 🔎 Construção da consulta
    query = LogAcao.query.order_by(LogAcao.data_hora.desc())

    if termo:
        query = query.filter(LogAcao.detalhes.ilike(f"%{termo}%"))
    if acao:
        query = query.filter(LogAcao.acao == acao)

    # ⏱ Paginação
    logs = query.paginate(page=pagina, per_page=15)

    # 🧾 Renderização
    return render_template(
        'painel_logs.html',
        logs=logs,
        acoes=acoes_lista,
        termo=termo,
        acao=acao
    )

@app.route('/alternar_status/<int:id>')
@login_required
def alternar_status(id):
    usuario = Usuario.query.get_or_404(id)

    usuario.ativo = not usuario.ativo  # alterna entre True e False
    db.session.commit()

    if usuario.ativo:
        flash(f"O usuário {usuario.nome} foi reativado com sucesso.")
    else:
        flash(f"O usuário {usuario.nome} foi inativado com sucesso.")

    return redirect('/listar_funcionarios')

@app.route('/exportar_clientes')
@login_required
def exportar_clientes():
    clientes = Cliente.query.all()
    si = csv.StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Nome', 'Email', 'Telefone', 'Empresa', 'Data'])
    for c in clientes:
        writer.writerow([c.id, c.nome, c.email, c.telefone, c.empresa, c.data_criacao.strftime('%d/%m/%Y')])
    output = Response(si.getvalue(), mimetype='text/csv')
    output.headers["Content-Disposition"] = "attachment; filename=clientes.csv"
    return output

from sqlalchemy import cast, Integer

@app.route('/cadastro_empresa', methods=['GET', 'POST'])
def cadastro_empresa():
    def limpar_cnpj(cnpj_original):
        return cnpj_original.replace('.', '').replace('/', '').replace('-', '')

    def validar_cnpj(cnpj):
        cnpj = ''.join(filter(str.isdigit, cnpj))
        if len(cnpj) != 14 or cnpj in (c * 14 for c in "1234567890"):
            return False

        def calc_digito(cnpj, pesos):
            soma = sum(int(n) * p for n, p in zip(cnpj, pesos))
            resto = soma % 11
            return '0' if resto < 2 else str(11 - resto)

        digito1 = calc_digito(cnpj[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
        digito2 = calc_digito(cnpj[:13], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
        return cnpj[-2:] == digito1 + digito2

    def gerar_codigo():
        ultimo_usuario = Usuario.query.order_by(
            cast(Usuario.codigo, Integer).desc()
        ).first()

        try:
            ultimo_codigo = int(ultimo_usuario.codigo)
            return str(ultimo_codigo + 1)
        except (AttributeError, ValueError):
            return '1'

    if request.method == 'POST':
        nome_empresa   = request.form.get('nome')
        email_empresa  = request.form.get('email')
        telefone       = request.form.get('telefone')
        endereco       = request.form.get('endereco')
        cidade         = request.form.get('cidade')
        estado         = request.form.get('estado')
        representante  = request.form.get('representante')
        cnpj           = limpar_cnpj(request.form.get('cnpj'))

        admin_nome     = request.form.get('admin_nome')
        admin_login    = request.form.get('admin_login')
        admin_email    = request.form.get('admin_email')
        admin_senha    = request.form.get('admin_senha')

        if not all([nome_empresa, cnpj, telefone, admin_nome, admin_login, admin_email, admin_senha]):
            flash("Preencha todos os campos obrigatórios!", "danger")
            return redirect(url_for('cadastro_empresa'))

        if not validar_cnpj(cnpj):
            flash("CNPJ inválido!", "danger")
            return redirect(url_for('cadastro_empresa'))

        try:
            base_slug = slugify(nome_empresa)
            slug_final = base_slug
            contador = 1
            while Empresa.query.filter_by(slug=slug_final).first():
                slug_final = f"{base_slug}-{contador}"
                contador += 1

            nova_empresa = Empresa(
                nome=nome_empresa,
                slug=slug_final,
                plano='gratuito',
                criada_em=datetime.now(UTC),
                cnpj=cnpj,
                telefone=telefone,
                email=email_empresa,
                endereco=endereco,
                cidade=cidade,
                estado=estado,
                representante=representante,
                codigo=str(uuid.uuid4())[:8]
            )

            db.session.add(nova_empresa)
            db.session.commit()

            if Usuario.query.filter_by(nome_usuario=admin_login).first():
                flash("Login já está em uso. Escolha outro.", "warning")
                return redirect(url_for('cadastro_empresa'))

            codigo = gerar_codigo()

            novo_admin = Usuario(
                codigo=codigo,
                nome=admin_nome,
                nome_usuario=admin_login,
                email=admin_email,
                senha_hash=generate_password_hash(admin_senha),
                tipo='admin',
                empresa_id=nova_empresa.id if admin_nome.lower() != 'admin' else None,
                ativo=True
            )

            db.session.add(novo_admin)
            db.session.commit()

            flash("Cadastro realizado com sucesso!", "success")
            return redirect(url_for('login'))

        except Exception as e:
            print(f"Erro ao cadastrar: {e}")
            flash("Erro ao cadastrar empresa ou usuário.", "danger")
            return redirect(url_for('login'))

    return render_template('cadastro_empresa.html')










def gerar_codigo():
    ultimo_usuario = Usuario.query.order_by(
        Usuario.codigo.cast(db.Integer).desc()
    ).first()

    try:
        ultimo_codigo = int(ultimo_usuario.codigo)
        return str(ultimo_codigo + 1)
    except (AttributeError, ValueError):
        return '1'  # Primeiro usuário
app.register_blueprint(relatorios_bp)

# Inicialização do servidor/# Criação automática do banco de dados na primeira execução
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # 🏢 Verifica se a empresa existe
        empresa = Empresa.query.filter_by(slug='empresateste').first()
        if not empresa:
            empresa = Empresa(
                nome='Empresa Teste',
                slug='empresateste',
                plano='gratuito'
            )
            db.session.add(empresa)
            db.session.commit()
            print(f'✅ Empresa "{empresa.nome}" criada com sucesso.')

        # 🔐 Verifica se o admin já existe
        admin_existente = Usuario.query.filter_by(email='admin@email.com').first()
        print("Admin existente?", bool(admin_existente))
        if not admin_existente:
            codigo = gerar_codigo()  # 👈 garantindo que o admin tenha código
            admin = Usuario(
                codigo=codigo,
                nome='admin',
                nome_usuario='admin',
                email='admin@email.com',
                tipo='admin',
                empresa_id=None  # 👈 admin global sem vínculo
            )
            admin.set_senha('123')
            db.session.add(admin)
            db.session.commit()
            print('✅ Usuário admin global criado com sucesso.')
        else:
            print('ℹ️ Usuário admin já existe.')
            

    # 🔥 Aqui inicia o servidor Flask
    app.run(debug=True)
    



    
