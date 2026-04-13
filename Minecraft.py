import os
import time
from playwright.sync_api import sync_playwright, Cookie, TimeoutError as PlaywrightTimeoutError

def add_server_time(server_url="https://hub.weirdhost.xyz/server/9bde6441"):
    # 从环境变量获取登录凭据
    remember_web_cookie = os.environ.get('REMEMBER_WEB_COOKIE')
    pterodactyl_email = os.environ.get('PTERODACTYL_EMAIL')
    pterodactyl_password = os.environ.get('PTERODACTYL_PASSWORD')

    if not (remember_web_cookie or (pterodactyl_email and pterodactyl_password)):
        print("错误: 缺少登录凭据。请设置 REMEMBER_WEB_COOKIE 环境变量。")
        return False

    with sync_playwright() as p:
        # 【重要修复】加入反爬虫伪装参数，对抗 Cloudflare
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = context.new_page()
        page.set_default_timeout(90000)

        try:
            if remember_web_cookie:
                print("检测到 REMEMBER_WEB_COOKIE，尝试使用 Cookie 登录...")
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
                print(f"已设置 Cookie。正在访问: {server_url}")
                
                try:
                    page.goto(server_url, wait_until="domcontentloaded", timeout=90000)
                except PlaywrightTimeoutError:
                    print(f"页面加载超时（90秒）。")
                
                if "login" in page.url or "auth" in page.url:
                    print("Cookie 登录失败或会话已过期。")
                    context.clear_cookies()
                    remember_web_cookie = None 
                else:
                    print("Cookie 登录成功，已进入服务器页面。")

            if not remember_web_cookie:
                print("未提供有效的 Cookie，请更新 Cookie。")
                browser.close()
                return False

            print("等待面板基础框架加载...")
            time.sleep(5) 

            print("向下滚动页面以加载完整内容...")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(3) 

            print("正在检查是否触发了 Cloudflare 人机验证...")
            try:
                cf_iframe = page.locator('iframe[src*="challenges.cloudflare.com"]')
                cf_iframe.wait_for(state='visible', timeout=10000)
                print("⚠️ 发现 Cloudflare 验证框！尝试模拟真人动作...")
                
                page.mouse.move(400, 400)
                time.sleep(1)
                page.mouse.move(700, 500)
                time.sleep(1)
                
                cf_iframe.click(force=True)
                print("已点击验证框，等待 8 秒让 Cloudflare 验证...")
                time.sleep(8) 
            except PlaywrightTimeoutError:
                print("✅ 10秒内未检测到明文的 Cloudflare 验证框，继续执行...")
            except Exception as e:
                print(f"处理 Cloudflare 验证时出现状况: {e}")

            print("正在寻找 '연장하기' 按钮...")
            try:
                add_button = page.locator('button:has-text("연장하기")')
                add_button.wait_for(state='attached', timeout=15000)
                add_button.scroll_into_view_if_needed()
                print("🎯 找到续期按钮！正在判断是否可点击...")

                for i in range(15): 
                    if add_button.is_enabled():
                        print(f"✨ 按钮已激活！准备执行点击...")
                        add_button.click(force=True) 
                        print("✅ 成功点击 '연장하기' 按钮！")
                        time.sleep(10) 
                        browser.close()
                        return True
                    else:
                        print(f"按钮仍为灰色不可用，等待2秒重试... ({i+1}/15)")
                        time.sleep(2)

                print("❌ 错误：长达30秒一直处于灰色不可点击状态。CF 盾拦截了数据加载！")
                page.screenshot(path="cf_block_timeout.png")
                browser.close()
                return False

            except PlaywrightTimeoutError:
                print("❌ 错误: 找不到 '연장하기' 按钮。")
                page.screenshot(path="add_button_not_found.png")
                browser.close()
                return False

        except Exception as e:
            print(f"执行过程中发生未知错误: {e}")
            page.screenshot(path="general_error.png")
            browser.close()
            return False

if __name__ == "__main__":
    print("开始执行添加服务器时间任务...")
    success = add_server_time()
    if success:
        print("任务执行成功。")
        exit(0)
    else:
        print("任务执行失败。")
        exit(1)
