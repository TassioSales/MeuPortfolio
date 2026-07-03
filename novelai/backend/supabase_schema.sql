-- NovelAI — Schema Supabase (PostgreSQL)
-- Execute este SQL no Supabase SQL Editor

-- ─── EXTENSÕES ───────────────────────────────────────────────────────────────────
create extension if not exists "uuid-ossp";

-- ─── NOVELAS ─────────────────────────────────────────────────────────────────────
create table if not exists novelas (
    id              uuid primary key default uuid_generate_v4(),
    titulo          varchar(300) not null,
    descricao       text,
    genero          text[] default '{}',
    idioma          varchar(10) default 'pt',
    ano             integer,
    poster_url      varchar(500),
    backdrop_url    varchar(500),
    rating_medio    float default 0.0,
    total_votos     integer default 0,
    views           integer default 0,
    origem          varchar(20) default 'agregada' check (origem in ('agregada', 'gerada_ia')),
    fonte_original  varchar(500),
    data_criacao    timestamptz default now(),
    atualizado_em   timestamptz default now()
);

create index if not exists idx_novelas_genero on novelas using gin(genero);
create index if not exists idx_novelas_views on novelas(views desc);
create index if not exists idx_novelas_rating on novelas(rating_medio desc);

-- ─── EPISÓDIOS ───────────────────────────────────────────────────────────────────
create table if not exists episodios (
    id                  uuid primary key default uuid_generate_v4(),
    novela_id           uuid references novelas(id) on delete cascade,
    youtube_id          varchar(50),
    numero              integer not null default 1,
    titulo              varchar(300) not null,
    descricao           text,
    video_url           varchar(1000) not null,
    duracao_segundos    integer default 0,
    legendas_url        varchar(500),
    thumbnail_url       varchar(500),
    data_lancamento     timestamptz default now(),
    criado_em           timestamptz default now(),
    unique(youtube_id)
);

create index if not exists idx_episodios_novela on episodios(novela_id);
create index if not exists idx_episodios_numero on episodios(novela_id, numero);

-- ─── USUÁRIOS ────────────────────────────────────────────────────────────────────
create table if not exists usuarios (
    id                  uuid primary key default uuid_generate_v4(),
    email               varchar(255) unique not null,
    password_hash       varchar(255) not null,
    nome                varchar(150) not null,
    foto_url            varchar(500),
    role                varchar(20) default 'user' check (role in ('user', 'admin')),
    idioma_preferido    varchar(10) default 'pt',
    qualidade_padrao    varchar(10) default '720p',
    legendas_padrao     varchar(10) default 'off',
    criado_em           timestamptz default now(),
    atualizado_em       timestamptz default now()
);

-- ─── HISTÓRICO DE REPRODUÇÃO ─────────────────────────────────────────────────────
create table if not exists historico_reproducao (
    id                  uuid primary key default uuid_generate_v4(),
    user_id             uuid references usuarios(id) on delete cascade,
    episode_id          uuid references episodios(id) on delete cascade,
    posicao_segundos    integer default 0,
    assistido_em        timestamptz default now(),
    unique(user_id, episode_id)
);

create index if not exists idx_historico_user on historico_reproducao(user_id, assistido_em desc);

-- ─── FAVORITOS ───────────────────────────────────────────────────────────────────
create table if not exists favoritos (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid references usuarios(id) on delete cascade,
    episode_id      uuid references episodios(id) on delete cascade,
    criado_em       timestamptz default now(),
    unique(user_id, episode_id)
);

-- ─── COMENTÁRIOS ─────────────────────────────────────────────────────────────────
create table if not exists comentarios (
    id              uuid primary key default uuid_generate_v4(),
    episode_id      uuid references episodios(id) on delete cascade,
    novela_id       uuid references novelas(id) on delete cascade,
    user_id         uuid references usuarios(id) on delete cascade,
    texto           text not null,
    likes           integer default 0,
    criado_em       timestamptz default now(),
    atualizado_em   timestamptz default now(),
    deletado_em     timestamptz
);

create index if not exists idx_comentarios_novela on comentarios(novela_id, criado_em desc);
create index if not exists idx_comentarios_ep on comentarios(episode_id, criado_em desc);

-- ─── RATINGS ─────────────────────────────────────────────────────────────────────
create table if not exists ratings (
    id              uuid primary key default uuid_generate_v4(),
    episode_id      uuid references episodios(id) on delete cascade,
    novela_id       uuid references novelas(id) on delete cascade,
    user_id         uuid references usuarios(id) on delete cascade,
    estrelas        integer check (estrelas between 1 and 5),
    criado_em       timestamptz default now(),
    unique(episode_id, user_id)
);

-- ─── FILA DE GERAÇÃO (ADMIN) ─────────────────────────────────────────────────────
create table if not exists fila_geracao (
    id                      uuid primary key default uuid_generate_v4(),
    status                  varchar(20) default 'pendente'
                            check (status in ('pendente','processando','concluido','publicado','erro')),
    tipo                    varchar(50) default 'episodio',
    parametros              jsonb default '{}',
    video_url_resultado     varchar(1000),
    erro_mensagem           text,
    criado_em               timestamptz default now(),
    iniciado_em             timestamptz,
    concluido_em            timestamptz
);

create index if not exists idx_fila_status on fila_geracao(status, criado_em desc);

-- ─── RLS (Row Level Security) ────────────────────────────────────────────────────
-- Ativar RLS nas tabelas sensíveis
alter table usuarios enable row level security;
alter table historico_reproducao enable row level security;
alter table favoritos enable row level security;
alter table comentarios enable row level security;
alter table ratings enable row level security;

-- Policies básicas (ajuste conforme necessário)
create policy "Users see own data" on usuarios
    for select using (auth.uid()::text = id::text);

create policy "Users manage own historico" on historico_reproducao
    for all using (auth.uid()::text = user_id::text);

create policy "Users manage own favoritos" on favoritos
    for all using (auth.uid()::text = user_id::text);

create policy "Public read comentarios" on comentarios
    for select using (deletado_em is null);

create policy "Auth write comentarios" on comentarios
    for insert with check (auth.uid()::text = user_id::text);

-- ─── DADOS DE EXEMPLO ────────────────────────────────────────────────────────────
insert into novelas (titulo, descricao, genero, idioma, ano, poster_url, backdrop_url, rating_medio, views, origem)
values
  ('Coração Partido', 'Uma história de amor e rivalidade em São Paulo', '{"Drama","Romance"}', 'pt', 2024,
   'https://picsum.photos/seed/novela1/400/600', 'https://picsum.photos/seed/novela1/1280/720', 4.2, 15420, 'agregada'),
  ('Destino Duplo', 'Gêmeas separadas ao nascer se reencontram décadas depois', '{"Drama","Suspense"}', 'pt', 2024,
   'https://picsum.photos/seed/novela2/400/600', 'https://picsum.photos/seed/novela2/1280/720', 3.8, 8930, 'agregada'),
  ('Amor de Verão', 'Romance proibido em uma cidade litorânea', '{"Romance","Comédia"}', 'pt', 2023,
   'https://picsum.photos/seed/novela3/400/600', 'https://picsum.photos/seed/novela3/1280/720', 4.5, 22100, 'gerada_ia'),
  ('Herança Maldita', 'Família rica esconde segredos sombrios', '{"Drama","Suspense","Mistério"}', 'pt', 2024,
   'https://picsum.photos/seed/novela4/400/600', 'https://picsum.photos/seed/novela4/1280/720', 4.0, 11200, 'agregada'),
  ('Jogo do Destino', 'Rivalidade corporativa que vira caso de amor', '{"Drama","Romance"}', 'pt', 2023,
   'https://picsum.photos/seed/novela5/400/600', 'https://picsum.photos/seed/novela5/1280/720', 3.6, 6750, 'gerada_ia');
