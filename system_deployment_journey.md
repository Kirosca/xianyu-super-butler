# 【Mxucc/xianyu-super-butler】闲鱼自动化发货系统部署与全历程技术文档

本文档详细记录了 **`Mxucc/xianyu-super-butler`（闲鱼超级管家/闲鱼自动化客服发货系统）** 在 Windows 原生环境（基于 SQLite 免安装 MySQL）下的完整搭建、报错排查、数据库适配及成功实现秒级自动发货的技术演进历程。

---

## 目录
1. [一、 项目概述与架构设计](#一-项目概述与架构设计)
2. [二、 部署与运行历程（突破的关键问题与解决方案）](#二-部署与运行历程突破的关键问题与解决方案)
   - [1. 数据库迁移与全量表结构构建（MySQL → SQLite）](#1-数据库迁移与全量表结构构建mysql--sqlite)
   - [2. 卡券绑定与原版 SQL 函数报错修复](#2-卡券绑定与原版-sql-函数报错修复)
   - [3. 闲鱼订单同步越权拦截修复（PERMISSION_EXCEPTION）](#3-闲鱼订单同步越权拦截修复permission_exception)
   - [4. 三大微服务架构搭建与通讯端口校准](#4-三大微服务架构搭建与通讯端口校准)
   - [5. 闲鱼 IM 令牌风控与滑块引擎修复](#5-闲鱼-im-令牌风控与滑块引擎修复)
3. [三、 项目核心代码修改对照表](#三-项目核心代码修改对照表)
4. [四、 项目一键启动与交互指南（一键BAT脚本）](#四-项目一键启动与交互指南一键bat脚本)
5. [五、 最终运行架构与日常维护指南](#五-最终运行架构与日常维护指南)

---

## 一、 项目概述与架构设计

项目采用 **Python + FastAPI + WebSocket + React** 构建，包含了前端管理 UI、后台 REST API、WebSocket 闲鱼实时长连接与定时调度引擎。

系统的核心模块分为：
- **`backend-web` (端口 8089)**：提供系统管理后台与 REST API 数据交互。
- **`websocket` (端口 8090)**：负责维护与闲鱼服务器的长连接通信，实现买家付款后的秒级自动发货。
- **`scheduler` (端口 8091)**：负责定时任务调度（防漏单轮询、自动评价、商品擦亮等）。
- **`frontend` (端口 9000)**：Vite 开发服务器，提供可视化管理界面。

---

## 二、 部署与运行历程（突破的关键问题与解决方案）

在部署与上线运行过程中，共克服了 5 大核心技术关卡：

### 1. 数据库迁移与全量表结构构建（MySQL → SQLite）
- **现象**：系统启动后前端报错 `(sqlite3.OperationalError) no such table: xy_system_settings`。
- **原因**：原代码依赖本地 MySQL 数据库，而当前环境需在 Windows 原生 SQLite (`data/xianyu_data.db`) 下运行。
- **解决方案**：
  - 编写了全量自动建表与 DDL 转换脚本 [`init_all_sqlite_tables.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/init_all_sqlite_tables.py)。
  - 解析 MySQL 建表语句，将 MySQL 专属数据类型（如 `LONGTEXT` → `TEXT`、`JSON` → `TEXT`、`AUTO_INCREMENT` → `INTEGER PRIMARY KEY AUTOINCREMENT`）进行正则替换与格式化。
  - 在 [`backend-web/_bootstrap.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/backend-web/_bootstrap.py) 中注入启动自动建表逻辑，成功一次性构建并初始化全套 68 张数据表。

### 2. 卡券绑定与原版 SQL 函数报错修复
- **现象**：卡券关联商品成功后，列表无法显示卡券，后台提示 `(sqlite3.OperationalError) no such function: NOW`。
- **原因**：原项目中部分原生 SQL 查询包含 MySQL 专属函数 `NOW()` 以及语法 `INSERT IGNORE`。
- **解决方案**：
  - 修改 [`common/services/card_matcher.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/common/services/card_matcher.py) 与 [`websocket/app/services/xianyu/cookie_token_manager.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/websocket/app/services/xianyu/cookie_token_manager.py)。
  - 将 `NOW()` 替换为 ANSI SQL 标准函数 `CURRENT_TIMESTAMP`。
  - 增加 SQLite 适配，将 `INSERT IGNORE` 动态替换为 `INSERT OR IGNORE`，成功完成商品 `1073352985883` 与卡券的绑定。

### 3. 闲鱼订单同步越权拦截修复（PERMISSION_EXCEPTION）
- **现象**：手动拉取订单时报错 `部分账号同步失败：2632848496: PERMISSION_EXCEPTION::无权限访问`。
- **原因**：原项目在调用淘宝 mtop 订单列表接口时，在 Request Header 中携带了 `'idle_site_biz_code': 'COMMONPRO'`，导致淘宝网关强制校验“鱼小店企业专业版”商户资质。
- **解决方案**：
  - 修改 [`common/services/order_service.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/common/services/order_service.py) 中的 `_fetch_sold_orders_page` 和 `_fetch_refund_orders_page`。
  - 移除企业版 Header 限制，成功一次性同步并导入个人卖家的 73 笔历史订单。

### 4. 三大微服务架构搭建与通讯端口校准
- **现象**：订单发货时提示 `【账号未连接，请先启动账号】`。
- **原因**：通用配置类 [`common/core/config.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/common/core/config.py) 中 `websocket_service_url` 默认指向了旧测试端口 `8001`，而 WebSocket 微服务实际监听在 `8090` 端口。
- **解决方案**：
  - 将 [`common/core/config.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/common/core/config.py) 中的 `websocket_service_url` 统一修正为 `http://127.0.0.1:8090`。
  - 放宽 [`backend-web/app/api/routes/orders.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/backend-web/app/api/routes/orders.py) 状态校验，只要账号处于 `running` 或 `is_connected` 即可发起发货。

### 5. 闲鱼 IM 令牌风控与滑块引擎修复
- **现象**：手动发货提示 `订单缺少会话ID且自动创建失败: 账号 2632848496 的 WebSocket 未连接`。
- **原因**：
  1. 闲鱼服务器请求 Token 时下发了 `FAIL_SYS_USER_VALIDATE` (`RGV587_ERROR` 滑块拦截)。
  2. Playwright 缺少 Chrome 浏览器组件 (`Chromium distribution 'chrome' is not found`)，导致后台自动解滑块中断。
- **解决方案与设置优化**：
  - **安装浏览器组件**：执行 `python -m playwright install chrome` 补全 Playwright 自动化 Chrome 二进制。
  - **开启显式窗口**：在数据库中将账号的 `show_browser` 设置为 `1`。启动时桌面会自动弹出交互窗口，鼠标拖拽一次滑块即可获取全新 `x5sec` 凭证。
  - **滑动模式切换为真实鼠标**：在系统的 **【系统设置】 -> 【基础设置】** 中，将 **【滑动滑块方式】** 修改切换为 **【真实鼠标滑动】**（`SLIDER_MODE_REAL_MOUSE`），结合显式 Chrome 窗口大幅提升阿里 Baxia 安全风控滑块的通过率与连接稳定度。
  - **SQLite Upsert 语法修复**：更新 [`common/services/token_renewal_cache_service.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/common/services/token_renewal_cache_service.py) 和 [`backend-web/app/services/goofish_crawler.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/backend-web/app/services/goofish_crawler.py)，使用 SQLite 原生的 `on_conflict_do_update` 替代 MySQL `on_duplicate_key_update`。

---

## 三、 项目核心代码修改对照表

| 修改文件 | 核心修改点 | 目的与效果 |
| :--- | :--- | :--- |
| [`common/core/config.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/common/core/config.py) | 1. 默认 DB 驱动切换为 SQLite<br>2. `websocket_service_url` 修正为 8090 | 实现免安装 MySQL 运行，校准微服务通信 |
| [`common/services/order_service.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/common/services/order_service.py) | 移除 Header 中的 `'idle_site_biz_code': 'COMMONPRO'` | 解决订单拉取 403 / 越权拒绝问题 |
| [`common/services/card_matcher.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/common/services/card_matcher.py) | `NOW()` → `CURRENT_TIMESTAMP`<br>`INSERT IGNORE` → `INSERT OR IGNORE` | 解决 SQLite 下卡券关联商品失败报错 |
| [`backend-web/app/api/routes/chat_new.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/backend-web/app/api/routes/chat_new.py) | MySQL `func.IF(...)` → SQLAlchemy `case(...)` | 解决账号列表加载 500 内部错误 |
| [`backend-web/app/api/routes/orders.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/backend-web/app/api/routes/orders.py) | 允许 `running` 或 `is_connected` 账号执行发货 | 解决手动发货时误判账号未连接问题 |
| [`common/services/token_renewal_cache_service.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/common/services/token_renewal_cache_service.py) | 增加 SQLite `on_conflict_do_update` | 解决 Token 缓存写入 UnsupportedCompilationError |
| [`backend-web/app/services/goofish_crawler.py`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/backend-web/app/services/goofish_crawler.py) | 增加 SQLite 复合主键 `on_conflict_do_update` | 解决商品采集批量保存报错问题 |

---

## 四、 项目一键启动与交互指南（一键BAT脚本）

为了方便日后随时一键启动全部 4 个后台服务，项目根目录下已为您创建了专属的 Windows 一键启动脚本：
[`一键启动闲鱼管家.bat`](file:///C:/Users/DS/.gemini/antigravity/scratch/zhinianboke-xianyu-auto-reply/%E4%B8%80%E9%94%AE%E5%90%AF%E5%8A%A8%E9%97%B2%E9%B1%BC%E7%AE%A1%E5%AE%B6.bat)

### 1. BAT 启动脚本完整代码
```bat
@echo off
chcp 65001 >nul
title 闲鱼超级管家一键启动器
echo ========================================================
echo               正在启动 闲鱼超级管家...
echo ========================================================

cd /d "%~dp0"

echo [1/4] 启动 Web API 后台服务 (端口 8089)...
start "1-BackendWeb(8089)" cmd /k "cd /d "%~dp0backend-web" && set PYTHONUTF8=1 && "C:\Program Files\Python311\python.exe" main.py"

timeout /t 2 >nul

echo [2/4] 启动 WebSocket 消息发货服务 (端口 8090)...
start "2-WebSocket(8090)" cmd /k "cd /d "%~dp0websocket" && set PYTHONUTF8=1 && "C:\Program Files\Python311\python.exe" main.py"

timeout /t 2 >nul

echo [3/4] 启动 Scheduler 定时调度服务 (端口 8091)...
start "3-Scheduler(8091)" cmd /k "cd /d "%~dp0scheduler" && set PYTHONUTF8=1 && "C:\Program Files\Python311\python.exe" main.py"

timeout /t 2 >nul

echo [4/4] 启动前端网页界面 (端口 9000)...
start "4-Frontend(9000)" cmd /k "cd /d "%~dp0" && npx vite --host 0.0.0.0 --port 9000"

echo ========================================================
echo 全部 4 个核心服务已在后台启动！
echo 请打开浏览器访问：http://localhost:9000
echo ========================================================
pause
```

### 2. 您自己如何启动？
- 找到项目路径 `C:\Users\DS\.gemini\antigravity\scratch\zhinianboke-xianyu-auto-reply\`
- 双击运行 **`一键启动闲鱼管家.bat`** 即可。
- 打开浏览器访问 **`http://localhost:9000`**。

### 3. 以后如何对我（AI 助手）说？
任何时候您想让我帮您重启或检查项目，只需发送以下任意一句话：
- 🗣️ **“帮我一键启动闲鱼管家所有服务”**
- 🗣️ **“闲鱼自动发货断了，帮我重新启动一下项目”**
- 🗣️ **“检查一下闲鱼管家的进程并全部启动”**

---

## 五、 最终运行架构与日常维护指南

### 1. 当前后台运行的服务列表
系统以 4 个独立守护进程协同工作：
- **Web API 服务 (`backend-web`)**：`http://127.0.0.1:8089`
- **WebSocket 长连接服务 (`websocket`)**：`http://127.0.0.1:8090`
- **定时调度服务 (`scheduler`)**：`http://127.0.0.1:8091`
- **前端 Web 界面 (`frontend`)**：`http://localhost:9000`

### 2. 日常防风控与使用建议
1. **回复延迟**：在【账号管理】编辑面板中，保持 2~5 秒的随机回复延迟，避免被系统判定为纯机械高频调用。
2. **滑块模式**：在【系统设置】->【基础设置】中确认滑块模式为【真实鼠标滑动】。遇到风控拦截时，点击后台【重启账号】，在桌面弹出的 Chrome 窗口中用鼠标拉动滑块通过即可。
3. **数据安全**：全量数据保存在 `data/xianyu_data.db` SQLite 数据库中，定期备份该文件即可完成全量配置与订单备份。
