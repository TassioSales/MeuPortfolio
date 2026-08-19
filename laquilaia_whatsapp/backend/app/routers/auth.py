"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from app.db.database import get_db_session
from app.db.models import User
from app.utils.auth_middleware import require_admin
from app.models.schemas import (
    TrocaDeSenha,
    UserUpdateByAdmin,
    TokenResponse,
    UserCreate,
    UserCreateByAdmin,
    UserLogin,
    UserResponse,
)
from app.services.auth_service import auth_service
from app.utils.auth_middleware import get_current_user
from app.utils.exceptions import UserAlreadyExistsException, InvalidCredentialsException
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Cria a conta do administrador — uma única vez.

    O cadastro é aberto enquanto não existe ninguém, e fecha no primeiro
    usuário criado. É o que resolve o ovo e a galinha sem script de bootstrap
    nem senha em variável de ambiente: quem instala o sistema abre a tela e
    cria a própria conta; qualquer um que chegue depois encontra a porta
    fechada.

    Operadores passam a ser criados pelo administrador, em `POST /auth/users`.
    """
    try:
        # Check if user already exists
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_user = result.scalars().first()

        if existing_user:
            logger.warning(f"⚠️ Registration attempt with existing email: {user_data.email}")
            raise UserAlreadyExistsException()

        total = await db.execute(select(func.count(User.id)))
        if (total.scalar() or 0) > 0:
            logger.warning("⚠️ Cadastro público recusado: o sistema já tem administrador")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "O cadastro está fechado. Peça ao administrador para criar "
                    "o seu acesso."
                ),
            )

        # Create new user
        hashed_password = auth_service.hash_password(user_data.senha)

        new_user = User(
            email=user_data.email,
            nome=user_data.nome,
            senha_hash=hashed_password,
            status="ativo",
            # O primeiro é o dono do sistema.
            papel="admin",
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        logger.info(f"✅ New user registered: {user_data.email}")

        return UserResponse(
            id=new_user.id,
            email=new_user.email,
            nome=new_user.nome,
            status=new_user.status,
            data_criacao=new_user.data_criacao,
        )

    except UserAlreadyExistsException:
        raise
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Registration error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during registration",
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db_session),
):
    """Login user and return access and refresh tokens."""
    try:
        # Find user by email
        result = await db.execute(
            select(User).where(User.email == credentials.email)
        )
        user = result.scalars().first()

        # Verify user exists and password is correct
        if not user or not auth_service.verify_password(credentials.senha, user.senha_hash):
            logger.warning(f"⚠️ Failed login attempt: {credentials.email}")
            raise InvalidCredentialsException()

        # Verify user is active
        if user.status != "ativo":
            logger.warning(f"⚠️ Login attempt by inactive user: {credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active",
            )

        # Create tokens
        access_token, refresh_token = auth_service.create_tokens(user.id)

        logger.info(f"✅ User logged in: {credentials.email}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

    except (InvalidCredentialsException, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during login",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: dict,
):
    """Refresh access token using a valid refresh token."""
    try:
        refresh_token = token_data.get("refresh_token")

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token is required",
            )

        # Verify and decode refresh token
        new_access_token = auth_service.refresh_access_token(refresh_token)

        if not new_access_token:
            logger.warning("⚠️ Invalid refresh token attempt")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        logger.info("✅ Access token refreshed")

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during token refresh",
        )


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Return the profile of the user owning the current access token."""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            logger.warning(f"⚠️ Token valid but user not found: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return UserResponse(
            id=user.id,
            email=user.email,
            nome=user.nome,
            status=user.status,
            # Sem isto o schema cai no default "operador" e o painel esconde do
            # administrador as telas que só ele pode abrir.
            papel=user.papel,
            data_criacao=user.data_criacao,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching current user",
        )


@router.post("/verify-token")
async def verify_token(
    token_data: dict,
):
    """Verify if a token is valid."""
    try:
        token = token_data.get("token")

        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is required",
            )

        user_id = auth_service.verify_token(token)

        if not user_id:
            return {
                "valid": False,
                "user_id": None,
                "message": "Token is invalid or expired",
            }

        return {
            "valid": True,
            "user_id": user_id,
            "message": "Token is valid",
        }

    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during token verification",
        )


# Import settings for token expiry
from app.config import settings


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def criar_usuario(
    dados: UserCreateByAdmin,
    _admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Cria um acesso — só o administrador.

    É por aqui que entram os operadores, agora que o cadastro público fecha no
    primeiro usuário. O papel vem do corpo e é validado pelo schema: nada de
    string livre virando privilégio.
    """
    try:
        existente = await db.execute(select(User).where(User.email == dados.email))
        if existente.scalars().first():
            raise UserAlreadyExistsException()

        usuario = User(
            email=dados.email,
            nome=dados.nome,
            senha_hash=auth_service.hash_password(dados.senha),
            status="ativo",
            papel=dados.papel,
        )
        db.add(usuario)
        await db.commit()
        await db.refresh(usuario)

        logger.info(f"👤 Acesso criado: {usuario.email} ({usuario.papel})")
        return UserResponse.model_validate(usuario)

    except UserAlreadyExistsException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao criar acesso: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao criar acesso",
        )


@router.get("/users", response_model=list[UserResponse])
async def listar_usuarios(
    _admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Quem tem acesso ao sistema — só o administrador enxerga.

    A lista é o que torna o controle de acesso administrável: sem ela, saber
    quem entra no painel exige consultar o banco, e o que exige terminal na
    prática não é feito.
    """
    resultado = await db.execute(select(User).order_by(User.data_criacao))
    return [UserResponse.model_validate(u) for u in resultado.scalars().all()]


@router.patch("/users/{user_id}", response_model=UserResponse)
async def alterar_usuario(
    user_id: str,
    dados: UserUpdateByAdmin,
    admin_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Muda papel ou status de um acesso — só o administrador.

    Desativar é como se tira acesso de quem saiu do escritório, e vale na hora:
    `get_current_user` confere o status a cada requisição, então o token que a
    pessoa já tem para de funcionar imediatamente.

    O administrador não pode desativar nem rebaixar a **si mesmo**. Não é
    paternalismo: o sistema tem um único caminho para criar administrador (o
    primeiro cadastro, que já fechou), e um admin que se rebaixa por engano
    deixa a instalação sem ninguém que possa consertá-la.
    """
    resultado = await db.execute(select(User).where(User.id == user_id))
    usuario = resultado.scalars().first()

    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if usuario.id == admin_id and (
        dados.status == "inativo" or dados.papel == "operador"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode remover o próprio acesso de administrador.",
        )

    if dados.papel is not None:
        usuario.papel = dados.papel
    if dados.status is not None:
        usuario.status = dados.status

    await db.commit()
    await db.refresh(usuario)

    logger.info(
        f"👤 Acesso alterado por {admin_id}: {usuario.email} "
        f"({usuario.papel}, {usuario.status})"
    )
    return UserResponse.model_validate(usuario)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def trocar_a_propria_senha(
    dados: TrocaDeSenha,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    A pessoa troca a própria senha.

    Exige a senha atual mesmo com a sessão aberta: um navegador esquecido
    aberto num computador do escritório não pode virar troca de senha — que é
    como se toma uma conta de alguém sem que ele perceba.

    O administrador **não** aparece aqui de propósito: ele cria e desativa
    acessos, não troca a senha alheia. Trocar a senha de outro é poder entrar
    como ele, e aí o registro do sistema passa a mentir sobre quem fez o quê.
    """
    resultado = await db.execute(select(User).where(User.id == user_id))
    usuario = resultado.scalars().first()

    if usuario is None or not auth_service.verify_password(
        dados.senha_atual, usuario.senha_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta.",
        )

    usuario.senha_hash = auth_service.hash_password(dados.senha_nova)
    await db.commit()

    logger.info(f"🔑 Senha trocada por {usuario.email}")
