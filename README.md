# LongBeach Transport - Backend API (FastAPI + PostgreSQL + SQLAlchemy + Alembic)

Backend da aplicação de transporte para vans universitárias e escolares com compartilhamento de rotas, confirmação diária de presença e cálculo de itinerários multi-destinos.

---

## 🛠️ Tecnologias Utilizadas

- **FastAPI**: Framework web assíncrono de alta performance.
- **SQLAlchemy 2.0**: ORM moderno com suporte assíncrono (`asyncpg` e `greenlet`).
- **Alembic**: Migrações versionadas de banco de dados.
- **PostgreSQL 16**: Banco de dados relacional oficial em container isolado.
- **PyJWT & Bcrypt**: Autenticação com tokens JWT e hashing seguro.
- **Pluggable Routing Engine**: Suporte a múltiplos provedores de rota (Mock/Haversine TSP, HERE Technologies, Google Routes API).
- **Docker & Docker Compose**: Orquestração completa (`postgres` + `backend-app`).

---

## 📁 Arquitetura de Dados & Entidades

```
Company (Empresa/Cooperativa)
  ├── Drivers (Motoristas)
  │     └── Trips (Viagens Recorrentes) ──────────────┐
  │           ├── TripDestinations (Faculdade A, B, C)├── [RoutingService]
  │           └── TripClients (Alunos vinculados)     │        ▲
  ├── Clients (Passageiros/Alunos) ───────────────────┘        │
  │     └── TripDailyAttendance (Check-in do dia: VOU / NÃO VOU)
  └── Users (Contas de Autenticação)
```

1. **Trip (`trips`)**: Viagem criada pelo motorista com ponto inicial/garagem e turno.
2. **TripDestination (`trip_destinations`)**: Múltiplos destinos finais em uma região (ex: Faculdade A, B e C com ordem de entrega).
3. **TripClient (`trip_clients`)**: Vínculo do aluno à viagem com os dias da semana em que ele vai (ex: Segundas, Quartas e Sextas).
4. **TripDailyAttendance (`trip_daily_attendance`)**: Confirmação diária de presença. O aluno avisa se vai (`CONFIRMED`) ou não (`ABSENT`) em uma data específica.

---

## 🚀 Como Rodar o Projeto

```bash
docker compose up -d
```

O container executa as migrações do Alembic automaticamente e sobe o servidor com hot-reload ativo em `http://localhost:8000`.

### Documentação Interativa da API (Swagger UI):
👉 **[http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)**

---

## 🧭 Fluxo de Viagens, Confirmação e Cálculo de Rota

### 1. Motorista Cadastra Novo Cliente e Vincula às Viagens
- **Endpoint:** `POST /api/v1/drivers/register-client`
- Permite que o motorista cadastre o aluno diretamente e defina quais dias da semana ele utiliza o serviço:
```json
{
  "email": "aluno@faculdade.com",
  "password": "senha123aluno",
  "full_name": "Lucas Aluno",
  "phone": "(11) 98888-7777",
  "pickup_address": "Rua Oscar Freire, 800 - Jardins, SP",
  "pickup_latitude": -23.5620,
  "pickup_longitude": -46.6690,
  "trip_assignments": [
    {
      "trip_id": "c11196ac-f5b3-47f8-962f-16af30f39dd9",
      "days_of_week": ["MONDAY", "WEDNESDAY", "FRIDAY"]
    }
  ]
}
```

---

### 2. Motorista Cria Viagem com Múltiplas Faculdades
- **Endpoint:** `POST /api/v1/trips`
```json
{
  "name": "Rota Manhã - Região Butantã / Pinheiros",
  "shift": "MORNING",
  "origin_address": "Garagem Central - Av. Rebouças, 1500",
  "origin_latitude": -23.5670,
  "origin_longitude": -46.6800,
  "destinations": [
    {
      "destination_name": "Faculdade A - USP Butantã",
      "address": "Av. Prof. Luciano Gualberto, 300",
      "latitude": -23.5580,
      "longitude": -46.7315,
      "drop_order": 1
    },
    {
      "destination_name": "Faculdade B - Mackenzie Higienópolis",
      "address": "Rua da Consolação, 930",
      "latitude": -23.5482,
      "longitude": -46.6521,
      "drop_order": 2
    }
  ]
}
```

---

### 3. Aluno Faz o Check-in Diário (Vai ou Não Vai)
- **Endpoint:** `POST /api/v1/trips/{trip_id}/attendance?trip_date=2026-10-18`
- O aluno envia `CONFIRMED` ou `ABSENT`:
```json
{
  "status": "CONFIRMED",
  "notes": "Estarei na calçada às 06:40 pontual!"
}
```

---

### 4. Motorista Calcula a Rota Otimizada do Dia
- **Endpoint:** `POST /api/v1/trips/{trip_id}/calculate-route?trip_date=2026-10-18`
- O `RoutingService` automaticamente:
  1. **Isola apenas os alunos confirmados** para a data informada (alunos ausentes são descartados da rota).
  2. Coleta as coordenadas de embarque dos confirmados.
  3. Adiciona os múltiplos destinos finais das faculdades.
  4. Executa o algoritmo de otimização de paradas (*Nearest Neighbor TSP* ou API externa).
  5. Retorna a lista ordenada com horários estimados de chegada (+X minutos) e distância total.

---

## 🧪 Teste de Integração Ponta a Ponta

Para validar todo o fluxo automaticamente (login de motorista, criação de viagem com 3 faculdades, onboarding de passageiro, check-in diário e roteamento inteligente):

```bash
docker compose exec backend-app python test_flow.py
```
