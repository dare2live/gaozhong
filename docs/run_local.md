# 本地启动 (Mac)

> 替代 Docker 部署 (用户 2026-05-24: 暂不需要).
> 一键起 + 浏览器自动打开教师端 / 主页 / 学生端.

## 启动 (3 步)

1. **首次** — 在终端跑一次依赖检查 (后续不用):
   ```bash
   cd /Users/dp/Documents/M/gaozhong
   python3 -c "import duckdb, pypdf, yaml; print('依赖 OK')"
   ```
   (这 3 个包系统 Python 3.13 已有, 不用 pip install)

2. **启动** — Finder 里**双击 `start.command`**
   - 首次会自动跑 `scripts/init_db.py` (3-5 秒)
   - 启 backend (端口 8765)
   - 自动打开浏览器 3 标签: 教师端 / 主页 / 学生端

3. **停止** — Finder 里双击 `stop.command`
   或终端 `pkill -f backend/api/main.py`

## 重建数据 (改了 extractor 或源数据)

```bash
python3 scripts/init_db.py
```
后双击 `stop.command` 再 `start.command` 重启.

## 日志

`logs/gaozhong-<时间戳>.log` — server stdout/stderr.

## 端口冲突

`start.command` 会先 `pkill` 旧 server. 若仍冲突, 改 `start.command` 里 `PORT=8765` 为别的.

## 多用户访问

`start.command` 用 `--host 127.0.0.1` 仅本机. 想让局域网其它机访问:
1. 改 `start.command`: `--host 0.0.0.0`
2. Mac 防火墙允许 Python 入站
3. 局域网机访问 `http://<你的局域网 IP>:8765/teacher`
