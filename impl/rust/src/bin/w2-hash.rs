use sha2::{Digest, Sha256};
use std::io::Read;

fn main() {
    let path = std::env::args().nth(1).expect("blob path");
    let mut file = std::fs::File::open(path).expect("open blob");
    let mut hasher = Sha256::new();
    let mut buf = vec![0u8; 1024 * 1024];
    loop {
        let n = file.read(&mut buf).expect("read blob");
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    let digest = hasher.finalize();
    println!("{}", digest.iter().map(|b| format!("{b:02x}")).collect::<String>());
}
