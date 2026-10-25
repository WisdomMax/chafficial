import subprocess
import json

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes("6ad7be96-e470-83e8-a5bf-1e8560f936e3"));
  if (!gptTab) {
    console.log("NO_TAB_FOUND");
    return;
  }
  const p = await attachBrowserTab(gptTab.targetId);

  // 1. 전체 body 텍스트에서 'REPORT 045-B 감사 결과'부터 끝까지 추출
  const auditText = await p.evaluate(() => {
    const full = document.body.innerText;
    const idx = full.lastIndexOf('REPORT 045-B 감사 결과');
    if (idx !== -1) {
      return full.slice(idx);
    }
    return full.slice(-15000);
  });

  console.log("AUDIT_LEN:" + auditText.length);
  console.log("===AUDIT_START===");
  console.log(auditText);
  console.log("===AUDIT_END===");
}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False
)

stdout = res.stdout
if "===AUDIT_START===" in stdout and "===AUDIT_END===" in stdout:
    content = stdout.split("===AUDIT_START===\n")[1].split("\n===AUDIT_END===")[0].strip()
    with open("reports/DIRECTIVE_045C_SPEC.md", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] 성공: reports/DIRECTIVE_045C_SPEC.md ({len(content)}자) 저장 완료")
else:
    print("[-] 추출 실패 stdout 앞부분:", stdout[:500])
