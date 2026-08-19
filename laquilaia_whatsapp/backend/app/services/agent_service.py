"""Agent management service."""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.db.models import Agent, AgentVariable
from app.models.schemas import AgentCreate, AgentUpdate, AgentResponse
from app.services.kanban_defaults import criar_colunas_padrao
from app.utils.exceptions import NotFoundException, ValidationException
from app.utils.logger import logger


class AgentService:
    """Service for managing AI agents."""

    @staticmethod
    async def create_agent(
        user_id: str,
        agent_data: AgentCreate,
        db: AsyncSession,
    ) -> AgentResponse:
        """Create a new agent."""
        try:
            # Validate system_prompt is not empty
            if not agent_data.system_prompt.strip():
                raise ValidationException("System prompt cannot be empty")

            # Validate temperatura is in valid range
            if not (0 <= agent_data.temperatura <= 2):
                raise ValidationException("Temperature must be between 0 and 2")

            # Validate max_tokens
            if not (1 <= agent_data.max_tokens <= 4096):
                raise ValidationException("Max tokens must be between 1 and 4096")

            new_agent = Agent(
                user_id=user_id,
                nome=agent_data.nome,
                nome_atendente=agent_data.nome_atendente,
                descricao=agent_data.descricao,
                system_prompt=agent_data.system_prompt,
                anexos_habilitados=agent_data.anexos_habilitados,
                temperatura=agent_data.temperatura,
                max_tokens=agent_data.max_tokens,
                status="ativo",
            )

            db.add(new_agent)
            # O id é gerado na aplicação, mas o flush garante que a linha do
            # agente exista antes das colunas que a referenciam.
            await db.flush()

            # O funil nasce junto com o agente. Antes ele só existia via
            # `POST /kanban/columns/init`, que nada chamava: um lead
            # qualificado por agente criado pela tela era gravado e nunca
            # aparecia no board, porque não havia coluna para receber o card.
            await criar_colunas_padrao(new_agent.id, db)

            await db.commit()
            await db.refresh(new_agent)

            logger.info(f"✅ Agent created: {new_agent.id} (user: {user_id})")

            return AgentResponse(
                id=new_agent.id,
                user_id=new_agent.user_id,
                nome=new_agent.nome,
                nome_atendente=new_agent.nome_atendente,
                descricao=new_agent.descricao,
                system_prompt=new_agent.system_prompt,
                anexos_habilitados=new_agent.anexos_habilitados,
                temperatura=new_agent.temperatura,
                max_tokens=new_agent.max_tokens,
                status=new_agent.status,
                data_criacao=new_agent.data_criacao,
                data_atualizacao=new_agent.data_atualizacao,
            )

        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"❌ Error creating agent: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def get_agent(
        agent_id: str,
        db: AsyncSession,
    ) -> AgentResponse:
        """
        O agente pelo id. Do escritório, não de quem pergunta.

        Antes havia um filtro por dono — `Agent.user_id == user_id` — e ele
        parecia segurança, mas não era: esta instalação atende **um**
        escritório, e ninguém se cadastra sozinho nela. O filtro não barrava
        estranho nenhum; barrava o operador que o próprio administrador criou.
        Na tela, isso era o atendente entrando no painel e lendo "Nenhum
        agente ainda" — sem fila, sem Kanban, sem métrica, sem trabalho.

        Quem pode **mexer** no agente continua sendo só o administrador, agora
        pelo papel (`require_admin` nas rotas de escrita), que é onde essa
        decisão pertence. `user_id` no agente vira registro de quem o criou.
        """
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalars().first()

        if not agent:
            logger.warning(f"⚠️ Agent not found: {agent_id}")
            raise NotFoundException("Agent")

        return AgentResponse(
            id=agent.id,
            user_id=agent.user_id,
            nome=agent.nome,
            nome_atendente=agent.nome_atendente,
            descricao=agent.descricao,
            system_prompt=agent.system_prompt,
            anexos_habilitados=agent.anexos_habilitados,
            temperatura=agent.temperatura,
            max_tokens=agent.max_tokens,
            status=agent.status,
            data_criacao=agent.data_criacao,
            data_atualizacao=agent.data_atualizacao,
        )

    @staticmethod
    async def list_agents(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> List[AgentResponse]:
        """Os agentes do escritório — ver `get_agent` para o porquê de não filtrar por dono."""
        query = select(Agent)

        if status:
            query = query.where(Agent.status == status)

        query = query.order_by(Agent.data_criacao.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        agents = result.scalars().all()

        return [
            AgentResponse(
                id=agent.id,
                user_id=agent.user_id,
                nome=agent.nome,
                nome_atendente=agent.nome_atendente,
                descricao=agent.descricao,
                system_prompt=agent.system_prompt,
                anexos_habilitados=agent.anexos_habilitados,
                temperatura=agent.temperatura,
                max_tokens=agent.max_tokens,
                status=agent.status,
                data_criacao=agent.data_criacao,
                data_atualizacao=agent.data_atualizacao,
            )
            for agent in agents
        ]

    @staticmethod
    async def update_agent(
        agent_id: str,
        agent_data: AgentUpdate,
        db: AsyncSession,
    ) -> AgentResponse:
        """
        Edita o agente. Quem chega aqui já passou por `require_admin` na rota.

        Sem filtro por dono, pelo mesmo motivo de `get_agent`: um segundo
        administrador do escritório não deve ficar impedido de corrigir o
        prompt porque quem clicou em "criar" foi outra pessoa.
        """
        try:
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalars().first()

            if not agent:
                logger.warning(f"⚠️ Agent not found: {agent_id}")
                raise NotFoundException("Agent")

            # Validate updates if provided
            if agent_data.temperatura is not None:
                if not (0 <= agent_data.temperatura <= 2):
                    raise ValidationException("Temperature must be between 0 and 2")

            if agent_data.max_tokens is not None:
                if not (1 <= agent_data.max_tokens <= 4096):
                    raise ValidationException("Max tokens must be between 1 and 4096")

            if agent_data.system_prompt is not None:
                if not agent_data.system_prompt.strip():
                    raise ValidationException("System prompt cannot be empty")

            # Update only provided fields
            update_data = agent_data.dict(exclude_unset=True)

            await db.execute(
                update(Agent)
                .where(Agent.id == agent_id)
                .values(**update_data)
            )

            await db.commit()

            # Refresh agent data
            await db.refresh(agent)

            logger.info(f"✅ Agent updated: {agent_id}")

            return AgentResponse(
                id=agent.id,
                user_id=agent.user_id,
                nome=agent.nome,
                nome_atendente=agent.nome_atendente,
                descricao=agent.descricao,
                system_prompt=agent.system_prompt,
                anexos_habilitados=agent.anexos_habilitados,
                temperatura=agent.temperatura,
                max_tokens=agent.max_tokens,
                status=agent.status,
                data_criacao=agent.data_criacao,
                data_atualizacao=agent.data_atualizacao,
            )

        except (ValidationException, NotFoundException):
            await db.rollback()
            raise
        except Exception as e:
            logger.error(f"❌ Error updating agent: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def delete_agent(
        agent_id: str,
        db: AsyncSession,
    ) -> dict:
        """Apaga o agente. Rota protegida por `require_admin`."""
        try:
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalars().first()

            if not agent:
                logger.warning(f"⚠️ Agent not found: {agent_id}")
                raise NotFoundException("Agent")

            # Delete agent (CASCADE will delete related records)
            await db.execute(delete(Agent).where(Agent.id == agent_id))
            await db.commit()

            logger.info(f"✅ Agent deleted: {agent_id}")

            return {"message": "Agent deleted successfully", "agent_id": agent_id}

        except NotFoundException:
            await db.rollback()
            raise
        except Exception as e:
            logger.error(f"❌ Error deleting agent: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def add_variable(
        agent_id: str,
        variable_data: dict,
        db: AsyncSession,
    ) -> dict:
        """Acrescenta uma variável ao agente. Rota protegida por `require_admin`."""
        try:
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalars().first()

            if not agent:
                raise NotFoundException("Agent")

            new_variable = AgentVariable(
                agent_id=agent_id,
                nome_variavel=variable_data["nome_variavel"],
                descricao=variable_data.get("descricao"),
                tipo=variable_data["tipo"],
                valor_padrao=variable_data.get("valor_padrao"),
                opcoes=variable_data.get("opcoes"),
            )

            db.add(new_variable)
            await db.commit()
            await db.refresh(new_variable)

            logger.info(f"✅ Variable added to agent {agent_id}: {new_variable.nome_variavel}")

            return {
                "id": new_variable.id,
                "agent_id": new_variable.agent_id,
                "nome_variavel": new_variable.nome_variavel,
                "tipo": new_variable.tipo,
            }

        except NotFoundException:
            await db.rollback()
            raise
        except Exception as e:
            logger.error(f"❌ Error adding variable: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def get_variables(
        agent_id: str,
        db: AsyncSession,
    ) -> List[dict]:
        """As variáveis do agente — leitura, liberada a quem tem conta."""
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalars().first()

        if not agent:
            raise NotFoundException("Agent")

        # Get variables
        result = await db.execute(
            select(AgentVariable).where(AgentVariable.agent_id == agent_id)
        )
        variables = result.scalars().all()

        return [
            {
                "id": var.id,
                "nome_variavel": var.nome_variavel,
                "descricao": var.descricao,
                "tipo": var.tipo,
                "valor_padrao": var.valor_padrao,
            }
            for var in variables
        ]


agent_service = AgentService()
