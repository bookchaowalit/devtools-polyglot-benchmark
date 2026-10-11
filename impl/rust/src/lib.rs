//! Data access and validation shared by the Rust framework variants, so each
//! variant differs only in its HTTP framework. The axum baseline
//! (src/bin/server.rs) keeps its own copy so its numbers stay comparable.
use deadpool_postgres::{Manager, Pool};
use serde_json::{Value, json};
use std::{collections::HashMap, str::FromStr};
use tokio_postgres::NoTls;

const POOL_SIZE: usize = 10;
const DB_QUERY: &str = "SELECT id, name, price_cents, qty, tags FROM bench_items WHERE id > $1 ORDER BY id LIMIT $2";

pub fn load_items() -> HashMap<i64, Value> {
    let path = std::env::var("RECORDS_PATH").expect("RECORDS_PATH");
    let records: Vec<Value> = serde_json::from_slice(&std::fs::read(path).expect("read")).expect("parse");
    records.into_iter().map(|r| (r["id"].as_i64().unwrap(), r)).collect()
}

/// None when DATABASE_URL is unset. Opens every connection up front, like the other lanes.
pub async fn open_pool() -> Option<Pool> {
    let url = std::env::var("DATABASE_URL").ok().filter(|u| !u.is_empty())?;
    let config = tokio_postgres::Config::from_str(&url).expect("DATABASE_URL");
    let pool = Pool::builder(Manager::new(config, NoTls)).max_size(POOL_SIZE).build().expect("pool");
    let mut clients = Vec::with_capacity(POOL_SIZE);
    for _ in 0..POOL_SIZE {
        clients.push(pool.get().await.expect("db connection"));
    }
    drop(clients);
    Some(pool)
}

fn digits(raw: &str) -> bool {
    !raw.is_empty() && raw.bytes().all(|b| b.is_ascii_digit())
}

pub fn item_id(raw: &str) -> Option<i64> {
    if digits(raw) { raw.parse().ok() } else { None }
}

/// (after, limit) validated the same way every lane does.
pub fn page_params(params: &HashMap<String, String>) -> Option<(i32, i64)> {
    let parse = |name: &str, fallback: i64| match params.get(name) {
        None => Some(fallback),
        Some(raw) if digits(raw) => raw.parse::<i64>().ok(),
        Some(_) => None,
    };
    let (after, limit) = (parse("after", 0)?, parse("limit", 50)?);
    if !(1..=100).contains(&limit) || after > i32::MAX as i64 {
        return None;
    }
    Some((after as i32, limit))
}

pub async fn fetch_page(pool: &Pool, after: i32, limit: i64) -> Result<Value, ()> {
    let client = pool.get().await.map_err(|_| ())?;
    let rows = client.query(DB_QUERY, &[&after, &limit]).await.map_err(|_| ())?;
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
    Ok(json!({"items": items}))
}
