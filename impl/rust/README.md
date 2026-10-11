# Lane: rust-axum

- Rust stable, `serde_json`, `sha2` (pure Rust), axum on the multi-threaded tokio runtime
- Built with `cargo build --release` (thin LTO, one codegen unit)

```bash
cd impl/rust && cargo build --release
```
