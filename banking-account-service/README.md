# Banking Account Service

Owns bank account records and balances. Customer name is stored as a local read projection.

Swagger UI: `http://localhost:8002/docs`

## Main APIs

- `POST /accounts`
- `GET /accounts`
- `GET /accounts/{account_id}`
- `GET /accounts/customer/{customer_id}`
- `GET /accounts/{account_id}/balance`
- `PUT /accounts/{account_id}`
- `PATCH /accounts/{account_id}/status`
- `DELETE /accounts/{account_id}`
- `GET /health`
