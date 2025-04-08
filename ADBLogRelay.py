try:
    import git
    import subprocess
    import os
except ImportError as e:
    if "git" in str(e):
        print("错误：未安装GitPython模块。")
        print("请运行以下命令进行安装：")
        print("pip install GitPython")
    else:
        print(f"Error: {e}")
    exit(1)

def git_clone(repo_url, repo_path):
    """
    使用GitPython克隆远程仓库到本地
    :param repo_url: 远程仓库地址
    :param repo_path: 本地仓库路径
    """
    try:
        print("Cloning repository...")
        git.Repo.clone_from(repo_url, repo_path)
        print("已成功克隆存储库。")
    except git.GitCommandError as e:
        print("git克隆过程中出错：", e)
    except Exception as e:
        print("出现错误：", e)

def git_pull(repo_path):
    """
    使用GitPython执行git pull命令来更新本地仓库
    :param repo_path: 本地仓库路径
    """
    try:
        # 打开本地仓库
        repo = git.Repo(repo_path)
        # 执行git pull命令
        origin = repo.remotes.origin
        origin.pull()
        print("Git拉取已成功完成。")
    except git.GitCommandError as e:
        print("git pull时出错：", e)
    except Exception as e:
        print("出现错误：", e)

def run_script(script_path):
    """
    运行指定的Python脚本，并实时显示打印信息
    :param script_path: 要运行的Python脚本路径
    """
    try:
        # 使用Popen启动子进程，合并stderr到stdout，并禁用缓冲
        process = subprocess.Popen(
            ['python', '-u', script_path],  # '-u' 参数禁用缓冲
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,       # 合并stderr到stdout
            text=True,
            bufsize=1                      # 行缓冲
        )

        # 实时读取并打印合并后的输出
        for line in process.stdout:
            print(line, end='', flush=True)  # 实时打印并刷新输出

        # 等待子进程结束
        process.wait()

        # 检查返回码
        if process.returncode != 0:
            print(f"Script exited with return code {process.returncode}")

    except Exception as e:
        print("An error occurred:", e)

if __name__ == "__main__":
    # 远程仓库地址
    repo_url = 'https://github.com/aaa147147/--------MQTT--'
    # 本地仓库路径
    repo_path = './repo/'

    # 如果本地仓库不存在，则克隆
    if not os.path.exists(repo_path):
        git_clone(repo_url, repo_path)
    else:
        # 如果本地仓库已存在，则执行git pull
        git_pull(repo_path)

    # 要运行的Python脚本路径
    script_path = os.path.join(repo_path, 'PingTest.py')
    # 确保脚本存在后运行
    if os.path.exists(script_path):
        run_script(script_path)
    else:
        print(f"Script {script_path} not found!")