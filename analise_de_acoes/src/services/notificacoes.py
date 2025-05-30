"""
Módulo para gerenciamento de notificações e alertas do sistema.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
import os
from twilio.rest import Client
from ..models.alertas import Alerta, TipoAlerta, StatusAlerta
from ..models.usuario import Usuario, PreferenciasNotificacao
from .. import db, app
from ..utils.logger import logger

class Notificador:
    """Classe base para notificações."""
    
    def __init__(self):
        """Inicializa o notificador."""
        self.tipo = 'base'
    
    def enviar(self, destinatario: str, assunto: str, mensagem: str, **kwargs) -> bool:
        """
        Método base para envio de notificação.
        
        Args:
            destinatario (str): Endereço de e-mail ou número de telefone do destinatário.
            assunto (str): Assunto da mensagem.
            mensagem (str): Corpo da mensagem.
            **kwargs: Argumentos adicionais específicos de cada implementação.
            
        Returns:
            bool: True se a notificação foi enviada com sucesso, False caso contrário.
        """
        raise NotImplementedError("Método 'enviar' deve ser implementado pelas subclasses.")


class NotificadorEmail(Notificador):
    """Implementação de notificador por e-mail."""
    
    def __init__(self):
        """Inicializa o notificador de e-mail."""
        super().__init__()
        self.tipo = 'email'
        self.smtp_server = app.config.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = app.config.get('SMTP_PORT', 587)
        self.smtp_username = app.config.get('SMTP_USERNAME', '')
        self.smtp_password = app.config.get('SMTP_PASSWORD', '')
        self.smtp_use_tls = app.config.get('SMTP_USE_TLS', True)
        self.smtp_from = app.config.get('MAIL_DEFAULT_SENDER', 'noreply@analisedeacoes.com')
    
    def enviar(self, destinatario: str, assunto: str, mensagem: str, **kwargs) -> bool:
        """
        Envia um e-mail.
        
        Args:
            destinatario (str): Endereço de e-mail do destinatário.
            assunto (str): Assunto do e-mail.
            mensagem (str): Corpo do e-mail (pode ser HTML).
            **kwargs: Argumentos adicionais:
                - html (bool): Se True, a mensagem será enviada como HTML.
                
        Returns:
            bool: True se o e-mail foi enviado com sucesso, False caso contrário.
        """
        try:
            # Cria a mensagem
            msg = MIMEMultipart()
            msg['From'] = self.smtp_from
            msg['To'] = destinatario
            msg['Subject'] = assunto
            
            # Define o corpo da mensagem
            is_html = kwargs.get('html', False)
            if is_html:
                msg.attach(MIMEText(mensagem, 'html'))
            else:
                msg.attach(MIMEText(mensagem, 'plain'))
            
            # Conecta ao servidor SMTP e envia o e-mail
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                
                server.send_message(msg)
                logger.info(f"E-mail enviado para {destinatario} com sucesso.")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail para {destinatario}: {str(e)}")
            return False


class NotificadorSMS(Notificador):
    """Implementação de notificador por SMS."""
    
    def __init__(self):
        """Inicializa o notificador de SMS."""
        super().__init__()
        self.tipo = 'sms'
        self.twilio_account_sid = app.config.get('TWILIO_ACCOUNT_SID', '')
        self.twilio_auth_token = app.config.get('TWILIO_AUTH_TOKEN', '')
        self.twilio_phone_number = app.config.get('TWILIO_PHONE_NUMBER', '')
        self.client = None
        
        if self.twilio_account_sid and self.twilio_auth_token:
            self.client = Client(self.twilio_account_sid, self.twilio_auth_token)
    
    def enviar(self, destinatario: str, mensagem: str, **kwargs) -> bool:
        """
        Envia um SMS.
        
        Args:
            destinatario (str): Número de telefone do destinatário (com código do país).
            mensagem (str): Mensagem de texto.
            **kwargs: Argumentos adicionais (não utilizados).
            
        Returns:
            bool: True se o SMS foi enviado com sucesso, False caso contrário.
        """
        if not self.client:
            logger.error("Twilio client não configurado corretamente.")
            return False
            
        try:
            # Remove caracteres não numéricos do número de telefone
            destinatario = ''.join(filter(str.isdigit, destinatario))
            
            # Envia o SMS
            message = self.client.messages.create(
                body=mensagem,
                from_=self.twilio_phone_number,
                to=f"+{destinatario}"  # Adiciona o sinal de + se não estiver presente
            )
            
            logger.info(f"SMS enviado para {destinatario} com sucesso (ID: {message.sid}).")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar SMS para {destinatario}: {str(e)}")
            return False


class NotificadorPush(Notificador):
    """Implementação de notificador por push notification."""
    
    def __init__(self):
        """Inicializa o notificador de push."""
        super().__init__()
        self.tipo = 'push'
        # Aqui você pode adicionar configurações específicas para o serviço de push
        # como chaves de API para Firebase Cloud Messaging (FCM), OneSignal, etc.
    
    def enviar(self, destinatario: str, titulo: str, mensagem: str, **kwargs) -> bool:
        """
        Envia uma notificação push.
        
        Args:
            destinatario (str): ID do dispositivo ou token do usuário.
            titulo (str): Título da notificação.
            mensagem (str): Corpo da mensagem.
            **kwargs: Argumentos adicionais:
                - data (dict): Dados adicionais para a notificação.
                
        Returns:
            bool: True se a notificação foi enviada com sucesso, False caso contrário.
        """
        try:
            # Implementação de exemplo para FCM (Firebase Cloud Messaging)
            # Em um ambiente real, você usaria o SDK do FCM
            data = kwargs.get('data', {})
            
            logger.info(f"Notificação push enviada para {destinatario}: {titulo} - {mensagem}")
            logger.debug(f"Dados adicionais: {data}")
            
            # Simula o envio da notificação
            # Em produção, você faria uma chamada para a API do FCM ou serviço similar
            # Exemplo com FCM:
            # from firebase_admin import messaging
            # message = messaging.Message(
            #     notification=messaging.Notification(
            #         title=titulo,
            #         body=mensagem,
            #     ),
            #     data=data,
            #     token=destinatario,
            # )
            # response = messaging.send(message)
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar notificação push para {destinatario}: {str(e)}")
            return False


class GerenciadorNotificacoes:
    """Gerencia o envio de notificações através de múltiplos canais."""
    
    def __init__(self):
        """Inicializa o gerenciador de notificações."""
        self.notificadores = {
            'email': NotificadorEmail(),
            'sms': NotificadorSMS(),
            'push': NotificadorPush()
        }
    
    def enviar_notificacao(
        self, 
        usuario_id: int, 
        tipo_alerta: str, 
        titulo: str, 
        mensagem: str,
        dados_adicionais: Optional[Dict] = None,
        forcar_envio: bool = False
    ) -> Dict[str, bool]:
        """
        Envia uma notificação para um usuário através dos canais configurados.
        
        Args:
            usuario_id (int): ID do usuário destinatário.
            tipo_alerta (str): Tipo de alerta (ex: 'preco_atingido', 'alerta_mercado').
            titulo (str): Título da notificação.
            mensagem (str): Mensagem da notificação.
            dados_adicionais (Dict, optional): Dados adicionais para a notificação. Defaults to None.
            forcar_envio (bool, optional): Se True, envia a notificação mesmo se o usuário tiver desativado. Defaults to False.
            
        Returns:
            Dict[str, bool]: Dicionário com o status de envio para cada canal.
        """
        try:
            # Busca o usuário e suas preferências
            usuario = Usuario.query.get(usuario_id)
            if not usuario:
                logger.error(f"Usuário com ID {usuario_id} não encontrado.")
                return {}
            
            # Verifica se o usuário quer receber notificações
            if not forcar_envio and not usuario.receber_notificacoes:
                logger.info(f"Usuário {usuario_id} optou por não receber notificações.")
                return {}
            
            # Obtém as preferências de notificação do usuário
            preferencias = PreferenciasNotificacao.query.filter_by(usuario_id=usuario_id).first()
            if not preferencias:
                logger.info(f"Usuário {usuario_id} não possui preferências de notificação definidas. Usando padrões.")
                preferencias = PreferenciasNotificacao(usuario_id=usuario_id)
            
            # Prepara os dados da notificação
            dados_adicionais = dados_adicionais or {}
            
            # Resultados do envio
            resultados = {}
            
            # Envia notificação por e-mail se habilitado
            if (forcar_envio or preferencias.email_habilitado) and usuario.email:
                email_enviado = self.notificadores['email'].enviar(
                    destinatario=usuario.email,
                    assunto=titulo,
                    mensagem=mensagem,
                    html=True
                )
                resultados['email'] = email_enviado
            
            # Envia notificação por SMS se habilitado
            if (forcar_envio or preferencias.sms_habilitado) and usuario.telefone:
                sms_enviado = self.notificadores['sms'].enviar(
                    destinatario=usuario.telefone,
                    mensagem=f"{titulo}: {mensagem}"
                )
                resultados['sms'] = sms_enviado
            
            # Envia notificação push se habilitado e o token estiver disponível
            if (forcar_envio or preferencias.push_habilitado) and usuario.push_token:
                push_enviado = self.notificadores['push'].enviar(
                    destinatario=usuario.push_token,
                    titulo=titulo,
                    mensagem=mensagem,
                    data={
                        'tipo_alerta': tipo_alerta,
                        **dados_adicionais
                    }
                )
                resultados['push'] = push_enviado
            
            # Registra a notificação no banco de dados
            self._registrar_notificacao(
                usuario_id=usuario_id,
                tipo_alerta=tipo_alerta,
                titulo=titulo,
                mensagem=mensagem,
                canais=list(resultados.keys()),
                dados_adicionais=dados_adicionais
            )
            
            return resultados
            
        except Exception as e:
            logger.error(f"Erro ao enviar notificação para o usuário {usuario_id}: {str(e)}")
            return {}
    
    def _registrar_notificacao(
        self,
        usuario_id: int,
        tipo_alerta: str,
        titulo: str,
        mensagem: str,
        canais: List[str],
        dados_adicionais: Optional[Dict] = None
    ) -> None:
        """
        Registra uma notificação no banco de dados.
        
        Args:
            usuario_id (int): ID do usuário destinatário.
            tipo_alerta (str): Tipo de alerta.
            titulo (str): Título da notificação.
            mensagem (str): Mensagem da notificação.
            canais (List[str]): Lista de canais utilizados para o envio.
            dados_adicionais (Dict, optional): Dados adicionais. Defaults to None.
        """
        try:
            notificacao = Alerta(
                usuario_id=usuario_id,
                tipo=tipo_alerta,
                titulo=titulo,
                mensagem=mensagem,
                canais=",".join(canais),
                dados_adicionais=dados_adicionais or {},
                status=StatusAlerta.ENVIADO,
                data_envio=datetime.utcnow()
            )
            
            db.session.add(notificacao)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Erro ao registrar notificação no banco de dados: {str(e)}")
            db.session.rollback()
    
    def verificar_alertas_preco(self) -> None:
        """
        Verifica e dispara alertas de preço configurados pelos usuários.
        """
        try:
            logger.info("Iniciando verificação de alertas de preço...")
            
            # Busca todos os alertas de preço ativos
            alertas = Alerta.query.filter_by(
                tipo=TipoAlerta.PRECO_ATINGIDO,
                status=StatusAlerta.ATIVO
            ).all()
            
            if not alertas:
                logger.info("Nenhum alerta de preço ativo encontrado.")
                return
            
            logger.info(f"Verificando {len(alertas)} alertas de preço...")
            
            # Agrupa alertas por ativo para otimizar as consultas
            alertas_por_ativo = {}
            for alerta in alertes:
                if alerta.ativo_id not in alertas_por_ativo:
                    alertas_por_ativo[alerta.ativo_id] = []
                alertas_por_ativo[alerta.ativo_id].append(alerta)
            
            # Para cada ativo com alertas, verifica o preço atual
            for ativo_id, alertas_ativo in alertas_por_ativo.items():
                ativo = Ativo.query.get(ativo_id)
                if not ativo or not ativo.preco_atual:
                    continue
                
                preco_atual = ativo.preco_atual
                
                # Verifica cada alerta para este ativo
                for alerta in alertas_ativo:
                    try:
                        # Verifica se o preço atual atinge a condição do alerta
                        condicao = alerta.dados_adicionais.get('condicao', 'maior_igual')
                        preco_alvo = alerta.dados_adicionais.get('preco_alvo', 0)
                        
                        disparar = False
                        
                        if condicao == 'maior_igual' and preco_atual >= preco_alvo:
                            disparar = True
                        elif condicao == 'menor_igual' and preco_atual <= preco_alvo:
                            disparar = True
                        elif condicao == 'igual' and preco_atual == preco_alvo:
                            disparar = True
                        
                        if disparar:
                            # Prepara a mensagem do alerta
                            mensagem = (
                                f"O ativo {ativo.symbol} ({ativo.nome or ''}) "
                                f"atingiu o preço de R$ {preco_atual:.2f}. "
                                f"(Alerta: {condicao} R$ {preco_alvo:.2f})"
                            )
                            
                            # Envia a notificação
                            self.enviar_notificacao(
                                usuario_id=alerta.usuario_id,
                                tipo_alerta=TipoAlerta.PRECO_ATINGIDO,
                                titulo=f"Alerta de Preço: {ativo.symbol}",
                                mensagem=mensagem,
                                dados_adicionais={
                                    'ativo_id': ativo.id,
                                    'simbolo': ativo.symbol,
                                    'preco_atual': preco_atual,
                                    'preco_alvo': preco_alvo,
                                    'condicao': condicao,
                                    'alerta_id': alerta.id
                                }
                            )
                            
                            # Atualiza o status do alerta para disparado
                            alerta.status = StatusAlerta.DISPARADO
                            alerta.data_disparo = datetime.utcnow()
                            db.session.commit()
                            
                    except Exception as e:
                        logger.error(f"Erro ao processar alerta {alerta.id}: {str(e)}")
                        db.session.rollback()
                        continue
            
            logger.info("Verificação de alertas de preço concluída.")
            
        except Exception as e:
            logger.error(f"Erro ao verificar alertas de preço: {str(e)}")
            db.session.rollback()


# Instância global do gerenciador de notificações
notificador = GerenciadorNotificacoes()

# Exemplo de uso:
if __name__ == "__main__":
    # Configuração básica do Flask para teste
    from flask import Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicializa o banco de dados
    from .. import db
    db.init_app(app)
    
    with app.app_context():
        # Cria as tabelas
        db.create_all()
        
        # Exemplo de envio de notificação
        resultados = notificador.enviar_notificacao(
            usuario_id=1,
            tipo_alerta='teste',
            titulo='Teste de Notificação',
            mensagem='Esta é uma mensagem de teste enviada pelo sistema.',
            forcar_envio=True
        )
        
        print(f"Resultados do envio: {resultados}")
        
        # Exemplo de verificação de alertas de preço
        notificador.verificar_alertas_preco()
