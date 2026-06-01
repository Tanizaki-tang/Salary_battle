# Salary Battle 部署指南

## 部署拓扑

- 后端 API: Render Web Service
- 数据库: Render Postgres
- 前端静态站点: Netlify

## 一、准备仓库

1. 把当前代码推到 GitHub、GitLab 或 Bitbucket。
2. 确保仓库根目录包含 `render.yaml`、`netlify.toml`、`Dockerfile`。

## 二、部署后端和数据库到 Render

1. 打开 Render 控制台，选择 `New -> Blueprint`。
2. 连接你的代码仓库。
3. 选择包含 `render.yaml` 的分支并部署。
4. Render 会创建：
   - `salary-battle-api` Web Service
   - `salary-battle-db` Postgres

## 三、在 Render 填写环境变量

以下变量需要在首次部署时补齐：

- `BAILIAN_API_KEY`
- `DASHSCOPE_API_KEY`（如果和 Bailian 相同，也可以留空）
- `CORS_ALLOW_ORIGINS`

`CORS_ALLOW_ORIGINS` 建议填写你的 Netlify 正式域名，例如：

```env
https://your-site.netlify.app
```

如果你希望临时放行所有 Netlify 预览域名，当前蓝图已默认配置：

```env
CORS_ALLOW_ORIGIN_REGEX=https://.*\.netlify\.app
```

## 四、记录 Render 后端地址

部署完成后，复制 Render 分配的后端地址，格式类似：

```text
https://salary-battle-api.onrender.com
```

健康检查地址：

```text
https://salary-battle-api.onrender.com/api/v1/health
```

## 五、部署前端到 Netlify

1. 打开 Netlify，选择 `Add new project`。
2. 连接同一个代码仓库。
3. 设置构建参数：
   - Base directory: `frontend`
   - Build command: `npm run build`
   - Publish directory: `dist`
4. 在 Netlify 的环境变量中设置：

```env
VITE_API_BASE_URL=https://你的-render-api.onrender.com
VITE_RUNTIME_MODE=api
VITE_APP_VARIANT=prod
```

5. 点击部署。

## 六、部署后自检

1. 打开前端首页，确认能正常进入开始页。
2. 创建一局文字对话，确认 `/api/v1/sessions` 返回 200。
3. 完成一局结算，确认排行榜能显示结果。
4. 访问 Render 健康检查接口，确认返回 `healthy`。

## 七、常见问题

### 1. 前端能打开，但接口全失败

优先检查：

- Netlify 是否设置了 `VITE_API_BASE_URL`
- Render 后端是否启动成功
- Render 的 `CORS_ALLOW_ORIGINS` 是否包含你的 Netlify 域名

### 2. 后端启动失败

优先检查：

- `DATABASE_URL` 是否已由 Render Blueprint 自动注入
- `BAILIAN_API_KEY` 是否已填写
- `render.yaml` 是否在仓库根目录

### 3. 排行榜没有数据

优先检查：

- 是否真的调用了 `/settle`
- Render Postgres 是否创建成功
- 后端日志里是否有数据库连接报错
