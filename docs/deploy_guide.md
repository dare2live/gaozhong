# 部署手册 (持牌机构内部)

## 0. 前提
- Linux 服务器 (Ubuntu 22+ 推荐), Docker + Docker Compose 已装
- 域名 DNS 解析到服务器
- HTTPS 证书 (letsencrypt 自动 / 商业证书均可)

## 1. 克隆
```bash
git clone <repo-url> /opt/gaozhong
cd /opt/gaozhong
```

## 2. 改证书路径
```bash
vim deploy/nginx.conf      # 把 your.domain.com 换成实际域名
```

## 3. 申请 letsencrypt 证书 (可选)
```bash
docker run --rm -it -v /etc/letsencrypt:/etc/letsencrypt \
  -p 80:80 certbot/certbot certonly --standalone -d your.domain.com
```

## 4. 启动
```bash
docker compose up -d
docker compose logs -f app    # 查跑情况
```

## 5. 访问
- `https://your.domain.com/`         主页 (探索 + 趋势 + 图谱)
- `https://your.domain.com/teacher`  教师端 (备课 / 题库 / 组卷)
- `https://your.domain.com/api/qb/stats` JSON API

## 6. 数据备份 (推荐 cron)
```cron
0 3 * * * /usr/bin/docker exec gaozhong-app cp /app/data/db/gaozhong.duckdb /app/data/db/backup-$(date +\%F).duckdb
```

## 7. 升级 / 重建
```bash
git pull
docker compose down
docker compose build --no-cache app
docker compose up -d
```

## 8. 内部教师账号
当前没正式 SSO. 临时方案:
- nginx basic auth 在 `/teacher` 路径上加密码
```nginx
location /teacher {
    auth_basic "教师端登录";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://app:8765/teacher;
}
```
- `.htpasswd` 用 `htpasswd -c .htpasswd teacher_id` 生成

## 9. 监控
- `docker compose logs app` 看 audit 输出
- 加 cron: `*/30 * * * * /usr/bin/docker exec gaozhong-app python3 -c "import duckdb; con=duckdb.connect('/app/data/db/gaozhong.duckdb', read_only=True); n=con.execute(\"SELECT COUNT(*) FROM audit_findings WHERE severity='FAIL'\").fetchone()[0]; assert n==0, f'AUDIT FAIL {n}'"`
- 失败邮件: `mailx -s "gaozhong audit FAIL" teacher@school.cn`

## 10. 已知 gap (运营中迭代)
- 学生答题日志: schema 已留 `student_answers`, 扫描 OCR pipeline 待实装
- 难度评估: 现在用题面长度启发式, 收集学生答对率后可上 sklearn 逻辑回归
- LLM 增强: 用户暂不启用. 后续接 Claude API 可:
  - 升级 cloze 干扰项
  - 抽 reading 真正"考点"短语
  - 趣味化改写 (教师 review 后入库)
