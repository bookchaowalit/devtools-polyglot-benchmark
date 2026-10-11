use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Deserialize)]
struct Item {
    id: i64,
    #[allow(dead_code)]
    name: String,
    price_cents: i64,
    qty: i64,
    tags: Vec<String>,
}

#[derive(Serialize)]
struct Summary {
    count: usize,
    total_value_cents: i64,
    by_tag: BTreeMap<String, u64>,
    top5: Vec<i64>,
}

fn main() {
    let path = std::env::args().nth(1).expect("records path");
    let data = std::fs::read(path).expect("read records");
    let records: Vec<Item> = serde_json::from_slice(&data).expect("parse records");
    let mut by_tag = BTreeMap::new();
    let mut total = 0;
    for r in &records {
        total += r.price_cents * r.qty;
        for t in &r.tags {
            *by_tag.entry(t.clone()).or_insert(0) += 1;
        }
    }
    let mut ranked: Vec<&Item> = records.iter().collect();
    ranked.sort_by(|a, b| (b.price_cents * b.qty).cmp(&(a.price_cents * a.qty)).then(a.id.cmp(&b.id)));
    let out = Summary {
        count: records.len(),
        total_value_cents: total,
        by_tag,
        top5: ranked.iter().take(5).map(|r| r.id).collect(),
    };
    println!("{}", serde_json::to_string(&out).unwrap());
}
