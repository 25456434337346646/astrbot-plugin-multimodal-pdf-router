import subprocess
import sys

COMMANDS = [
    ['git', 'fetch', '--all'],
    ['git', 'reset', '--hard', 'origin/main']
]

def run():
    print("正在强制同步最新代码...")
    for i, cmd in enumerate(COMMANDS):
        print(f"[{i+1}/{len(COMMANDS)}] 执行: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            print(f"同步失败，请检查网络连接或手动运行 git pull。")
            return result.returncode
    print("同步成功！请在 AstrBot 插件页面点击【重载插件】。")
    return 0

if __name__ == "__main__":
    sys.exit(run())
