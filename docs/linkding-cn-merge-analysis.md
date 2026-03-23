# linkding-cn 与当前项目对比及合并可行性分析

## 一、项目概况

| 维度 | 当前项目 (linkding) | linkding-cn |
|------|-------------------|-------------|
| **版本** | 1.45.0.2（本仓库 fork） | 1.0.3 |
| **上游** | sissbruecker/linkding (官方) | fork 自 sissbruecker/linkding |
| **分叉点** | - | 约 2025 年 7 月 (merge base: 4e8318d) |
| **提交差异** | 最新 (573b6f5) | 领先 186 个自定义提交，落后 111 个上游提交 |
| **Python** | 3.13 | 3.12 |
| **Django** | 6.0 | 5.2.4 |
| **依赖管理** | pyproject.toml + uv | requirements.txt + uv pip compile |

---

## 二、技术栈差异

### 1. 依赖差异

**linkding-cn 独有依赖：**

- `drissionpage`：自定义快照脚本（浏览器自动化）
- `pypinyin`：中文标签拼音分组
- `python-dateutil`：日期处理
- `django-registration`：用户注册
- `django-widget-tweaks`：表单控件增强

**当前项目无上述依赖**，且已移除 `django-registration` 等旧方案。

### 2. 模型差异

| 模型/类 | linkding-cn 变更 | 当前项目 |
|---------|------------------|----------|
| **Bookmark** | `is_deleted`, `date_deleted`, `preview_image_remote_url` | 无回收站字段 |
| **BookmarkBundle** | `show_count`, `is_folder`, `search_params` (JSON)，移除 `filter_unread`/`filter_shared` | 有 `filter_unread`, `filter_shared` (#1308) |
| **BookmarkSearch** | `SORT_RANDOM`, `SORT_DELETED_*`, `FILTER_TAGGED_*`, 日期筛选（绝对/相对） | 无随机排序、回收站排序、标签状态筛选、日期筛选 |
| **UserProfile** | `custom_domain_root`, `trash_search_preferences`, `sticky_header_controls`, `sticky_side_panel` | 有 `legacy_search`，无上述字段 |
| **ApiToken** | 无 | 有（多 Token 管理） |

---

## 三、linkding-cn 独有功能概览

| 类别 | 功能 |
|------|------|
| **本地化** | 界面中文化、中文标签聚合（pypinyin）、时区与日期处理、favicon.im |
| **搜索** | 限定搜索范围（标题、描述、笔记、URL） |
| **筛选** | 日期筛选（绝对/相对）、标签状态（有标签/无标签） |
| **排序** | 随机排序、按删除时间排序 |
| **过滤器** | 二级过滤器、`search_params` 支持更多筛选项 |
| **元数据** | 自定义解析脚本、更多网站支持 |
| **快照** | 自定义脚本（drissionpage）、重命名 |
| **阅读模式** | 无快照时也可开启 |
| **回收站** | 软删除、还原、永久删除、批量操作 |
| **界面** | 书签数量、粘性搜索/分页/侧边栏、favicon 快速筛选、独立滚动、位置记忆、折叠状态记忆 |
| **样式** | 各类影响操作或美观的样式问题 |

---

## 四、合并可行性评估

### 1. 直接合并（Git merge）—— 不可行

- 分叉点距今约 8 个月，上游有 111 个新提交
- 模型、视图、模板、配置差异大
- 依赖冲突（Django 5 vs 6、Python 3.12 vs 3.13）
- 合并冲突会非常多，难以一次性解决

### 2. 按功能 cherry-pick —— 可行但工作量大

**建议按功能模块拆分迁移：**

| 优先级 | 功能 | 难度 | 说明 |
|--------|------|------|------|
| 高 | 中文本地化 | 中 | 翻译文件、locale 配置、i18n 流程 |
| 高 | 回收站 | 高 | 需新增 `is_deleted`、`date_deleted`，迁移与视图逻辑 |
| 中 | 日期筛选 | 中 | 扩展 `BookmarkSearch` 参数 |
| 中 | 随机排序 | 低 | 新增排序选项 |
| 中 | 标签状态筛选 | 低 | 新增筛选参数 |
| 中 | 搜索范围限定 | 中 | 修改搜索解析逻辑 |
| 低 | Bundle 二级过滤器 | 高 | 与 `filter_unread`/`filter_shared` 并存，需统一设计 |
| 低 | 自定义元数据/快照脚本 | 高 | 引入 drissionpage，依赖与维护成本高 |
| 低 | 界面增强 | 中 | 粘性、滚动、折叠等，需适配当前 CSS/JS |

### 3. 依赖与兼容性

- **drissionpage**：依赖较重，需评估是否引入
- **pypinyin**：轻量，适合中文标签分组
- **django-registration**：当前项目已移除，需确认是否仍需要注册功能
- **Django 6**：linkding-cn 基于 Django 5，需在迁移时做兼容性检查

---

## 五、建议方案

### 方案 A：按需选择性迁移（推荐）

1. 在**当前项目**上新建分支
2. 按优先级选择功能（如：中文、回收站、日期筛选、随机排序）
3. 按 linkding-cn 的实现逐行迁移，并适配 Django 6、当前模型和 API
4. 为每个功能单独迁移、测试

### 方案 B：保持 linkding-cn 为独立分支

1. 继续使用 linkding-cn 作为独立仓库
2. 定期与上游 linkding 合并，解决冲突
3. 适合：需要 linkding-cn 全部功能且能接受维护成本

### 方案 C：向官方提交 PR

1. 将「回收站」「日期筛选」「随机排序」等通用功能做成 PR
2. 提交到 sissbruecker/linkding
3. 若被接受，后续维护成本最低

---

## 六、总结

| 项目 | 结论 |
|------|------|
| **直接合并** | 不建议，冲突多、依赖复杂 |
| **按功能迁移** | 可行，但需逐个适配并测试 |
| **推荐顺序** | 先做：中文本地化、回收站、日期筛选、随机排序 |
| **预估工作量** | 中等：每个功能约 1–3 天，取决于测试覆盖 |
| **风险** | 依赖升级、模型迁移、API 兼容性需重点验证 |

---

## 参考链接

- [linkding-cn GitHub](https://github.com/WooHooDai/linkding-cn)
- [linkding 官方](https://github.com/sissbruecker/linkding)
- [功能迁移计划](linkding-cn-migration-plan.md)
