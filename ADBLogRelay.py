import os
import subprocess
try:
    from dulwich import porcelain
    from dulwich.repo import Repo, NotGitRepository
except ImportError:
    print("模块 dulwich 未找到，请使用以下命令安装：pip install dulwich")
    exit(1)

def git_clone(repo_url, repo_path):
    """
    使用 Dulwich 克隆远程仓库到本地
    :param repo_url: 远程仓库地址
    :param repo_path: 本地仓库路径
    """
    try:
        print("Cloning repository...")
        porcelain.clone(repo_url, repo_path)  # 使用 Dulwich 的克隆接口
        print("已成功克隆存储库。")
    except Exception as e:
        print("克隆过程中出错：", e)

def git_pull(repo_path):
    """
    强制拉取远程仓库的最新更改，丢弃所有本地未提交的修改
    :param repo_path: 本地仓库路径
    """
    try:
        repo = Repo(repo_path)
        
        # 1. 获取远程最新数据
        porcelain.fetch(repo, remote_location="origin")
        
        # 2. 获取当前分支名（如 "main" 或 "master"）
        current_branch = repo.refs.follow(b"HEAD")[0][1].decode("utf-8").split("/")[-1]
        remote_branch = f"origin/{current_branch}"
        
        # 3. 强制重置本地分支到远程最新状态（相当于 `git reset --hard origin/<branch>`）
        repo.refs[b"HEAD"] = repo.refs[f"refs/remotes/{remote_branch}".encode("utf-8")]
        repo.reset_index()
        
        print("强制拉取成功，本地已与远程完全同步。")
    except NotGitRepository:
        print("错误：目标路径不是Git仓库。")
    except Exception as e:
        print("强制拉取时出错：", e)

        
def run_script(script_path):
    """
    运行指定的Python脚本（与原代码一致，无需修改）
    """
    try:
        process = subprocess.Popen(
            ['python', '-u', script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for line in process.stdout:
            print(line, end='', flush=True)
        process.wait()
        if process.returncode != 0:
            print(f"Script exited with return code {process.returncode}")
    except Exception as e:
        print("An error occurred:", e)

if __name__ == "__main__":
    repo_url = 'https://github.com/aaa147147/--------MQTT--'
    repo_path = './repo/'

    # 检查是否为Git仓库（避免重复克隆）
    try:
        Repo(repo_path)
        git_pull(repo_path)  # 存在则拉取更新
    except NotGitRepository:
        git_clone(repo_url, repo_path)  # 不存在则克隆

    script_path = os.path.join(repo_path, 'PingTest.py')
    if os.path.exists(script_path):
        run_script(script_path)
    else:
        print(f"Script {script_path} not found!")