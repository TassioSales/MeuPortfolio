"""
Authentication routes for the application.
Handles user login, logout, registration, and password management.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import logging

from src.models import db, Usuario
from src.utils.logger import setup_logger

# Setup logger
auth_logger = setup_logger('auth_routes', 'auth.log')

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        # Validate input
        if not username or not password:
            flash('Por favor, preencha todos os campos.', 'error')
            return redirect(url_for('auth.login'))
        
        # Find user by username
        user = Usuario.query.filter_by(usuario=username).first()
        
        # Check if user exists and password is correct
        if not user or not check_password_hash(user.senha, password):
            auth_logger.warning(f'Falha no login para o usuário: {username}')
            flash('Usuário ou senha incorretos.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if account is active
        if not user.ativo:
            auth_logger.warning(f'Tentativa de login em conta inativa: {username}')
            flash('Esta conta está desativada. Entre em contato com o administrador.', 'error')
            return redirect(url_for('auth.login'))
        
        # Log the successful login
        auth_logger.info(f'Login bem-sucedido para o usuário: {username}')
        
        # Update last login time
        user.ultimo_login = datetime.utcnow()
        db.session.commit()
        
        # Log the user in
        login_user(user, remember=remember)
        
        # Redirect to the next page if it exists, otherwise go to dashboard
        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.dashboard'))
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    auth_logger.info(f'Usuário fez logout: {current_user.usuario}')
    logout_user()
    flash('Você saiu da sua conta com sucesso.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle new user registration (admin only)."""
    # Only allow admin to register new users
    if not current_user.is_authenticated or not current_user.eh_admin:
        flash('Acesso não autorizado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        is_admin = True if request.form.get('is_admin') else False
        
        # Validate input
        if not all([username, email, password, confirm_password]):
            flash('Por favor, preencha todos os campos obrigatórios.', 'error')
            return redirect(url_for('auth.register'))
        
        if password != confirm_password:
            flash('As senhas não coincidem.', 'error')
            return redirect(url_for('auth.register'))
        
        # Check if username or email already exists
        if Usuario.query.filter_by(usuario=username).first():
            flash('Nome de usuário já está em uso.', 'error')
            return redirect(url_for('auth.register'))
        
        if Usuario.query.filter_by(email=email).first():
            flash('Endereço de e-mail já está em uso.', 'error')
            return redirect(url_for('auth.register'))
        
        # Create new user
        try:
            new_user = Usuario(
                usuario=username,
                email=email,
                senha=generate_password_hash(password, method='pbkdf2:sha256'),
                eh_admin=is_admin,
                ativo=True,
                data_cadastro=datetime.utcnow(),
                ultimo_login=None
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            auth_logger.info(f'Novo usuário registrado por {current_user.usuario}: {username}')
            flash('Usuário registrado com sucesso!', 'success')
            return redirect(url_for('auth.users'))
            
        except Exception as e:
            db.session.rollback()
            auth_logger.error(f'Erro ao registrar novo usuário: {str(e)}')
            flash('Ocorreu um erro ao registrar o usuário. Por favor, tente novamente.', 'error')
    
    return render_template('auth/register.html')

@auth_bp.route('/users')
@login_required
def users():
    """List all users (admin only)."""
    if not current_user.eh_admin:
        flash('Acesso não autorizado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    users = Usuario.query.order_by(Usuario.data_cadastro.desc()).all()
    return render_template('auth/users.html', users=users)

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Update user profile."""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate current password
        if not check_password_hash(current_user.senha, current_password):
            flash('Senha atual incorreta.', 'error')
            return redirect(url_for('auth.profile'))
        
        # Validate new password
        if new_password != confirm_password:
            flash('As novas senhas não coincidem.', 'error')
            return redirect(url_for('auth.profile'))
        
        # Update password
        try:
            current_user.senha = generate_password_hash(new_password, method='pbkdf2:sha256')
            db.session.commit()
            
            auth_logger.info(f'Senha alterada para o usuário: {current_user.usuario}')
            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            auth_logger.error(f'Erro ao atualizar senha: {str(e)}')
            flash('Ocorreu um erro ao atualizar sua senha. Por favor, tente novamente.', 'error')
    
    return render_template('auth/profile.html')

@auth_bp.route('/request-reset', methods=['GET', 'POST'])
def request_reset():
    """Request password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = Usuario.query.filter_by(email=email).first()
        
        if user:
            # In a real app, you would send an email with a reset link
            # For now, we'll just log it
            auth_logger.info(f'Solicitação de redefinição de senha para: {email}')
        
        # Always show success to prevent email enumeration
        flash('Se o e-mail estiver cadastrado, você receberá um link para redefinir sua senha.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/request_reset.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    # In a real app, you would verify the token
    # For now, we'll just check if it's a valid email
    user = Usuario.query.filter_by(email=token).first()
    
    if not user:
        flash('Link de redefinição inválido ou expirado.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('As senhas não coincidem.', 'error')
            return redirect(url_for('auth.reset_password', token=token))
        
        try:
            user.senha = generate_password_hash(password, method='pbkdf2:sha256')
            db.session.commit()
            
            auth_logger.info(f'Senha redefinida para o usuário: {user.usuario}')
            flash('Sua senha foi redefinida com sucesso! Faça login com a nova senha.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            auth_logger.error(f'Erro ao redefinir senha: {str(e)}')
            flash('Ocorreu um erro ao redefinir sua senha. Por favor, tente novamente.', 'error')
    
    return render_template('auth/reset_password.html', token=token)
