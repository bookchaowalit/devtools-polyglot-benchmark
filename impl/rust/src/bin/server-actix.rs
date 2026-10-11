use actix_web::{App, HttpResponse, HttpServer, web};
use deadpool_postgres::Pool;
use lane_rust_axum::{fetch_page, item_id, load_items, open_pool, page_params};
use serde_json::{Value, json};
use std::collections::HashMap;

struct AppState {
    items: HashMap<i64, Value>,
    pool: Option<Pool>,
}

async fn health() -> HttpResponse {
    HttpResponse::Ok().json(json!({"status": "ok"}))
}

async fn item(state: web::Data<AppState>, id: web::Path<String>) -> HttpResponse {
    match item_id(&id).and_then(|n| state.items.get(&n)) {
        Some(record) => HttpResponse::Ok().json(record),
        None => HttpResponse::NotFound().json(json!({"error": "not_found"})),
    }
}

async fn db_items(state: web::Data<AppState>, query: web::Query<HashMap<String, String>>) -> HttpResponse {
    let Some(pool) = state.pool.as_ref() else {
        return HttpResponse::ServiceUnavailable().json(json!({"error": "no_database"}));
    };
    let Some((after, limit)) = page_params(&query) else {
        return HttpResponse::BadRequest().json(json!({"error": "bad_request"}));
    };
    match fetch_page(pool, after, limit).await {
        Ok(page) => HttpResponse::Ok().json(page),
        Err(()) => HttpResponse::InternalServerError().json(json!({"error": "db"})),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let state = web::Data::new(AppState { items: load_items(), pool: open_pool().await });
    let port = std::env::var("PORT").expect("PORT");
    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .route("/health", web::get().to(health))
            .route("/items/{id}", web::get().to(item))
            .route("/db/items", web::get().to(db_items))
    })
    .bind(format!("127.0.0.1:{port}"))?
    .run()
    .await
}
