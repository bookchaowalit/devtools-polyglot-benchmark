use axum::{Json, Router, extract::{Path, Query, State}, http::StatusCode, routing::get};
use deadpool_postgres::{Manager, Pool};
use serde_json::{Value, json};
use std::{collections::HashMap, str::FromStr, sync::Arc};
use tokio_postgres::NoTls;

const POOL_SIZE: usize = 10;
const DB_QUERY: &str = "SELECT id, name, price_cents, qty, tags FROM bench_items WHERE id > $1 ORDER BY id LIMIT $2";

#[derive(Clone)]
struct AppState {
    items: Arc<HashMap<i64, Value>>,
    pool: Option<Pool>,
}

type Reply = (StatusCode, Json<Value>);

fn error(status: StatusCode, code: &str) -> Reply {
    (status, Json(json!({"error": code})))
}

async fn health() -> Json<Value> {
    Json(json!({"status": "ok"}))
}

async fn item(State(state): State<AppState>, Path(id): Path<String>) -> Reply {
    let found = if !id.is_empty() && id.bytes().all(|b| b.is_ascii_digit()) {
        id.parse::<i64>().ok().and_then(|n| state.items.get(&n))
    } else {
        None
    };
    match found {
        Some(record) => (StatusCode::OK, Json(record.clone())),
        None => error(StatusCode::NOT_FOUND, "not_found"),
    }
}

fn int_param(params: &HashMap<String, String>, name: &str, fallback: i64) -> Option<i64> {
    match params.get(name) {
        None => Some(fallback),
        Some(raw) if !raw.is_empty() && raw.bytes().all(|b| b.is_ascii_digit()) => raw.parse().ok(),
        Some(_) => None,
    }
}

async fn db_items(State(state): State<AppState>, Query(params): Query<HashMap<String, String>>) -> Reply {
    let Some(pool) = state.pool.as_ref() else {
        return error(StatusCode::SERVICE_UNAVAILABLE, "no_database");
    };
    let (Some(after), Some(limit)) = (int_param(&params, "after", 0), int_param(&params, "limit", 50)) else {
        return error(StatusCode::BAD_REQUEST, "bad_request");
    };
    if !(1..=100).contains(&limit) || after > i32::MAX as i64 {
        return error(StatusCode::BAD_REQUEST, "bad_request");
    }
    let Ok(client) = pool.get().await else {
        return error(StatusCode::INTERNAL_SERVER_ERROR, "db");
    };
    let Ok(rows) = client.query(DB_QUERY, &[&(after as i32), &limit]).await else {
        return error(StatusCode::INTERNAL_SERVER_ERROR, "db");
    };
    let items: Vec<Value> = rows
        .iter()
        .map(|r| {
            json!({
                "id": r.get::<_, i32>(0),
                "name": r.get::<_, String>(1),
                "price_cents": r.get::<_, i32>(2),
                "qty": r.get::<_, i32>(3),
                "tags": r.get::<_, Vec<String>>(4),
            })
        })
        .collect();
    (StatusCode::OK, Json(json!({"items": items})))
}

async fn open_pool(url: &str) -> Pool {
    let config = tokio_postgres::Config::from_str(url).expect("DATABASE_URL");
    let pool = Pool::builder(Manager::new(config, NoTls)).max_size(POOL_SIZE).build().expect("pool");
    // open every connection up front, as the other lanes do
    let clients = futures_all(&pool).await;
    drop(clients);
    pool
}

async fn futures_all(pool: &Pool) -> Vec<deadpool_postgres::Object> {
    let mut handles = Vec::with_capacity(POOL_SIZE);
    for _ in 0..POOL_SIZE {
        let p = pool.clone();
        handles.push(tokio::spawn(async move { p.get().await.expect("db connection") }));
    }
    let mut clients = Vec::with_capacity(POOL_SIZE);
    for h in handles {
        clients.push(h.await.expect("join"));
    }
    clients
}

#[tokio::main]
async fn main() {
    let path = std::env::var("RECORDS_PATH").expect("RECORDS_PATH");
    let records: Vec<Value> = serde_json::from_slice(&std::fs::read(path).expect("read")).expect("parse");
    let items = Arc::new(records.into_iter().map(|r| (r["id"].as_i64().unwrap(), r)).collect());
    let pool = match std::env::var("DATABASE_URL") {
        Ok(url) if !url.is_empty() => Some(open_pool(&url).await),
        _ => None,
    };
    let app = Router::new()
        .route("/health", get(health))
        .route("/items/{id}", get(item))
        .route("/db/items", get(db_items))
        .with_state(AppState { items, pool });
    let port = std::env::var("PORT").expect("PORT");
    let listener = tokio::net::TcpListener::bind(format!("127.0.0.1:{port}")).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
