/// executor.rs: execute commands & save outputs

use std::process::Command;
use std::time::Instant;

pub struct ExecResult {
    pub exit_code: i32,
    pub stdout: String,
    pub stderr: String,
    pub exec_time_ms: u128,
}

pub fn run_shell(cmd: &str) -> ExecResult {
    let start = Instant::now();

    #[cfg(target_os = "windows")]
    let output = Command::new("cmd").args(["/C", cmd]).output();

    #[cfg(not(target_os = "windows"))]
    let output = Command::new("sh").args(["-c", cmd]).output();

    let elapsed = start.elapsed().as_millis();

    match output {
        Ok(out) => ExecResult {
            exit_code: out.status.code().unwrap_or(-1),
            stdout: String::from_utf8_lossy(&out.stdout).to_string(),
            stderr: String::from_utf8_lossy(&out.stderr).to_string(),
            exec_time_ms: elapsed,
        },
        Err(e) => ExecResult {
            exit_code: -1,
            stdout: String::new(),
            stderr: format!("beacon exec error: {e}"),
            exec_time_ms: elapsed,
        },
    }
}
