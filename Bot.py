import os
import time
from playwright.sync_api import sync_playwright, Cookie, TimeoutError as PlaywrightTimeoutError

def add_server_time(server_url="https://hub.weirdhost.xyz/server/9bde6441"):
    remember_web_cookie = os.environ.get('REMEMBER_WEB_COOKIE')
    pterodactyl_email = os.environ.get('PTERODACTYL_EMAIL')
    pterodactyl_password = os.environ.get('PTERODACTYL_PASSWORD')

    if not (remember_web_cookie or (pterodactyl_email and pterodactyl_password)):
        print("❌ 错误: 缺少登录凭据。请设置 REMEMBER_WEB_COOKIE 环境变量。")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-setuid-sandbox']
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            timezone_id='Asia/Shanghai', # 强制设置为北京时间，与你的电脑保持完全一致
            locale='ko-KR'
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = context.new_page()
        page.set_default_timeout(90000)

        try:
            if remember_web_cookie:
                print("🍪 检测到 Cookie，尝试使用会话登录...")
                session_cookie = {
                    'name': 'remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d',
                    'value': remember_web_cookie,
                    'domain': 'hub.weirdhost.xyz',
                    'path': '/',
                    'expires': int(time.time()) + 3600 * 24 * 365,
                    'httpOnly': True,
                    'secure': True,
                    'sameSite': 'Lax'
                }
                context.add_cookies([session_cookie])
                
                try:
                    page.goto(server_url, wait_until="domcontentloaded", timeout=90000)
                except PlaywrightTimeoutError:
                    print("⚠️ 页面基础加载超时（90秒），尝试继续执行...")
                
                if "login" in page.url or "auth" in page.url:
                    print("❌ Cookie 已过期或无效，请更新 GitHub Secrets 中的 Cookie。")
                    browser.close()
                    return False
                else:
                    print("✅ Cookie 登录成功，已进入服务器控制台页面。")

            print("⏳ 等待面板数据加载...")
            time.sleep(6) 

            # 向下滚动页面以加载底部信息
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2) 

            # CF 盾处理预留
            try:
                cf_iframe = page.locator('iframe[src*="challenges.cloudflare.com"]')
                cf_iframe.wait_for(state='visible', timeout=5000)
                print("🛡️ 发现 Cloudflare 验证，尝试点击...")
                page.mouse.move(500, 500)
                cf_iframe.click(force=True)
                time.sleep(6) 
            except PlaywrightTimeoutError:
                pass 

            # ----------------------------------------------------
            # 【核心功能】：基于按钮真实状态的安全点击
            # ----------------------------------------------------
            print("\n🔍 正在解析服务器状态...")
            
            try:
                add_button = page.locator('button:has-text("연장하기")')
                add_button.wait_for(state='attached', timeout=20000)
                add_button.scroll_into_view_if_needed()
            except PlaywrightTimeoutError:
                print("❌ 未能在页面找到 '연장하기' 按钮结构，面板可能发生了大改版。")
                page.screenshot(path="no_button_error.png")
                browser.close()
                return False

            # 等待 5 秒，让前端 JS 彻底算完时间并解除按钮锁定
            time.sleep(5)

            # 仅读取文本用于日志展示 (不作为点击判断依据)
            expire_locator = page.locator('text=/유통기한/')
            if expire_locator.count() > 0:
                print(f"📅 【整体到期时间】: {expire_locator.first.inner_text().strip()}")

            status_locator = page.locator('text=/연장할수있어요|연장할 수 있어요|연장이 가능해요/')
            if status_locator.count() > 0:
                print(f"💡 【页面提示文本】: {status_locator.first.inner_text().strip()}")

            # 回归本质：以按钮的实际 HTML 可用属性为准
            print("⚙️ 正在检测按钮真实可用状态...")
            is_ready = False
            for i in range(5):
                if add_button.is_enabled():
                    is_ready = True
                    break
                time.sleep(2)

            if is_ready:
                print("✨ 【状态：可续期】！按钮已亮起，正在执行强制点击...")
                add_button.click(force=True)
                print("✅ 成功点击！已发送续期请求，等待 10 秒供服务器处理...")
                time.sleep(10)
            else:
                print("⏳ 【状态：冷却中】。按钮为灰色不可用状态。")
                print("🎉 任务正常结束（未到时间，跳过点击）。")
                
            browser.close()
            return True

        except Exception as e:
            print(f"执行过程中发生未知错误: {e}")
            page.screenshot(path="general_error.png")
            browser.close()
            return False

if __name__ == "__main__":
    print("🚀 开始执行面板续期任务...")
    success = add_server_time()
    if success:
        print("🟢 脚本执行完毕。")
        exit(0)
    else:
        print("🔴 脚本执行异常。")
        exit(1)
