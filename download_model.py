from huggingface_hub import snapshot_download

# 指定模型 ID
REPO_ID = "Qwen/Qwen3-VL-8B-Instruct"

# **指定新的下载目录**
TARGET_DIR = "/mnt/ssd/qwen_models/Qwen3-VL-8B-Instruct"

# 运行下载
local_path = snapshot_download(
    repo_id=REPO_ID, 
    local_dir=TARGET_DIR,  # 模型文件将直接下载到此目录
    local_dir_use_symlinks=False
)

print(f"模型下载到：{local_path}")