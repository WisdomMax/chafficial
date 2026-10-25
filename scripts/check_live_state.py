import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes("6ad7be96-e470-83e8-a5bf-1e8560f936e3"));
  const p = await attachBrowserTab(gptTab.targetId);

  const status = await p.evaluate(() => {
    const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                    document.querySelector('button[aria-label*="중지"]') ||
                    document.querySelector('button[aria-label*="Stop"]');
    const sendBtn = document.querySelector('button[data-testid="send-button"]') ||
                    document.querySelector('button[aria-label*="전송"]') ||
                    document.querySelector('button[aria-label*="Send"]');
    const retryBtn = document.querySelector('button[aria-label*="다시 시도"]') ||
                     document.querySelector('button[aria-label*="응답 다시 생성"]');
    const composer = document.querySelector('#prompt-textarea') ||
                     document.querySelector('[contenteditable="true"]');
    
    // 마지막 article 태그
    const articles = Array.from(document.querySelectorAll('article'));
    const lastArticle = articles.length > 0 ? articles[articles.length - 1].innerText.slice(0, 200) : '';

    return {
      hasStopBtn: !!stopBtn,
      hasSendBtn: !!sendBtn,
      sendDisabled: sendBtn ? sendBtn.disabled : null,
      hasRetryBtn: !!retryBtn,
      composerText: composer ? composer.innerText : '',
      articleCount: articles.length,
      lastArticlePreview: lastArticle
    };
  });

  console.log("STATUS:" + JSON.stringify(status, null, 2));
}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True
)

for line in res.stdout.splitlines():
    print(line)
